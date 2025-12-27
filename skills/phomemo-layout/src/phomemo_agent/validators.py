from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "layout_job.schema.json"


class LayoutJobValidator:
    def __init__(self, schema_path: Path | None = None) -> None:
        self.schema_path = schema_path or SCHEMA_PATH
        self._validator = self._load_validator()

    @lru_cache(maxsize=1)
    def _load_validator(self) -> Draft202012Validator:
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        return Draft202012Validator(schema)

    def validate(self, config: Dict) -> None:
        errors = sorted(self._validator.iter_errors(config), key=lambda e: e.path)
        if errors:
            formatted = "\n".join(
                f"- {'/'.join(map(str, err.absolute_path)) or '(root)'}: {err.message}"
                for err in errors
            )
            raise ValueError(f"layout job schema validation failed:\n{formatted}")
