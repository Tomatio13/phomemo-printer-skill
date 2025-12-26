from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageColor
from imagetext_py import (
    Canvas,
    Color,
    EmojiOptions,
    EmojiSource,
    Font,
    Paint,
    TextAlign,
    WrapStyle,
    draw_text_multiline,
    text_size_multiline,
    text_wrap,
)

from .constants import CANVAS_WIDTH

ALIGN_MAP = {
    "left": TextAlign.Left,
    "center": TextAlign.Center,
    "right": TextAlign.Right,
}

WRAP_STYLE_MAP = {
    "word": WrapStyle.Word,
    "character": WrapStyle.Character,
}

EMOJI_SOURCE_MAP = {
    "twitter": EmojiSource.Twitter,
    "apple": EmojiSource.Apple,
    "google": EmojiSource.Google,
    "microsoft": EmojiSource.Microsoft,
    "samsung": EmojiSource.Samsung,
    "whatsapp": EmojiSource.WhatsApp,
    "joypixels": EmojiSource.JoyPixels,
    "openmoji": EmojiSource.OpenMoji,
    "emojidex": EmojiSource.Emojidex,
    "messenger": EmojiSource.Messenger,
    "mozilla": EmojiSource.Mozilla,
    "lg": EmojiSource.Lg,
    "htc": EmojiSource.Htc,
    "twemoji": EmojiSource.Twemoji,
}


@dataclass
class RenderedLayer:
    image: Image.Image
    position: Tuple[int, int]


def hex_to_rgba(value: str) -> Tuple[int, int, int, int]:
    color = ImageColor.getcolor(value, "RGBA")
    return tuple(color)


def build_font(
    font_path: str,
    fallback_fonts: Sequence[str],
    emoji_cfg: Dict,
) -> Font:
    shift = emoji_cfg.get("shift", [0, 0])
    shift_tuple = (int(round(shift[0])), int(round(shift[1]))) if len(shift) == 2 else (0, 0)

    source_name = str(emoji_cfg.get("source", "google")).lower()
    source_factory = EMOJI_SOURCE_MAP.get(source_name, EmojiSource.Google)

    emoji_options = EmojiOptions(
        scale=emoji_cfg.get("scale", 1.0),
        shift=shift_tuple,
        parse_shortcodes=emoji_cfg.get("parse_shortcodes", True),
        parse_discord_emojis=emoji_cfg.get("parse_discord", False),
        source=source_factory(),
    )
    return Font(str(font_path), fallbacks=[str(p) for p in fallback_fonts], emoji_options=emoji_options)


def ensure_text(layer: Dict, encoding: str) -> str:
    if "text" in layer and layer["text"] is not None:
        return layer["text"]
    if "text_file" in layer:
        return Path(layer["text_file"]).read_text(encoding=layer.get("encoding", encoding))
    raise ValueError("text layer には text または text_file の指定が必要です")


def render_text_layer(
    layer: Dict,
    canvas_width: int,
    global_defaults: Dict,
    encoding: str,
) -> RenderedLayer:
    text = ensure_text(layer, encoding=layer.get("encoding", encoding))
    font_path = layer.get("font_path") or global_defaults.get("font_path")
    if not font_path:
        raise ValueError("font_path が指定されていません (canvas.font_path もしくは layer.font_path が必要)")
    fallback_fonts = [
        str(p) for p in layer.get("fallback_fonts", global_defaults.get("fallback_fonts", []))
    ]
    emoji_cfg = {**global_defaults.get("emoji", {}), **layer.get("emoji", {})}
    font = build_font(font_path, fallback_fonts, emoji_cfg)

    font_size = layer.get("font_size", global_defaults.get("font_size", 32))
    line_spacing = layer.get("line_spacing", global_defaults.get("line_spacing", 1.2))
    wrap_style_name = layer.get("wrap_style", global_defaults.get("wrap_style", "character"))
    wrap_style = WRAP_STYLE_MAP.get(wrap_style_name.lower(), WrapStyle.Character)

    margin = global_defaults.get("margin", 20)
    width = layer.get("width", canvas_width - margin * 2)
    width = max(1, int(width))

    lines: List[str] = []
    paragraphs = text.splitlines() or [""]
    for paragraph in paragraphs:
        if paragraph == "":
            lines.append("")
            continue
        wrapped = text_wrap(
            text=paragraph,
            width=width,
            size=font_size,
            font=font,
            draw_emojis=True,
            wrap_style=wrap_style,
        )
        lines.extend(wrapped or [""])
    if not lines:
        lines = [""]

    _, text_height = text_size_multiline(
        lines=lines,
        size=font_size,
        font=font,
        line_spacing=line_spacing,
        draw_emojis=True,
    )
    height = max(int(text_height), int(font_size))

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas = Canvas.from_image(img)

    stroke_cfg = layer.get("stroke") or {}
    stroke_width = stroke_cfg.get("width", 0)
    stroke_color = stroke_cfg.get("color", "#FFFFFF")
    stroke = stroke_width if stroke_width > 0 else None
    stroke_paint = Paint.Color(Color(*hex_to_rgba(stroke_color))) if stroke is not None else None

    align = ALIGN_MAP.get(layer.get("align", "left").lower(), TextAlign.Left)

    draw_text_multiline(
        canvas=canvas,
        lines=lines,
        x=0,
        y=0,
        ax=0.0,
        ay=0.0,
        width=width,
        size=font_size,
        font=font,
        fill=Paint.Color(Color(0, 0, 0, 255)),
        line_spacing=line_spacing,
        align=align,
        stroke=stroke,
        stroke_color=stroke_paint,
        draw_emojis=True,
    )

    position = layer.get("position", {})
    x = int(position.get("x", margin))
    y = int(position.get("y", margin))
    return RenderedLayer(canvas.to_image(), (x, y))


