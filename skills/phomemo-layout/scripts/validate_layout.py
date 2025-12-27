from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phomemo_agent.validators import LayoutJobValidator


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phomemo layout JSON.")
    parser.add_argument("json_path", type=Path, help="Path to layout JSON")
    args = parser.parse_args()

    if not args.json_path.exists():
        print("error: json file not found", file=sys.stderr)
        return 2

    try:
        payload = json.loads(args.json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid json: {exc}", file=sys.stderr)
        return 2

    try:
        validator = LayoutJobValidator()
        validator.validate(payload)
    except Exception as exc:
        print(f"error: validation failed: {exc}", file=sys.stderr)
        return 1

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
