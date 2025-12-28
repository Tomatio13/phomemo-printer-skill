<h1 align="center">phomemo-printer-skill</h1>

<p align="center">
  <a href="README_JP.md">🇯🇵 日本語</a> ·
  <a href="README_EN.md">🇺🇸 English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/bluez-required-orange" />
  <img src="https://img.shields.io/badge/skills-agent-green" />
  <img src="https://img.shields.io/badge/mcp-server-green" />
</p>

Phomemo M02 Pro 向けのレイアウト生成（JSON）-> 画像合成 -> プレビュー/印刷を、MCPサーバ経由で提供します。

## 📌 機能概要

- Phomemo M02 Pro 向けのレイアウトを JSON で生成
- レイアウトを画像に変換してプレビュー/印刷
- MCP ツールで検証・レンダリング・印刷を提供

## ✅ 必要要件

- OS: Linux（BlueZを使用）
- Python: 3.10+（動作確認は環境に依存）
- Bluetooth: プリンタと接続できること

## ⚙️ セットアップ

### 依存関係（BlueZ）

```bash
sudo apt update
sudo apt install -y bluez libbluetooth-dev python3-venv python3-full
```

> 補足: venv推奨、uv非推奨
> OS環境にも依存しそうですが、Bluetoothを使うのに、BlueZが必要です。
> bluezを入れた後に、pythonをインストールするとコンパイルされて、
> bluetooth用のヘッダ周りが参照できるようになるようです。
> uvでやると、コンパイル済みのpythonを使用されるためか、
> bluetooth用のヘッダ周りが参照できないようでエラーが発生します。

### Python環境（venv）

```bash
cd /path/to/phomemo
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 🔐 環境変数（.env）

このプロジェクトは起動時に`.env`を読み込みます（`.env`は`.gitignore`に含まれておりコミットされません）。

```bash
cp env.example .env
```

`.env`の例:

```dotenv
PHOMEMO_PRINTER_ADDRESS=B5:4B:B4:78:7B:C4
PHOMEMO_PRINTER_CHANNEL=1
```

## ▶️ 使い方

### プリンタ接続（Bluetooth）

スキャン:

```bash
hcitool scan
```

接続:

```bash
bluetoothctl connect XX:XX:XX:XX:XX:XX
```

RFCOMM Channel 確認:

```bash
sudo sdptool records XX:XX:XX:XX:XX:XX
```

### プリンタ単体テスト（任意）

`phomemo_printer` CLIで疎通できます（※`-t`のテキスト印刷は環境のフォント事情に依存します。レイアウト印刷は画像化するため日本語も印刷可能です）。

```bash
phomemo_printer -a XX:XX:XX:XX:XX:XX -c 1 -t "Hello world"
phomemo_printer -a XX:XX:XX:XX:XX:XX -c 1 -i ./image.jpg
```

## 🧭 Skills

`skills/phomemo-layout` は、Phomemo M02 Pro 向けのレイアウトJSONの生成・検証・プレビュー・印刷までを扱う Agent Skills です。
Claude Codeや、Codex等のコーディングエージェントのSkillとして利用できます。
例えば、コーディングエージェント上で`xxxxを印刷してください`という依頼を出した場合に、
スキルを利用してレイアウトJSONを生成し、印刷を行うことができます。

### ⏳スキルのフロー:
以下のような流れで動作します。

1) プリンタ仕様とスキーマを読む
2) JSONのみを出力し、`skills/phomemo-layout/outputs/` に配置する
3) `requirements.txt` で依存を導入する
4) 検証: `PYTHONPATH=src python skills/phomemo-layout/scripts/validate_layout.py <layout.json>`
5) プレビュー: `PYTHONPATH=src python skills/phomemo-layout/scripts/render_layout.py --dry-run <layout.json>`
6) 印刷する場合: `PYTHONPATH=src python skills/phomemo-layout/scripts/render_layout.py --print <layout.json>`

### 🖨 レイアウト仕様の要点:

- 幅は常に 576px 固定。背景は白、文字は黒が基本。
- 印刷前に `output.threshold` で2値化される。
- 実寸換算（300dpi想定）: `px = cm / 2.54 * 300`。576px は約 4.88cm。
- 長尺は `output.slice_height`（例: 1400）と `output.chunk_rows`（1-256）で分割送信する。
- 回転は `output.rotate`（`auto` / `none` / `cw90` / `ccw90`）。長尺の定規は回転せずY方向で確保する。

### 利用方法
ディレクトリ`phomemo-layout`を各コーディングエージェントのディレクトリ`skills`に配置します。
コーディングエージェントのSkillとして利用できます。


### 📝 サンプル:
jsonファイルのサンプルです。
- `skills/phomemo-layout/references/layout.sample.json`

## 🧰 MCPサーバ（Codex/Strands等から利用）

### 起動（重要: PYTHONPATH）

このリポジトリは現状「インストール済みパッケージ」ではないため、`python -m ...`で動かす場合は`PYTHONPATH=src`が必要です。

```bash
export PYTHONPATH="$PWD/src"
```

### 起動例（トランスポート・ホスト/ポートは引数で変更可能）

```bash
# Streamable HTTP（推奨）
python -m phomemo_agent.cli.run_mcp_server --transport streamable-http --host 0.0.0.0 --port 8787

