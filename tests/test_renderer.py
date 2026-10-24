"""
Unit tests for Renderer module in AURELIA.
Tests text rendering, normalized coordinate positioning, scaling, text wrapping, and bounding box math.
"""

from PIL import Image
from models.text_field import TextField
from core.renderer import Renderer


def test_normalized_coordinate_calculations():
    renderer = Renderer()
    template_w, template_h = 1000, 800
    img = Image.new("RGB", (template_w, template_h), "#101014")

    # Center-aligned field at (0.50, 0.40)
    field = TextField(
        name="Name",
        column_name="Name",
        x=0.50,
        y=0.40,
        font_size=40,
        align_h="center",
        align_v="center",
    )

    bbox = renderer.calculate_field_bbox(
        field_obj=field,
        template_width=template_w,
        template_height=template_h,
        record={"Name": "Soorya G"},
        scale=1.0,
    )
    # Bbox is (left, top, right, bottom)
    left, top, right, bottom = bbox
    center_x = (left + right) / 2.0
    center_y = (top + bottom) / 2.0

    # Must be centered around x = 500 px (0.50 * 1000) and y = 320 px (0.40 * 800)
    assert abs(center_x - 500) < 5.0
    assert abs(center_y - 320) < 5.0


def test_text_rendering_on_template():
    renderer = Renderer()
    template = Image.new("RGB", (800, 600), "#0B0B0D")

    fields = [
        TextField(name="Title", is_static=True, static_text="Certificate", x=0.5, y=0.2, font_size=32),
        TextField(name="Name", column_name="Name", x=0.5, y=0.5, font_size=40, text_color="#D4AF37"),
    ]

    rendered = renderer.render_certificate(
        template_image=template,
        fields=fields,
        record={"Name": "Prathisha S"},
        scale=1.0,
    )

    assert rendered.size == (800, 600)
    # The rendered image should not be identical to blank template (pixels were modified)
    assert rendered.tobytes() != template.tobytes()


def test_text_wrapping_and_letter_spacing():
    renderer = Renderer()
    template = Image.new("RGB", (600, 400), "#FFFFFF")

    # Long text with wrapping enabled and 0.4 max_width (240px)
    long_field = TextField(
        name="Long",
        is_static=True,
        static_text="This is an extremely long recognition statement for testing wrapping",
        x=0.5,
        y=0.5,
        font_size=24,
        wrap_text=True,
        max_width=0.4,
        letter_spacing=2,
    )

    rendered = renderer.render_certificate(
        template_image=template,
        fields=[long_field],
        scale=1.0,
    )
    assert rendered.size == (600, 400)


def test_scaling_consistency():
    renderer = Renderer()
    template = Image.new("RGB", (2000, 1000), "#000000")
    field = TextField(name="N", is_static=True, static_text="Test", x=0.5, y=0.5, font_size=50)

    # Render at full scale (1.0)
    img_full = renderer.render_certificate(template, [field], scale=1.0)
    assert img_full.size == (2000, 1000)

    # Render at thumbnail scale (0.5)
    img_thumb = renderer.render_certificate(template, [field], scale=0.5)
    assert img_thumb.size == (1000, 500)