def render_image_layer(layer: Dict) -> RenderedLayer:
    if "path" not in layer:
        raise ValueError("image layerにはpathが必要です")
    path = Path(layer["path"])
    if not path.exists():
        raise FileNotFoundError(f"画像が見つかりません: {path}")
    img = Image.open(path).convert("RGBA")

    max_width = layer.get("max_width")
    max_height = layer.get("max_height")
    scale = layer.get("scale")

    if scale:
        img = img.resize(
            (int(img.width * float(scale)), int(img.height * float(scale))),
            resample=Image.LANCZOS,
        )
    if max_width:
        max_width = float(max_width)
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((int(max_width), int(img.height * ratio)), Image.LANCZOS)
    if max_height:
        max_height = float(max_height)
        if img.height > max_height:
            ratio = max_height / img.height
            img = img.resize((int(img.width * ratio), int(max_height)), Image.LANCZOS)

    opacity = layer.get("opacity", 1.0)
    if opacity < 1.0:
        alpha = img.split()[-1].point(lambda p: int(p * opacity))
        img.putalpha(alpha)

    position = layer.get("position", {})
    x = int(position.get("x", 0))
    y = int(position.get("y", 0))
    return RenderedLayer(img, (x, y))


def slice_image(image: Image.Image, max_height: int) -> List[Image.Image]:
    if max_height <= 0 or image.height <= max_height:
        return [image]
    slices: List[Image.Image] = []
    for start in range(0, image.height, max_height):
        end = min(start + max_height, image.height)
        slices.append(image.crop((0, start, image.width, end)))
    return slices


def to_thermal_ready(image: Image.Image, threshold: int) -> Image.Image:
    gray = image.convert("L")
    return gray.point(lambda x: 0 if x < threshold else 255, mode="1")


def compose_canvas(config: Dict, encoding: str = "utf-8") -> Tuple[Image.Image, Dict]:
    canvas_cfg = config.get("canvas", {})
    global_defaults = {
        "font_path": canvas_cfg.get("font_path"),
        "fallback_fonts": [str(p) for p in canvas_cfg.get("fallback_fonts", [])],
        "font_size": canvas_cfg.get("font_size", 32),
        "line_spacing": canvas_cfg.get("line_spacing", 1.2),
        "wrap_style": canvas_cfg.get("wrap_style", "character"),
        "margin": canvas_cfg.get("margin", 20),
        "emoji": canvas_cfg.get("emoji", {}),
    }

    if not global_defaults["font_path"]:
        raise ValueError("canvas.font_path は必須です")

    layers = config.get("layers", [])
    if not layers:
        raise ValueError("layers が空です")

    rendered_layers: List[RenderedLayer] = []
    for layer in layers:
        layer_type = layer.get("type")
        if layer_type == "text":
            rendered = render_text_layer(layer, CANVAS_WIDTH, global_defaults, encoding)
        elif layer_type == "image":
            rendered = render_image_layer(layer)
        else:
            raise ValueError(f"未知のレイヤーtypeです: {layer_type}")
        rendered_layers.append(rendered)

    height = canvas_cfg.get("height")
    if height is None:
        max_bottom = 0
        for rendered in rendered_layers:
            img, (x, y) = rendered.image, rendered.position
            max_bottom = max(max_bottom, y + img.height)
        height = max_bottom + global_defaults["margin"]

    background_color = canvas_cfg.get("background_color", "#FFFFFF")
    base = Image.new("RGBA", (CANVAS_WIDTH, int(height)), hex_to_rgba(background_color))

    for rendered in rendered_layers:
        img, (x, y) = rendered.image, rendered.position
        base.paste(img, (x, y), mask=img)

    return base, config.get("output", {})
