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

Phomemo M02 Pro layout generation (JSON) -> image composition -> preview/print via an MCP server.

## 📌 Overview

- Generate layouts as JSON for Phomemo M02 Pro.
- Render layouts into images for preview/printing.
- Provide MCP tools for validation, rendering, and printing.

## ✅ Requirements

- OS: Linux (BlueZ)
- Python: 3.10+ (runtime behavior depends on environment)
- Bluetooth: Printer must be connectable

## ⚙️ Setup

### Dependencies (BlueZ)

```bash
sudo apt update
sudo apt install -y bluez libbluetooth-dev python3-venv python3-full
```

> Note: venv is recommended; uv is not recommended.
> Bluetooth requires BlueZ. If you install Python after BlueZ, Python can be
> compiled with bluetooth headers available. With uv, a prebuilt Python is
> used, and bluetooth headers may not be found, leading to build errors.

### Python environment (venv)

```bash
cd /path/to/phomemo
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 🔐 Environment variables (.env)

This project reads `.env` on startup (`.env` is in `.gitignore` and is not committed).

```bash
cp env.example .env
```

Example `.env`:

```dotenv
PHOMEMO_PRINTER_ADDRESS=B5:4B:B4:78:7B:C4
PHOMEMO_PRINTER_CHANNEL=1
```

## ▶️ Usage

### Printer connection (Bluetooth)

Scan:

```bash
hcitool scan
```

Connect:

```bash
bluetoothctl connect XX:XX:XX:XX:XX:XX
```

Check RFCOMM channel:

```bash
sudo sdptool records XX:XX:XX:XX:XX:XX
```

### Printer smoke test (optional)

Use the `phomemo_printer` CLI to verify connectivity (`-t` text printing depends on local fonts. Layout printing is rendered to images, so Japanese is supported).

```bash
phomemo_printer -a XX:XX:XX:XX:XX:XX -c 1 -t "Hello world"
phomemo_printer -a XX:XX:XX:XX:XX:XX -c 1 -i ./image.jpg
```

## 🧭 Skills

`skills/phomemo-layout` is an Agent Skill for generating, validating, previewing, and printing layout JSON for Phomemo M02 Pro.
It can be used as a skill in coding agents such as Claude Code or Codex.
For example, if you ask an agent to “print xxxx,” it can generate a layout JSON and send it to the printer via this skill.

### ⏳ Skill flow

1) Read the printer spec and schema.
2) Create JSON only and place it under `skills/phomemo-layout/outputs/`.
3) Install dependencies from `requirements.txt`.
4) Validate: `PYTHONPATH=src python skills/phomemo-layout/scripts/validate_layout.py <layout.json>`
5) Preview: `PYTHONPATH=src python skills/phomemo-layout/scripts/render_layout.py --dry-run <layout.json>`
6) Print if needed: `PYTHONPATH=src python skills/phomemo-layout/scripts/render_layout.py --print <layout.json>`

### 🖨 Layout spec highlights

- Fixed width is 576px; background should be white and text black by default.
- Output is binarized at `output.threshold` before printing.
- Approx conversion (300dpi): `px = cm / 2.54 * 300` and 576px is about 4.88cm wide.
- If the job is long, use `output.slice_height` (e.g., 1400) and `output.chunk_rows` (1-256) to avoid Bluetooth transfer stalls.
- Rotation is controlled by `output.rotate` (`auto`, `none`, `cw90`, `ccw90`); avoid rotation for long ruler-style layouts by extending Y.

### How to use

Place the `phomemo-layout` directory under the agent's `skills` directory to make it available as an Agent Skill.

### 📝 Sample

- `skills/phomemo-layout/references/layout.sample.json`

## 🧰 MCP server (for Codex/Strands clients)

### Startup (important: PYTHONPATH)

This repository is not installed as a package yet, so `python -m ...` requires `PYTHONPATH=src`.

```bash
export PYTHONPATH="$PWD/src"
```

### Startup examples (transport and host/port are configurable)

```bash
# Streamable HTTP (recommended)
python -m phomemo_agent.cli.run_mcp_server --transport streamable-http --host 0.0.0.0 --port 8787

# Streamable HTTP (compatible alias: http)
python -m phomemo_agent.cli.run_mcp_server --transport http --host 0.0.0.0 --port 8787

# SSE
python -m phomemo_agent.cli.run_mcp_server --transport sse --host 0.0.0.0 --port 8787

# stdio
python -m phomemo_agent.cli.run_mcp_server --transport stdio
```

### Endpoints

- Streamable HTTP: `http://<host>:8787/mcp`
- SSE: `http://<host>:8787/sse`

### Client connection examples

- Streamable HTTP: `streamable_http_client("http://<host>:8787/mcp")`
- SSE: `sse_client("http://<host>:8787/sse")`

### MCP tools

- `get_printer_spec`
- `get_layout_schema`
- `get_layout_examples`
- `validate_layout(layout)`
- `render_layout_job(layout, dry_run=true|false, encoding="utf-8")`

## 🧪 Recommended print flow

1) Create a preview first (default `dry_run=true`).
2) If it looks good, print with `dry_run=false`.

**Note**: `dry_run` defaults to `true`, so set `dry_run=false` when you want to print.

## 🧩 Notes

- When running scripts, set `PYTHONPATH=src`.
- Layout printing is rendered to images, so Japanese is supported.

## 🛠 Troubleshooting

### Debugging `printed=false`

The `info` field of `render_layout_job` includes (after server restart):

- `info.dry_run`
- `info.send_to_printer`
- `info.printer.address_present` (MAC is not returned, only presence)
- `info.printer.address_source` (`env`/`missing`, etc.)
- `info.reason_not_printed` (e.g., `"dry_run=true (preview only)"`)

Common causes:

- `dry_run=true` (preview only)
- Layout JSON sets `output.send_to_printer=false`
- `.env` lacks `PHOMEMO_PRINTER_ADDRESS` or Bluetooth is not connected

## 🗂 Repository structure

- `src/phomemo_agent/`: core implementation
  - `composer.py` / `printer.py` / `pipeline.py` / `validators.py`
  - `mcp/layout_server.py`: MCP server (tools/resources/prompts)
  - `cli/run_mcp_server.py`: MCP server CLI
- `schemas/layout_job.schema.json`: Layout JSON schema
- `env.example`: `.env` template
