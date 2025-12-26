## Phomemo MCP サーバー設計

Phomemo M02 Pro 向けに、Strands Agents 等のLLMが **レイアウトJSONを生成**し、MCPツール経由で **プレビュー/印刷** するための上位設計をまとめる。

### 1. 目標と前提
- ユーザーの曖昧なアイディアから、印刷に耐えるレイアウトを自動生成する。
- `print_layout_from_json.py` を中心にした JSON レイアウト合成フローを活かしつつ、マルチモーダル画像生成（例: 鳥居や列車）も扱えるようにする。
- 生成した Skill を Mastra / MCP 相当の Agent Skill として再利用可能にする。

### 2. 機能要件
|区分|要求|
|---|---|
|ユースケース|巻物Skill / 長尺Skill / トレインSkill 等のレイアウトをワンショット生成・印刷|
|入力|ユーザー指示（自然言語）・必要に応じ素材画像/フォント指定|
|出力|576px 幅のPNGプレビュー、実機印刷データ、生成メタ情報|
|UX|印刷前に`--dry-run`プレビューで内容確認、再生成や追記を容易に|

### 3. 非機能要件
- 再現性: JSON スキーマで差分管理し、LLM 出力をバリデート。
- 品質: 熱転写向けにコントラスト調整（`to_thermal_ready`）を徹底。
- 拡張性: Skill/テンプレ単位で追加しやすい構造。
- 安全性: Bluetooth 送信前にリストリクションチェック（寸法 / chunk_rows）。

### 4. コンポーネント構成
```
┌────────┐    ┌────────────┐
│User/Agent│→→│Intent Resolver│
└────────┘    └─────┬──────┘
                      │
        ┌─────────────┴─────────────┐
        │                             │
┌───────────────────────────┐
│ Strands Agent (LLM)        │
│ - spec/schema/example取得  │
│ - layout JSON 生成          │
└──────────────┬────────────┘
               │ MCP tool call
┌──────────────▼────────────┐
│ Phomemo MCP Server         │
│ - validate_layout          │
│ - render_layout_job        │
└──────────────┬────────────┘
               │
┌──────────────▼────────────┐
│ LayoutJobPipeline          │
│ - compose_canvas           │
│ - to_thermal_ready         │
│ - transmit                 │
└───────────────────────────┘
```

### 5. MCPサーバの責務
- **仕様提供**: `get_printer_spec` / `get_layout_schema` / `get_layout_examples` と、`phomemo://...` リソースでLLMが段階的に参照可能にする
- **検証**: `validate_layout(layout)` でJSONSchema検証
- **実行**: `render_layout_job(layout, dry_run=...)` でプレビュー/印刷（`output.rotate` による回転含む）

### 8. 画像を含むレイアウト
- `layers[].type="image"` を使うことで、LLMは画像レイヤー＋テキストレイヤーの複合レイアウトを設計できる。
- 画像ファイルはローカルパス（`path`）参照のため、必要ならStrands側で素材を用意してからJSONに組み込む。

### 9. データ定義
- **Job Config JSON**（主要キー）
  - `canvas.font_path` (必須) / `fallback_fonts`
  - `canvas.margin` / `height`（未指定時は自動計算）
  - `layers[]` … `type` (`text` or `image`), `position`, `width`, `font_size`, `wrap_style`, `stroke`, `opacity` など
  - `output.path` / `threshold` / `slice_height` / `chunk_rows` / `send_to_printer`
- **Generation Metadata**
  - `skill_name`, `intent`, `prompts`, `model`, `validation_errors`, `preview_path`, `print_timestamp`

### 10. プロンプト設計メモ
- LLMには「JSONのみ返す」「Schemaに厳密準拠」「存在するフォントパスのみ使用」を強く指示すると安定する。
- 物理制約（幅576px固定、cm→px換算、長尺はY方向で確保）を必ず先に読ませる。

### 10.1 MCPサーバーでの統合
- Strands公式のMCPツール仕様（[参照](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/index.md)）に倣い、`phomemo_agent.mcp.layout_server` で `FastMCP` サーバーを提供
- Tool: `render_layout_job(layout, dry_run?, encoding?)`（プリンタ設定は環境変数を参照）
  - `layout` を `LayoutJobValidator` で検証後、`LayoutJobPipeline` に渡しプレビュー/印刷
  - 戻り値は `preview_path`, `printed`, `slice_heights`, `info`
- 起動: `python -m phomemo_agent.cli.run_mcp_server --transport sse --port 8787`
- Strands側では `MCPClient` を `streamable_http_client` や `stdio_client` で接続し、tool filtering・prefixingを使って他ツールと共存させる

### 11. エラー処理・リトライ
- JSON バリデーション失敗時は自動修正プロンプトを返す（例: 「font_path missing, add field」）。
- 画像生成がノイズ過多の場合は閾値を上げて再生成 or `ImageEnhance.Contrast` で補正。
- `Printer` 送信で例外が出たら再接続し、未送信スライスから再送。

### 12. Agent Skill 実装方針
- Skill ごとに以下を提供:
  - `describe()`：ユースケース説明と必要入力（例: 巻物Skill＝本文テキスト、装飾トーン）
  - `plan()`：Intent Resolver から受け取るコンテキスト→どのテンプレを使うか決定
  - `execute()`：LayoutSkill or IllustrationSkill の呼び出しと検証
  - `post_process()`：プレビュー格納、ログ記録、印刷可否確認
- Mastra/MCP 互換を意識して `tools/print_preview`, `tools/send_to_phomemo` のようなAPIを定義。

### 13. 今後の拡張
- Prompt/JSON を Git バージョン管理し、成功例を Knowledge Base 化。
- Skill Marketplace 風に、ユーザーが自作テンプレをアップロードし共有できるようにする。
- 画像生成モデルをローカル実行（Flux.1-dev 等）に切り替えるオプションを追加。
- BLE 以外の接続手段（USB, Wi-Fi ブリッジ）にも対応。

### 14. 実装フォルダ構成
- `src/phomemo_agent/`
  - `composer.py` / `printer.py` / `pipeline.py` / `validators.py`
  - `mcp/layout_server.py` … MCPサーバ本体（tools/resources/prompts）
  - `cli/run_mcp_server.py` … MCPサーバ起動CLI
- `schemas/layout_job.schema.json` … JSONSchema
- `artifacts/` … （任意）過去の試験用に残っている場合があるが、現状のMCPフローでは不要。プレビューはデフォルトで `/tmp/phomemo_preview_*.png` に出力される。
