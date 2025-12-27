from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phomemo_agent.pipeline import LayoutJobPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Phomemo layout JSON.")
    parser.add_argument("json_path", type=Path, help="Path to layout JSON")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview only (do not send to printer)",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        default=False,
        help="Send to printer (overrides --dry-run)",
    )
    parser.add_argument("--encoding", default="utf-8", help="Text encoding")
    args = parser.parse_args()

    if not args.json_path.exists():
        print("error: json file not found", file=sys.stderr)
        return 2

    dry_run = True
    if args.print:
        dry_run = False
    elif args.dry_run:
        dry_run = True

    pipeline = LayoutJobPipeline()
    try:
        result = pipeline.run(
            job_config_path=args.json_path,
            printer_address=None,
            printer_channel=1,
            encoding=args.encoding,
            dry_run=dry_run,
        )
    except Exception as exc:
        error_message = f"render failed: {exc}"
        print(f"error: {error_message}", file=sys.stderr)
        print(
            json.dumps(
                {
                    "preview_path": "",
                    "printed": False,
                    "slice_heights": None,
                    "info": {"error": error_message},
                },
                ensure_ascii=False,
            )
        )
        return 1

    payload = {
        "preview_path": str(result.preview_path or ""),
        "printed": result.printed,
        "slice_heights": result.slice_heights,
        "info": result.info,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