# Streamable HTTP（互換エイリアス: http）
python -m phomemo_agent.cli.run_mcp_server --transport http --host 0.0.0.0 --port 8787

# SSE
python -m phomemo_agent.cli.run_mcp_server --transport sse --host 0.0.0.0 --port 8787

# stdio
python -m phomemo_agent.cli.run_mcp_server --transport stdio
```

### エンドポイント

- Streamable HTTP: `http://<host>:8787/mcp`
- SSE: `http://<host>:8787/sse`

### クライアント接続（例）

- Streamable HTTP: `streamable_http_client("http://<host>:8787/mcp")`
- SSE: `sse_client("http://<host>:8787/sse")`

### MCPで提供する主なツール

- `get_printer_spec`
- `get_layout_schema`
- `get_layout_examples`
- `validate_layout(layout)`
- `render_layout_job(layout, dry_run=true|false, encoding="utf-8")`

## 🧪 印刷フロー（推奨）

1) まずプレビュー（既定 `dry_run=true`）を作る
2) 問題なければ `dry_run=false` で印刷する

**注意**: `dry_run`の既定は`true`なので、印刷したい場合は必ず`dry_run=false`を指定してください。

## 🧩 補足

- スクリプト実行時は `PYTHONPATH=src` を設定する。
- レイアウト印刷は画像化するため日本語も印刷可能です。

## 🛠 トラブルシューティング

### `printed=false` の切り分け

`render_layout_job`の戻り値`info`には、以下が入ります（サーバ再起動後に反映）:

- `info.dry_run`
- `info.send_to_printer`
- `info.printer.address_present`（MACアドレス本体は返さず存在有無のみ）
- `info.printer.address_source`（`env`/`missing` など）
- `info.reason_not_printed`（例: `"dry_run=true (preview only)"`）

典型原因:

- `dry_run=true`のまま（プレビューのみ）
- レイアウトJSON側が `output.send_to_printer=false`
- `.env`の`PHOMEMO_PRINTER_ADDRESS`未設定、またはBluetooth未接続

## 🗂 リポジトリ構成

- `src/phomemo_agent/`: 実装本体
  - `composer.py` / `printer.py` / `pipeline.py` / `validators.py`
  - `mcp/layout_server.py`: MCPサーバ本体（tools/resources/prompts）
  - `cli/run_mcp_server.py`: MCPサーバ起動CLI
- `schemas/layout_job.schema.json`: レイアウトJSON Schema
- `env.example`: `.env`の雛形
