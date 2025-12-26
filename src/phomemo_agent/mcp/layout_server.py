from __future__ import annotations

import json
import tempfile
from pathlib import Path
import os
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

from ..pipeline import LayoutJobPipeline
from ..validators import LayoutJobValidator

pipeline = LayoutJobPipeline()
validator = LayoutJobValidator()

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "schemas" / "layout_job.schema.json"
SAMPLE_PATH = REPO_ROOT / "Docs" / "layout.sample.json"


def _read_text_if_exists(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _printer_spec_markdown() -> str:
    return """# Phomemo M02 Pro 印刷仕様（レイアウト設計用）

## 物理/画像制約
- **幅は常に 576px 固定**（M02 Proの印字幅に合わせる）
- 背景は白（#FFFFFF）、文字は黒を基本
- 出力は最終的に**しきい値で2値化**される（`output.threshold`）

## 実寸換算（重要）
- M02 Pro（300dpi想定）では、おおよそ **300px = 1 inch** です
- cm → px の目安:
  - `px = cm / 2.54 * 300`
  - 例: **5cm ≒ 591px**
- 逆に、固定幅 576px は `576 / 300 * 2.54 ≒ 4.88cm` なので、
  - **横方向（X方向）だけで5cmを表現するのは物理的に不可能**です
  - 5cm以上の長さが必要な表現（定規/長尺メモ等）は **紙送り方向（Y方向=画像の高さ）** で長さを確保してください

## 長尺データ送信の注意
- Bluetooth送信で途中停止する場合があるため、画像を縦方向に分割して送る
- `output.slice_height`（例: 1400）で画像をスライス
- `output.chunk_rows`（例: 200、1〜256）で送信ブロックを小さくする

## JSONレイアウトの基本
- `canvas` / `layers` / `output` を必ず含める
- `layers[].type` は `text` または `image`
- `text` レイヤーは `text` または `text_file` のどちらかを持つ
- `image` レイヤーは `path` を持つ（ローカルファイル）

## フォント
- `canvas.font_path` は **存在するフォントパスのみ**を指定（存在しないパスを創作しない）
- 候補例（環境により存在するものを使う）:
  - `/usr/local/share/fonts/HackGen_NF/HackGenConsoleNFJ-Regular.ttf`
  - `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
  - 絵文字は `/usr/local/share/fonts/NotoEmoji-Regular.ttf` などを `fallback_fonts` へ

## レイアウト品質のヒント
- 余白: `canvas.margin` を 20〜40 程度
- テキスト幅: おおむね `576 - margin*2`
- 文字が潰れる場合は `font_size` を上げるか細いウェイトのフォントに切替

## 方向（縦横）について
- 実機側の見え方によっては「縦横が逆」に感じることがあります。
- `output.rotate` で回転を制御できます:
  - `auto`: 横長（width > height）のとき90度回転（既定）
  - `none`: 回転しない
  - `cw90` / `ccw90`: 強制回転
- **長尺スキル（例: “5cm以上の定規”）は回転に頼らず、最初からY方向に必要pxを確保する**のが確実です（例: 5cm→高さ591px以上）。
"""


def build_server(host: str, port: int) -> FastMCP:
    server = FastMCP(
        "PhomemoLayoutServer",
        host=host,
        port=port,
    )

    # -------------------------
    # Resources (LLMに仕様を渡す)
    # -------------------------
    @server.resource(
        "phomemo://printer/spec.md",
        title="Phomemo Printer Spec (Markdown)",
        mime_type="text/markdown",
        description="Phomemo M02 Pro向けのレイアウト設計仕様（幅576px固定、分割送信など）",
    )
    def printer_spec_resource() -> str:
        return _printer_spec_markdown()

    @server.resource(
        "phomemo://layout/schema.json",
        title="Layout Job JSON Schema",
        mime_type="application/json",
        description="PhomemoレイアウトJSONのスキーマ",
    )
    def layout_schema_resource() -> str:
        return _read_text_if_exists(SCHEMA_PATH)

    @server.resource(
        "phomemo://layout/example.json",
        title="Layout Job Example",
        mime_type="application/json",
        description="レイアウトJSONのサンプル",
    )
    def layout_example_resource() -> str:
        return _read_text_if_exists(SAMPLE_PATH)

    # -------------------------
    # Prompts (Strands側に与える雛形)
    # -------------------------
    @server.prompt(
        name="phomemo_layout_json_generator",
        title="Generate Phomemo layout JSON",
        description="プリンタ仕様とスキーマを踏まえて、レイアウトJSONのみを返すためのプロンプト雛形",
    )
    def phomemo_layout_json_generator(user_request: str) -> list[dict]:
        schema_text = _read_text_if_exists(SCHEMA_PATH)
        example_text = _read_text_if_exists(SAMPLE_PATH)
        spec_text = _printer_spec_markdown()
        return [
            {
                "role": "system",
                "content": "あなたは熱転写プリンタ(Phomemo M02 Pro)向けのレイアウト設計者です。必ずJSONのみを返してください。",
            },
            {
                "role": "user",
                "content": f"""以下の仕様・スキーマ・例を読み、ユーザー要望を満たすレイアウトJSONを生成してください。

## ユーザー要望
{user_request}

## プリンタ仕様
{spec_text}

## JSON Schema
{schema_text}

## Example JSON
{example_text}

### 厳守事項
- 出力は **JSONのみ**（説明文、Markdown、コードブロック禁止）
- `canvas`/`layers`/`output` を含める
- `canvas.font_path` は存在するパスのみ（不明なら例のパスを使う）
""",
            },
        ]

    # -------------------------
    # Tools (LLMが段階的に参照できる)
    # -------------------------
    @server.tool(
        name="get_printer_spec",
        description="Phomemo M02 Proの印刷仕様（幅576px固定、送信分割など）を返す",
    )
    def get_printer_spec() -> str:
        return _printer_spec_markdown()

    @server.tool(
        name="get_layout_schema",
        description="レイアウトJSONのスキーマ(JSON Schema)を返す",
    )
    def get_layout_schema() -> Dict[str, Any]:
        return json.loads(_read_text_if_exists(SCHEMA_PATH) or "{}")

    @server.tool(
        name="get_layout_examples",
        description="レイアウトJSONの例を返す",
    )
    def get_layout_examples() -> List[Dict[str, Any]]:
        text = _read_text_if_exists(SAMPLE_PATH)
        if not text:
            return []
        return [json.loads(text)]

    @server.tool(
        name="validate_layout",
        description="レイアウトJSONをスキーマ検証し、エラーがあれば返す（印刷はしない）",
    )
    def validate_layout(layout: Dict[str, Any]) -> Dict[str, Any]:
        validator.validate(layout)
        return {"ok": True}

    @server.tool(
        name="render_layout_job",
        description="Phomemo向けレイアウトJSONを検証し、プレビュー/印刷を実行します。",
    )
    def render_layout_job(
        layout: Dict[str, Any],
        printer_address: Optional[str] = None,
        channel: Optional[int] = None,
        dry_run: bool = True,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        validator.validate(layout)
        if printer_address is None:
            printer_address = os.getenv("PHOMEMO_PRINTER_ADDRESS")
        if channel is None:
            env_channel = os.getenv("PHOMEMO_PRINTER_CHANNEL")
            channel = int(env_channel) if env_channel else 1
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(json.dumps(layout, ensure_ascii=False).encode("utf-8"))

        try:
            result = pipeline.run(
                job_config_path=tmp_path,
                printer_address=printer_address,
                printer_channel=int(channel),
                encoding=encoding,
                dry_run=dry_run,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        return {
            "preview_path": str(result.preview_path or ""),
            "printed": result.printed,
            "slice_heights": result.slice_heights,
            "info": result.info,
        }

    return server


def run_server(transport: str, host: str = "127.0.0.1", port: int = 8000) -> None:
    server = build_server(host=host, port=port)
    if transport == "stdio":
        server.run(transport="stdio")
    elif transport == "sse":
        server.run(transport="sse")
    else:
        raise ValueError("transport must be 'stdio' or 'sse'")
