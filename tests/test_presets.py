"""
Unit tests for LayoutPreset and PresetService in AURELIA.
Tests serialization, deserialization, JSON schema validation, and file operations.
"""

import pytest
from models.layout_preset import LayoutPreset
from models.text_field import TextField
from services.preset_service import PresetService, PresetError


def test_preset_serialization_and_deserialization():
    field1 = TextField(name="Student Name", column_name="Name", x=0.5, y=0.4, font_size=48)
    field2 = TextField(name="Title", is_static=True, static_text="Excellence", x=0.5, y=0.2)

    preset = LayoutPreset(
        name="Award Preset",
        version="1.0",
        template_width=1920,
        template_height=1080,
        fields=[field1, field2],
    )

    json_str = preset.to_json()
    loaded = LayoutPreset.from_json(json_str)

    assert loaded.name == "Award Preset"
    assert loaded.template_width == 1920
    assert len(loaded.fields) == 2
    assert loaded.fields[0].name == "Student Name"
    assert loaded.fields[0].column_name == "Name"
    assert loaded.fields[1].static_text == "Excellence"


def test_invalid_preset_json():
    # Empty string
    with pytest.raises(Exception):
        LayoutPreset.from_json("")

    # Not a dictionary
    with pytest.raises(ValueError):
        LayoutPreset.from_json("[1, 2, 3]")

    # Missing name
    with pytest.raises(ValueError, match="name"):
        LayoutPreset.from_dict({"version": "1.0", "fields": []})


def test_preset_service_crud_and_clone(tmp_path):
    storage_dir = tmp_path / "presets"
    service = PresetService(storage_dir=str(storage_dir))

    # 1. Save
    f = TextField(name="Winner", column_name="Name", x=0.5, y=0.5)
    p = LayoutPreset(name="Champion Layout", fields=[f])
    saved_path = service.save_preset(p)
    assert storage_dir.exists()

    # 2. List
    presets = service.list_presets()
    assert "Champion Layout" in presets

    # 3. Load
    loaded = service.load_preset_by_name("Champion Layout")
    assert loaded.name == "Champion Layout"
    assert len(loaded.fields) == 1

    # 4. Duplicate
    dup = service.duplicate_preset("Champion Layout", "Champion Layout Copy")
    assert dup.name == "Champion Layout Copy"
    assert len(service.list_presets()) == 2

    # 5. Delete
    deleted = service.delete_preset("Champion Layout Copy")
    assert deleted
    assert "Champion Layout Copy" not in service.list_presets()
