from __future__ import annotations

import json
from dataclasses import dataclass
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from .composer import compose_canvas, to_thermal_ready
from .constants import DEFAULT_CHUNK_ROWS, DEFAULT_SLICE_HEIGHT, DEFAULT_THRESHOLD
from .printer import transmit
from .validators import LayoutJobValidator


@dataclass
class LayoutJobResult:
    preview_path: Optional[Path]
    printed: bool
    slice_heights: Optional[list[int]]
    info: Dict


class LayoutJobPipeline:
    """
    JSONレイアウトの生成→画像合成→印刷までを一貫して扱う。
    """

    def __init__(self, validator: Optional[LayoutJobValidator] = None) -> None:
        self.validator = validator or LayoutJobValidator()

    def run(
        self,
        job_config_path: Path,
        printer_address: Optional[str] = None,
        printer_channel: int = 1,
        encoding: str = "utf-8",
        dry_run: bool = False,
    ) -> LayoutJobResult:
        config = json.loads(job_config_path.read_text(encoding="utf-8"))
        self.validator.validate(config)

        composed_image, output_cfg = compose_canvas(config, encoding=encoding)

        rotate_mode = str(output_cfg.get("rotate", "auto")).lower()
        composed_image = self._apply_orientation(composed_image, rotate_mode)

        threshold = output_cfg.get("threshold", DEFAULT_THRESHOLD)
        slice_height = output_cfg.get("slice_height", DEFAULT_SLICE_HEIGHT)
        chunk_rows = output_cfg.get("chunk_rows", DEFAULT_CHUNK_ROWS)
        output_path = output_cfg.get("path")
        send_to_printer = output_cfg.get("send_to_printer", True) and not dry_run

        preview_path = None
        # プレビュー保存先:
        # - output.path 指定あり: その場所へ
        # - output.path なし & dry_run: /tmp に自動生成して返す（artifacts不要化）
        if output_path or dry_run:
            if output_path:
                preview_path = Path(output_path)
                # 相対パスはジョブJSONのあるディレクトリ基準で解決する
                if not preview_path.is_absolute():
                    preview_path = (job_config_path.parent / preview_path)
                preview_path = preview_path.resolve()
            else:
                fd, tmp_name = tempfile.mkstemp(prefix="phomemo_preview_", suffix=".png")
                os.close(fd)
                preview_path = Path(tmp_name).resolve()

            preview_path.parent.mkdir(parents=True, exist_ok=True)
            composed_image.save(preview_path, format="PNG")

        bw_image = to_thermal_ready(composed_image, threshold)
        slice_heights: Optional[list[int]] = None

        # Printer config from env (if not explicitly provided)
        printer_address_source = "argument" if printer_address else "env"
        if printer_address is None:
            printer_address = os.getenv("PHOMEMO_PRINTER_ADDRESS")
            if not printer_address:
                printer_address_source = "missing"

        printer_channel_source = "argument"
        if (not printer_channel) or printer_channel == 1:
            # allow overriding default(1) by env var
            env_channel = os.getenv("PHOMEMO_PRINTER_CHANNEL")
            if env_channel:
                try:
                    printer_channel = int(env_channel)
                    printer_channel_source = "env"
                except ValueError:
                    pass

        if send_to_printer:
            from phomemo_printer.ESCPOS_printer import Printer

            if not printer_address:
                raise ValueError("send_to_printer=True の場合は printer_address が必要です。")

            printer = Printer(printer_address, printer_channel)
            try:
                slice_heights = transmit(printer, bw_image, slice_height, chunk_rows)
            finally:
                printer.close()

        reason_not_printed: str | None = None
        if not send_to_printer:
            # printed=false の典型原因を一言で返す（LLMが環境変数確認などを過剰に聞かないため）
            if dry_run:
                reason_not_printed = "dry_run=true (preview only)"
            else:
                reason_not_printed = "output.send_to_printer=false"

        return LayoutJobResult(
            preview_path=preview_path,
            printed=bool(send_to_printer),
            slice_heights=slice_heights,
            info={
                "threshold": threshold,
                "slice_height": slice_height,
                "chunk_rows": chunk_rows,
                "rotate": rotate_mode,
                "width": bw_image.width,
                "height": bw_image.height,
                "dry_run": bool(dry_run),
                "send_to_printer": bool(send_to_printer),
                "printer": {
                    # セキュリティ/ログ配慮でMACアドレス本体は返さない（存在有無と取得元のみ）
                    "address_present": bool(printer_address),
                    "address_source": printer_address_source,
                    "channel": int(printer_channel),
                    "channel_source": printer_channel_source,
                },
                "reason_not_printed": reason_not_printed,
            },
        )

    def _apply_orientation(self, image: Image.Image, rotate_mode: str) -> Image.Image:
        """
        - rotate_mode:
          - "none": 回転しない
          - "auto": 横長(width>height)のとき90度回転（phomemo_printerのprint_image互換の感覚）
          - "cw90": 常に時計回り90度回転
          - "ccw90": 常に反時計回り90度回転
        """
        if rotate_mode in ("none", "0", "false"):
            return image

        should_rotate = False
        if rotate_mode == "auto":
            should_rotate = image.width > image.height
        elif rotate_mode == "cw90":
            should_rotate = True
            rotate_op = Image.ROTATE_90
        elif rotate_mode == "ccw90":
            should_rotate = True
            rotate_op = Image.ROTATE_270
        else:
            # unknown => behave like auto
            should_rotate = image.width > image.height
            rotate_op = Image.ROTATE_90

        if should_rotate:
            rotate_op = rotate_op if "rotate_op" in locals() else Image.ROTATE_90
            rotated = image.transpose(rotate_op)
            # 幅576に合わせる: 576より狭ければパディング、広ければ縮小
            if rotated.width < 576:
                bg = Image.new("RGBA", (576, rotated.height), (255, 255, 255, 255))
                x = (576 - rotated.width) // 2
                bg.paste(rotated, (x, 0), mask=rotated if rotated.mode == "RGBA" else None)
                return bg
            if rotated.width > 576:
                new_h = max(1, int(rotated.height * 576 / rotated.width))
                return rotated.resize((576, new_h), resample=Image.LANCZOS)
            return rotated

        # 念のため幅がズレていたら縮小/拡張はせずパディング
        if image.width < 576:
            bg = Image.new("RGBA", (576, image.height), (255, 255, 255, 255))
            x = (576 - image.width) // 2
            bg.paste(image, (x, 0), mask=image if image.mode == "RGBA" else None)
            return bg
        if image.width > 576:
            new_h = max(1, int(image.height * 576 / image.width))
            return image.resize((576, new_h), resample=Image.LANCZOS)
        return image
