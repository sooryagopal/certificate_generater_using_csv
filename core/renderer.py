"""
Renderer module for AURELIA — Bulk Certificate Generator.
Shared rendering engine used identically for both the interactive UI canvas
and high-resolution batch export (PDF/PNG/JPG).
Translates normalized (0.0 to 1.0) coordinates to exact pixel placements,
with full typography, text wrapping, tracking, outlines, rotation, and bounding box calculations.
"""

from __future__ import annotations
import math
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFont
if TYPE_CHECKING:
    from models.text_field import TextField
from core.font_manager import FontManager


class Renderer:
    """Core graphic rendering engine for certificates."""

    def __init__(self) -> None:
        self.font_manager = FontManager()

    def render_certificate(
        self,
        template_image: Image.Image,
        fields: List[TextField],
        record: Optional[Dict[str, Any]] = None,
        scale: float = 1.0,
    ) -> Image.Image:
        """
        Renders all visible fields onto a copy of the template image.
        
        Args:
            template_image: Source template PIL Image (RGB mode).
            fields: List of TextField objects.
            record: Dictionary mapping CSV column names to participant values.
            scale: Resolution scaling multiplier (1.0 for original, < 1.0 for UI thumbnails).

        Returns:
            Rendered PIL Image.
        """
        target_w = int(template_image.width * scale)
        target_h = int(template_image.height * scale)

        if scale != 1.0:
            base_img = template_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        else:
            base_img = template_image.copy()

        # Sort fields by layer order
        sorted_fields = sorted(fields, key=lambda f: f.order)

        for field_obj in sorted_fields:
            if not field_obj.is_visible:
                continue
            self._render_field(base_img, field_obj, record, target_w, target_h, scale)

        return base_img

    def _render_field(
        self,
        canvas: Image.Image,
        field_obj: TextField,
        record: Optional[Dict[str, Any]],
        canvas_w: int,
        canvas_h: int,
        scale: float,
    ) -> None:
        """Renders an individual TextField onto the canvas image."""
        text = field_obj.resolve_text(record)
        if not text:
            return

        scaled_font_size = max(6, int(field_obj.font_size * scale))
        font = self.font_manager.get_font(
            font_family=field_obj.font_family,
            font_path=field_obj.font_path,
            font_size=scaled_font_size,
            bold=field_obj.bold,
            italic=field_obj.italic,
        )

        # Handle text wrapping
        max_px_width = None
        if field_obj.wrap_text and field_obj.max_width:
            max_px_width = int(field_obj.max_width * canvas_w)

        lines = self._wrap_lines(text, font, max_px_width)
        if not lines:
            return

        # Measure dimensions
        line_heights = []
        line_widths = []
        for line in lines:
            w, h = self._measure_line(line, font, field_obj.letter_spacing * scale)
            line_widths.append(w)
            line_heights.append(h)

        max_line_w = max(line_widths) if line_widths else 0
        base_line_h = max(line_heights) if line_heights else scaled_font_size
        spacing_extra = int(base_line_h * (field_obj.line_spacing - 1.0))
        total_block_h = sum(line_heights) + spacing_extra * (len(lines) - 1)

        # Anchor origin from normalized coordinates
        origin_x = field_obj.x * canvas_w
        origin_y = field_obj.y * canvas_h

        # Compute block top-left based on horizontal & vertical alignment
        if field_obj.align_h == "center":
            block_left = origin_x - (max_line_w / 2.0)
        elif field_obj.align_h == "right":
            block_left = origin_x - max_line_w
        else:  # left
            block_left = origin_x

        if field_obj.align_v == "center":
            block_top = origin_y - (total_block_h / 2.0)
        elif field_obj.align_v == "bottom":
            block_top = origin_y - total_block_h
        else:  # top
            block_top = origin_y

        # If rotation is required, render to RGBA overlay
        if abs(field_obj.rotation) > 0.1:
            self._render_rotated(
                canvas, lines, font, field_obj, block_left, block_top,
                max_line_w, total_block_h, line_heights, spacing_extra, scale
            )
            return

        draw = ImageDraw.Draw(canvas)

        # Draw background highlight if configured
        if field_obj.bg_color:
            pad = int(8 * scale)
            bg_rect = [
                block_left - pad,
                block_top - pad,
                block_left + max_line_w + pad,
                block_top + total_block_h + pad,
            ]
            draw.rectangle(bg_rect, fill=field_obj.bg_color)

        # Draw text line by line
        curr_y = block_top
        stroke_w = int(field_obj.stroke_width * scale) if field_obj.stroke_color else 0

        for idx, line in enumerate(lines):
            line_w = line_widths[idx]
            line_h = line_heights[idx]

            # Line horizontal alignment relative to block
            if field_obj.align_h == "center":
                curr_x = block_left + ((max_line_w - line_w) / 2.0)
            elif field_obj.align_h == "right":
                curr_x = block_left + (max_line_w - line_w)
            else:
                curr_x = block_left

            self._draw_single_line(
                draw=draw,
                line=line,
                font=font,
                x=curr_x,
                y=curr_y,
                text_color=field_obj.text_color,
                stroke_color=field_obj.stroke_color,
                stroke_width=stroke_w,
                letter_spacing=int(field_obj.letter_spacing * scale),
            )

            curr_y += line_h + spacing_extra

    def _draw_single_line(
        self,
        draw: ImageDraw.ImageDraw,
        line: str,
        font: ImageFont.FreeTypeFont,
        x: float,
        y: float,
        text_color: str,
        stroke_color: Optional[str] = None,
        stroke_width: int = 0,
        letter_spacing: int = 0,
    ) -> None:
        """Draws one line with optional letter spacing tracking and stroke."""
        if letter_spacing <= 0:
            draw.text(
                (x, y),
                line,
                font=font,
                fill=text_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color if stroke_width > 0 else None,
            )
        else:
            # Draw character-by-character for custom letter spacing
            cursor_x = x
            for char in line:
                draw.text(
                    (cursor_x, y),
                    char,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color if stroke_width > 0 else None,
                )
                bbox = font.getbbox(char)
                char_w = (bbox[2] - bbox[0]) if bbox else 10
                cursor_x += char_w + letter_spacing

    def _render_rotated(
        self,
        canvas: Image.Image,
        lines: List[str],
        font: ImageFont.FreeTypeFont,
        field_obj: TextField,
        block_left: float,
        block_top: float,
        block_w: float,
        block_h: float,
        line_heights: List[int],
        spacing_extra: int,
        scale: float,
    ) -> None:
        """Renders rotated text via temporary transparent RGBA layer."""
        pad = int(20 * scale)
        layer_w = int(block_w + pad * 2)
        layer_h = int(block_h + pad * 2)

        overlay = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if field_obj.bg_color:
            draw.rectangle([pad, pad, pad + block_w, pad + block_h], fill=field_obj.bg_color)

        curr_y = pad
        stroke_w = int(field_obj.stroke_width * scale) if field_obj.stroke_color else 0

        for idx, line in enumerate(lines):
            line_w, line_h = self._measure_line(line, font, field_obj.letter_spacing * scale)
            if field_obj.align_h == "center":
                curr_x = pad + ((block_w - line_w) / 2.0)
            elif field_obj.align_h == "right":
                curr_x = pad + (block_w - line_w)
            else:
                curr_x = pad

            self._draw_single_line(
                draw=draw,
                line=line,
                font=font,
                x=curr_x,
                y=curr_y,
                text_color=field_obj.text_color,
                stroke_color=field_obj.stroke_color,
                stroke_width=stroke_w,
                letter_spacing=int(field_obj.letter_spacing * scale),
            )
            curr_y += line_heights[idx] + spacing_extra

        # Rotate overlay counter-clockwise or clockwise
        rotated = overlay.rotate(
            field_obj.rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

        center_x = block_left + block_w / 2.0
        center_y = block_top + block_h / 2.0
        paste_x = int(center_x - rotated.width / 2.0)
        paste_y = int(center_y - rotated.height / 2.0)

        canvas.paste(rotated, (paste_x, paste_y), rotated)

    def _wrap_lines(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: Optional[int]
    ) -> List[str]:
        """Splits multiline strings and applies word wrapping if max_width is exceeded."""
        raw_lines = text.splitlines() or [""]
        if not max_width or max_width <= 0:
            return raw_lines

        wrapped_lines: List[str] = []
        for line in raw_lines:
            words = line.split(" ")
            if not words or not line.strip():
                wrapped_lines.append("")
                continue

            current_line: List[str] = []
            for word in words:
                test_line = " ".join(current_line + [word])
                bbox = font.getbbox(test_line)
                test_w = (bbox[2] - bbox[0]) if bbox else 0

                if test_w <= max_width or not current_line:
                    current_line.append(word)
                else:
                    wrapped_lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                wrapped_lines.append(" ".join(current_line))

        return wrapped_lines

    def _measure_line(
        self, line: str, font: ImageFont.FreeTypeFont, letter_spacing: float = 0
    ) -> Tuple[int, int]:
        """Computes pixel width and height of a line including character spacing."""
        if not line:
            # Empty line measurement
            bbox = font.getbbox("Aj")
            return 0, (bbox[3] - bbox[1]) if bbox else 24

        bbox = font.getbbox(line)
        if not bbox:
            return 0, 24

        base_w = bbox[2] - bbox[0]
        base_h = bbox[3] - bbox[1]

        if letter_spacing > 0:
            extra_w = int(letter_spacing * max(0, len(line) - 1))
            return base_w + extra_w, base_h

        return base_w, base_h

    def calculate_field_bbox(
        self,
        field_obj: TextField,
        template_width: int,
        template_height: int,
        record: Optional[Dict[str, Any]] = None,
        scale: float = 1.0,
    ) -> Tuple[float, float, float, float]:
        """
        Calculates the bounding box (left, top, right, bottom) of a field in pixel coordinates.
        Essential for selection bounding boxes, hover handles, and drag hit-testing.
        """
        text = field_obj.resolve_text(record)
        if not text:
            text = field_obj.name or "Text Field"

        scaled_font_size = max(6, int(field_obj.font_size * scale))
        font = self.font_manager.get_font(
            font_family=field_obj.font_family,
            font_path=field_obj.font_path,
            font_size=scaled_font_size,
            bold=field_obj.bold,
            italic=field_obj.italic,
        )

        scaled_w = int(template_width * scale)
        scaled_h = int(template_height * scale)

        max_px_width = None
        if field_obj.wrap_text and field_obj.max_width:
            max_px_width = int(field_obj.max_width * scaled_w)

        lines = self._wrap_lines(text, font, max_px_width)
        line_widths = []
        line_heights = []
        for line in lines:
            w, h = self._measure_line(line, font, field_obj.letter_spacing * scale)
            line_widths.append(w)
            line_heights.append(h)

        max_line_w = max(line_widths) if line_widths else int(100 * scale)
        base_line_h = max(line_heights) if line_heights else scaled_font_size
        spacing_extra = int(base_line_h * (field_obj.line_spacing - 1.0))
        total_block_h = sum(line_heights) + spacing_extra * max(0, len(lines) - 1)

        origin_x = field_obj.x * scaled_w
        origin_y = field_obj.y * scaled_h

        if field_obj.align_h == "center":
            block_left = origin_x - (max_line_w / 2.0)
        elif field_obj.align_h == "right":
            block_left = origin_x - max_line_w
        else:
            block_left = origin_x

        if field_obj.align_v == "center":
            block_top = origin_y - (total_block_h / 2.0)
        elif field_obj.align_v == "bottom":
            block_top = origin_y - total_block_h
        else:
            block_top = origin_y

        block_right = block_left + max_line_w
        block_bottom = block_top + total_block_h

        return (block_left, block_top, block_right, block_bottom)
