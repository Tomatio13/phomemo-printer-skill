<h1 align="center">phomemo</h1>
<p align="center">
Phomemo M02 Pro 向けのレイアウト生成（JSON）→ 画像合成 → プレビュー/印刷を、MCPサーバ経由で提供します。
</p>

## 前提
- OS: Linux（BlueZを使用）
- Python: 3.10+（動作確認は環境に依存）
- Bluetooth: プリンタと接続できること

## セットアップ

### 依存関係（BlueZ）
```bash
sudo apt update
sudo apt install -y bluez libbluetooth-dev python3-venv python3-full
```

### Python環境
```bash
cd /path/to/phomemo
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 環境変数（.env）
このプロジェクトは起動時に`.env`を読み込みます（`.env`は`.gitignore`に含まれておりコミットされません）。

```bash
cp env.example .env
```

`.env`の例:
```dotenv
PHOMEMO_PRINTER_ADDRESS=B5:4B:B4:78:7B:C4
PHOMEMO_PRINTER_CHANNEL=1
```

## プリンタ接続（Bluetooth）

### スキャン
```bash
hcitool scan
```

### 接続
```bash
bluetoothctl connect XX:XX:XX:XX:XX:XX
```

### RFCOMM Channel 確認
```bash
sudo sdptool records XX:XX:XX:XX:XX:XX
```

## プリンタ単体テスト（任意）
`phomemo_printer` CLIで疎通できます（※`-t`のテキスト印刷は環境のフォント事情に依存します。レイアウト印刷は画像化するため日本語も印刷可能です）。

```bash
phomemo_printer -a XX:XX:XX:XX:XX:XX -c 1 -t "Hello world"
phomemo_printer -a XX:XX:XX:XX:XX:XX -c 1 -i ./image.jpg
```

## MCPサーバ（Codex/Strands等から利用）

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

## MCPで提供する主なツール
- `get_printer_spec`
- `get_layout_schema`
- `get_layout_examples`
- `validate_layout(layout)`
- `render_layout_job(layout, dry_run=true|false, encoding="utf-8")`

## 印刷フロー（推奨）
1) まずプレビュー（既定 `dry_run=true`）を作る  
2) 問題なければ `dry_run=false` で印刷する

注意: `dry_run`の既定は`true`なので、**印刷したい場合は必ず`dry_run=false`を指定してください**。

## `printed=false` の切り分け
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

## リポジトリ構成
- `src/phomemo_agent/`: 実装本体
  - `composer.py` / `printer.py` / `pipeline.py` / `validators.py`
  - `mcp/layout_server.py`: MCPサーバ本体（tools/resources/prompts）
  - `cli/run_mcp_server.py`: MCPサーバ起動CLI
- `schemas/layout_job.schema.json`: レイアウトJSON Schema
- `env.example`: `.env`の雛形
