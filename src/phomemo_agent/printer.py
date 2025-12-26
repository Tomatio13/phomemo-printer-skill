from __future__ import annotations

from typing import List

from PIL import Image

from phomemo_printer.ESCPOS_constants import FOOTER, GSV0, HEADER, PRINT_FEED
from phomemo_printer.ESCPOS_printer import Printer

from .composer import slice_image
from .constants import CANVAS_WIDTH


def _send_slice(printer: Printer, image: Image.Image, chunk_rows: int) -> None:
    if image.mode != "1":
        image = image.convert("1")
    if image.width != CANVAS_WIDTH:
        raise ValueError(f"画像幅は{CANVAS_WIDTH}pxである必要があります。")
    if chunk_rows <= 0 or chunk_rows > 256:
        raise ValueError("chunk_rowsは1-256で指定してください。")

    width_bytes = image.width // 8
    pixels = image.load()
    height = image.height

    for start_row in range(0, height, chunk_rows):
        block_height = min(chunk_rows, height - start_row)
        block_marker = (
            GSV0
            + bytes([width_bytes])
            + b"\x00"
            + bytes([block_height - 1])
            + b"\x00"
        )
        printer._print_bytes(block_marker)

        for row_offset in range(block_height):
            y = start_row + row_offset
            line = bytearray()
            for byte_start in range(width_bytes):
                byte = 0
                for bit in range(8):
                    x = byte_start * 8 + bit
                    if pixels[x, y] == 0:
                        byte |= 1 << (7 - bit)
                if byte == 0x0A:
                    byte = 0x14
                line.append(byte)
            printer._print_bytes(bytes(line))


def transmit(printer: Printer, image: Image.Image, slice_height: int, chunk_rows: int) -> List[int]:
    slices = slice_image(image, slice_height)
    printer._print_bytes(HEADER)
    heights: List[int] = []
    for index, slice_img in enumerate(slices):
        _send_slice(printer, slice_img, chunk_rows)
        heights.append(slice_img.height)
        printer._print_bytes(PRINT_FEED)
        if index != len(slices) - 1:
            printer._print_bytes(PRINT_FEED)
    printer._print_bytes(PRINT_FEED)
    printer._print_bytes(FOOTER)
    return heights
