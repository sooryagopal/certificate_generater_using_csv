"""
Unit tests for StrikeLine model, LayoutManager strike line operations,
Renderer strike line drawing, and LayoutPreset integration in AURELIA.
"""

import pytest
from PIL import Image
from models.strike_line import StrikeLine
from models.text_field import TextField
from models.layout_preset import LayoutPreset
from core.layout_manager import LayoutManager
from core.renderer import Renderer


def test_strike_line_model_properties_and_endpoints():
    line = StrikeLine(
        name="Technical Strike",
        x=0.50,
        y=0.55,
        length=0.20,
        thickness=4,
        color="#D4AF37",
    )

    assert line.name == "Technical Strike"
    assert line.x == 0.50
    assert line.y == 0.55
    assert line.length == 0.20
    assert line.thickness == 4
    assert line.color == "#D4AF37"
    assert line.is_visible is True

    # Check calculated endpoints
    assert pytest.approx(line.x1, rel=1e-3) == 0.40
    assert pytest.approx(line.x2, rel=1e-3) == 0.60

    # Test set_endpoints
    line.set_endpoints(0.30, 0.70)
    assert pytest.approx(line.x, rel=1e-3) == 0.50
    assert pytest.approx(line.length, rel=1e-3) == 0.40
    assert pytest.approx(line.x1, rel=1e-3) == 0.30
    assert pytest.approx(line.x2, rel=1e-3) == 0.70

    # Test copy
    line_copy = line.copy()
    assert line_copy.id != line.id
    assert "Copy" in line_copy.name
    assert pytest.approx(line_copy.x, rel=1e-3) == line.x
    assert line_copy.color == line.color


def test_strike_line_serialization_and_preset():
    line1 = StrikeLine(name="Line A", x=0.35, y=0.52, length=0.10, thickness=2, color="#000000")
    line2 = StrikeLine(name="Line B", x=0.65, y=0.52, length=0.12, thickness=3, color="#D4AF37")
    field1 = TextField(name="Name", column_name="Name", x=0.5, y=0.4)

    preset = LayoutPreset(
        name="Symposium Preset",
        version="2.0",
        template_width=1920,
        template_height=1080,
        fields=[field1],
        lines=[line1, line2],
    )

    json_str = preset.to_json()
    restored = LayoutPreset.from_json(json_str)

    assert restored.name == "Symposium Preset"
    assert len(restored.fields) == 1
    assert len(restored.lines) == 2
    assert restored.lines[0].name == "Line A"
    assert restored.lines[0].color == "#000000"
    assert restored.lines[1].name == "Line B"
    assert restored.lines[1].color == "#D4AF37"


def test_preset_backward_compatibility_without_lines():
    # Legacy preset dictionary missing "lines" key
    legacy_data = {
        "name": "Legacy Preset",
        "version": "1.0",
        "template_width": 1920,
        "template_height": 1080,
        "fields": [{"name": "Recipient", "column_name": "Name", "x": 0.5, "y": 0.5}],
    }
    preset = LayoutPreset.from_dict(legacy_data)
    assert preset.name == "Legacy Preset"
    assert len(preset.fields) == 1
    assert hasattr(preset, "lines")
    assert preset.lines == []


def test_layout_manager_strike_line_crud_and_undo():
    lm = LayoutManager()

    # 1. Add strike line
    line = lm.add_strike_line(name="Test Strike", x=0.45, y=0.55, length=0.15, thickness=4, color="#000000")
    assert len(lm.lines) == 1
    assert lm.selected_line_id == line.id
    assert lm.selected_type == "line"
    assert lm.selected_field_id is None

    # 2. Update property
    lm.update_line_property(line.id, thickness=6, color="#FF0000")
    updated = lm.get_line(line.id)
    assert updated is not None
    assert updated.thickness == 6
    assert updated.color == "#FF0000"

    # 3. Duplicate line
    dup = lm.duplicate_line(line.id)
    assert dup is not None
    assert len(lm.lines) == 2
    assert lm.selected_line_id == dup.id

    # 4. Delete line
    lm.delete_line(dup.id)
    assert len(lm.lines) == 1

    # 5. Undo / Redo
    assert lm.can_undo()
    lm.undo()  # Reverts delete
    assert len(lm.lines) == 2
    lm.redo()  # Re-applies delete
    assert len(lm.lines) == 1


def test_renderer_draws_strike_line():
    renderer = Renderer()
    # Create white canvas 400x200
    base_img = Image.new("RGB", (400, 200), color=(255, 255, 255))

    line = StrikeLine(
        name="Black Strike",
        x=0.50,
        y=0.50,
        length=0.50,  # 200px long, spanning from x=100 to x=300 at y=100
        thickness=6,
        color="#000000",
    )

    rendered = renderer.render_certificate(
        template_image=base_img,
        fields=[],
        scale=1.0,
        lines=[line],
    )

    # Pixel at center (x=200, y=100) must be black
    center_pixel = rendered.getpixel((200, 100))
    assert center_pixel == (0, 0, 0)

    # Pixel outside line span (x=50, y=100) must remain white
    outside_pixel = rendered.getpixel((50, 100))
    assert outside_pixel == (255, 255, 255)


def test_generation_service_with_strike_lines(tmp_path):
    import time
    from services.generation_service import GenerationService, GenerationOptions

    out_dir = tmp_path / "batch_out"
    out_dir.mkdir()

    template = Image.new("RGB", (600, 400), "#FFFFFF")
    fields = [TextField(name="Name", column_name="Name", x=0.5, y=0.4, font_size=24)]
    lines = [
        StrikeLine(name="Strike Non-Tech", x=0.60, y=0.60, length=0.20, thickness=4, color="#000000")
    ]
    records = [{"Name": "Alice", "RollNumber": "101"}, {"Name": "Bob", "RollNumber": "102"}]

    options = GenerationOptions(
        output_dir=str(out_dir),
        export_mode="pdf_png",
        filename_pattern="{Name}_{RollNumber}",
        create_subfolder=True,
        batch_name="StrikeBatch",
        include_combined_pdf=True,
        target_dpi=150,
    )

    service = GenerationService()
    completed_results = []
    combined_pdf_path = None

    def on_progress(p):
        pass

    def on_complete(results, combined_pdf, report_path):
        nonlocal combined_pdf_path
        completed_results.extend(results)
        combined_pdf_path = combined_pdf

    service.start_batch_generation(
        template_image=template,
        fields=fields,
        records=records,
        options=options,
        progress_callback=on_progress,
        completion_callback=on_complete,
        lines=lines,
    )

    timeout = 10
    start = time.time()
    while service.is_running() and (time.time() - start) < timeout:
        time.sleep(0.05)

    assert not service.is_running()
    assert len(completed_results) == 2
    assert combined_pdf_path is not None
    assert (out_dir / "StrikeBatch" / "certificates" / "Alice_101.pdf").exists()
    assert (out_dir / "StrikeBatch" / "certificates" / "Alice_101.png").exists()
    assert (out_dir / "StrikeBatch" / "combined_certificates.pdf").exists()

