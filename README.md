
#1. インストール

BlueZのインストール
```bash
sudo apt update && sudo apt install bluez libbluetooth-dev

$ sudo apt install python3-venv python3-full
$ cd phomemo-printer-skill
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install --upgrade pip
(.venv) $ pip install -r requirements.txt
```

#2. プリンターの接続

Bluetoothのスキャン
```bash
$ hcitool scan                                              
Scanning ...
    B5:4B:B4:78:7B:C4       M02 Pro
```
Bluetoothの接続
```bash
$ bluetoothctl connect B5:4B:B4:78:7B:C4
Attempting to connect to B5:4B:B4:78:7B:C4
[CHG] Device B5:4B:B4:78:7B:C4 WakeAllowed: yes
[CHG] Device B5:4B:B4:78:7B:C4 Connected: yes
Connection successful
```

Channel 番号の確認
RFCOMMのChannel番号を確認する
```bash
$ sudo sdptool records B5:4B:B4:78:7B:C4
Service Name: JL_SPP
Service RecHandle: 0x10004
Service Class ID List:
  "Serial Port" (0x1101)
Protocol Descriptor List:
  "L2CAP" (0x0100)
  "RFCOMM" (0x0003)
    Channel: 1
Profile Descriptor List:
  "Serial Port" (0x1101)
    Version: 0x0102
```

#3. プリンターのテスト
文字の印刷テスト
```bash
phomemo_printer -a B5:4B:B4:78:7B:C4 -c 1 -t "Hello world"
```
ただし、日本語フォントがないため日本語は直接印刷はできない。


画像の印刷テスト
```bash
phomemo_printer -a B5:4B:B4:78:7B:C4 -c 1 -i ./image.jpg 
```

#4. MCP サーバー経由での Strands Agent 連携

- Strands Agents の MCP ツール仕様に従い（[ドキュメント](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/mcp-tools/index.md)）、このプロジェクトは `FastMCP` ベースのサーバーを提供します
- 起動例（SSE・ホスト/ポートは引数で変更可能）:

```
(.venv) $ python -m phomemo_agent.cli.run_mcp_server --transport sse --host 0.0.0.0 --port 8787
```

- Strands 側では公式ドキュメントの通り `MCPClient` を構築し、`streamable_http_client("http://<host>:8787/mcp")` もしくは `sse_client("http://<host>:8787/sse")` で接続してください
- **推奨フロー**（LLMが設計→JSON→印刷）:
  - `get_printer_spec` / `get_layout_schema` / `get_layout_examples` を呼んで仕様を読み込む
  - LLMが `schemas/layout_job.schema.json` 準拠の `layout` JSON を生成
  - `validate_layout(layout)` で事前検証
  - `render_layout_job(layout, dry_run=true)` でプレビュー生成 → OKなら `dry_run=false` で印刷
- 提供ツール `render_layout_job` は Strands エージェントが生成したレイアウトJSONを受け取り、`LayoutJobPipeline` による検証・プレビュー・印刷を行います（`dry_run=True` でプレビューのみ）
- `output.path` は省略可能です。省略した場合、`dry_run=true` 時は `/tmp/phomemo_preview_*.png` に自動保存され、その絶対パスが `preview_path` として返ります（`artifacts/` 不要）。
- 縦横が逆に見える場合は `output.rotate` を指定してください（既定: `auto`）
- MCP 経由で複数のツールを組み合わせる場合は、Strands 側の `tool_filters` や `prefix` オプションで名称衝突を回避できます（上記ドキュメント参照）
