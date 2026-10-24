"""
Automated Test Suite for Dynamic CSV Column Detection and Certificate Placeholders.
Covers all 15 scenarios specified in Section 16 of the prompt:
1. Detecting all CSV headers.
2. Handling 5, 20, 50, and 100 columns.
3. Generating placeholders dynamically.
4. Preserving Unicode header names.
5. Resolving multiple placeholders.
6. Resolving repeated placeholders.
7. Preserving leading zeros.
8. Handling empty cells.
9. Detecting unknown placeholders.
10. Supporting duplicate use of a column in multiple fields.
11. Reloading a CSV with the same headers.
12. Reloading a CSV with changed headers.
13. Saving and loading placeholder-based presets.
14. Exporting different participant values correctly.
15. Ensuring no unresolved placeholders remain in generated output.
"""

import os
import io
import json
import pytest
from PIL import Image

from core.csv_reader import CSVReader, CSVData
from core.placeholder_engine import PlaceholderEngine
from core.layout_manager import LayoutManager
from core.validators import PreFlightValidator
from core.renderer import Renderer
from models.text_field import TextField
from models.layout_preset import LayoutPreset
from services.preset_service import PresetService


# -----------------------------------------------------------------------------
# Scenario 1: Detecting all CSV headers
# -----------------------------------------------------------------------------
def test_detecting_all_csv_headers(tmp_path):
    csv_file = tmp_path / "headers_test.csv"
    csv_file.write_text("Name,RollNumber,Department,Class,EventName,EventDate,College,Email,Phone,CertificateID,Prize,Duration\n"
                        "Soorya G,23ADR154,AIDS,IV Year,NEWELLS 3.0,24-10-2026,KEC,soorya@example.com,9876543210,CERT001,First Prize,24 Hours\n",
                        encoding="utf-8")
    data = CSVReader.load_csv(str(csv_file))
    expected = [
        "Name", "RollNumber", "Department", "Class", "EventName", "EventDate",
        "College", "Email", "Phone", "CertificateID", "Prize", "Duration"
    ]
    assert data.columns == expected
    assert len(data.columns) == 12
    assert data.row_count == 1


# -----------------------------------------------------------------------------
# Scenario 2: Handling 5, 20, 50, and 100 columns
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("col_count", [5, 20, 50, 100])
def test_handling_various_column_counts(tmp_path, col_count):
    headers = [f"Col_{i}" for i in range(1, col_count + 1)]
    row = [f"Val_{i}" for i in range(1, col_count + 1)]
    csv_file = tmp_path / f"test_{col_count}_cols.csv"
    csv_file.write_text(",".join(headers) + "\n" + ",".join(row) + "\n", encoding="utf-8")

    data = CSVReader.load_csv(str(csv_file))
    assert len(data.columns) == col_count
    assert data.columns == headers

    # Verify placeholder engine generates dict for every single column without truncation
    ph_dict = PlaceholderEngine.create_dynamic_placeholders_dict(data.columns, data.records[0])
    assert len(ph_dict) == col_count
    assert ph_dict[0]["placeholder"] == "{{Col_1}}"
    assert ph_dict[-1]["placeholder"] == f"{{{{Col_{col_count}}}}}"


# -----------------------------------------------------------------------------
# Scenario 3: Generating placeholders dynamically
# -----------------------------------------------------------------------------
def test_generating_placeholders_dynamically():
    assert PlaceholderEngine.generate_placeholder("Student Name") == "{{Student Name}}"
    assert PlaceholderEngine.generate_placeholder("  EventDate  ") == "{{EventDate}}"
    assert PlaceholderEngine.generate_placeholder("Certificate-ID") == "{{Certificate-ID}}"

    cols = ["First", "Second", "Third"]
    rec = {"First": "A", "Second": "B", "Third": "C"}
    items = PlaceholderEngine.create_dynamic_placeholders_dict(cols, rec)
    assert len(items) == 3
    assert items[0] == {"column": "First", "placeholder": "{{First}}", "sample_value": "A"}


# -----------------------------------------------------------------------------
# Scenario 4: Preserving Unicode header names
# -----------------------------------------------------------------------------
def test_preserving_unicode_header_names(tmp_path):
    headers = ["பெயர்", "வகுப்பு", "Prénom", "Schüler Name", "Event"]
    values = ["சூர்யா ஜி", "IV Year", "René", "Müller", "Symposium 2026"]
    csv_file = tmp_path / "unicode_headers.csv"
    csv_file.write_text(",".join(headers) + "\n" + ",".join(values) + "\n", encoding="utf-8")

    data = CSVReader.load_csv(str(csv_file))
    assert data.columns == headers

    # Test dynamic placeholders
    ph_tamil = PlaceholderEngine.generate_placeholder("பெயர்")
    assert ph_tamil == "{{பெயர்}}"

    resolved = PlaceholderEngine.resolve_string("சான்றிதழ்: {{பெயர்}}", data.records[0])
    assert resolved == "சான்றிதழ்: சூர்யா ஜி"

    resolved_french = PlaceholderEngine.resolve_string("Participant: {{Prénom}}", data.records[0])
    assert resolved_french == "Participant: René"


# -----------------------------------------------------------------------------
# Scenario 5: Resolving multiple placeholders
# -----------------------------------------------------------------------------
def test_resolving_multiple_placeholders():
    template = "Awarded to {{Name}} (Roll No: {{RollNumber}}) of {{Department}} for winning {{Prize}} in {{EventName}}."
    record = {
        "Name": "Soorya G",
        "RollNumber": "23ADR154",
        "Department": "AIDS",
        "Prize": "First Prize",
        "EventName": "NEWELLS 3.0",
    }
    resolved = PlaceholderEngine.resolve_string(template, record)
    expected = "Awarded to Soorya G (Roll No: 23ADR154) of AIDS for winning First Prize in NEWELLS 3.0."
    assert resolved == expected


# -----------------------------------------------------------------------------
# Scenario 6: Resolving repeated placeholders
# -----------------------------------------------------------------------------
def test_resolving_repeated_placeholders():
    template = "Certificate for {{Name}}. Congratulations {{Name}}, on your award!"
    record = {"Name": "Prathisha S"}
    resolved = PlaceholderEngine.resolve_string(template, record)
    assert resolved == "Certificate for Prathisha S. Congratulations Prathisha S, on your award!"


# -----------------------------------------------------------------------------
# Scenario 7: Preserving leading zeros
# -----------------------------------------------------------------------------
def test_preserving_leading_zeros(tmp_path):
    csv_file = tmp_path / "leading_zeros.csv"
    csv_file.write_text("ID,Phone,Code\n001048,0987654321,00042\n", encoding="utf-8")
    data = CSVReader.load_csv(str(csv_file))

    record = data.records[0]
    assert record["ID"] == "001048"
    assert record["Phone"] == "0987654321"
    assert record["Code"] == "00042"

    template = "ID: {{ID}} | Phone: {{Phone}} | Code: {{Code}}"
    resolved = PlaceholderEngine.resolve_string(template, record)
    assert resolved == "ID: 001048 | Phone: 0987654321 | Code: 00042"


# -----------------------------------------------------------------------------
# Scenario 8: Handling empty cells
# -----------------------------------------------------------------------------
def test_handling_empty_cells():
    record = {"Name": "Soorya G", "MiddleName": "", "Prize": None}
    template = "Name: {{Name}} | Middle: '{{MiddleName}}' | Prize: '{{Prize}}'"
    resolved = PlaceholderEngine.resolve_string(template, record)
    assert resolved == "Name: Soorya G | Middle: '' | Prize: ''"


# -----------------------------------------------------------------------------
# Scenario 9: Detecting unknown placeholders
# -----------------------------------------------------------------------------
def test_detecting_unknown_placeholders():
    known_cols = {"Name", "RollNumber", "Department"}
    template = "Awarded to {{Name}} for {{NonExistentEvent}} at {{UnknownCollege}}"
    unresolved = PlaceholderEngine.find_unresolved(template, known_cols)
    assert "NonExistentEvent" in unresolved
    assert "UnknownCollege" in unresolved
    assert "Name" not in unresolved

    # Test PreFlightValidator integration
    field = TextField(name="Summary", template_text=template, is_static=False)
    csv_data = CSVData(
        filepath="dummy.csv",
        columns=["Name", "RollNumber", "Department"],
        records=[{"Name": "A", "RollNumber": "1", "Department": "D"}],
        encoding="utf-8",
        delimiter=",",
        warnings=[],
    )
    report = PreFlightValidator.validate_all(
        csv_data=csv_data,
        template_data=None,
        fields=[field],
        output_dir="/tmp",
        filename_pattern="{Name}",
    )
    assert not report.is_valid
    assert any("references unknown placeholder" in err for err in report.errors)


# -----------------------------------------------------------------------------
# Scenario 10: Supporting duplicate use of a column in multiple fields
# -----------------------------------------------------------------------------
def test_supporting_duplicate_use_of_column_in_multiple_fields():
    lm = LayoutManager()
    f1 = lm.add_placeholder_field("Name", x=0.5, y=0.45, font_size=52)
    f2 = lm.add_placeholder_field("Name", x=0.2, y=0.85, font_size=20)

    # Must be separate field instances with distinct IDs
    assert f1.id != f2.id
    assert f1.font_size == 52
    assert f2.font_size == 20
    assert f1.x == 0.5
    assert f2.x == 0.2

    # Both resolve correctly from the same record
    rec = {"Name": "Soorya G"}
    assert f1.resolve_text(rec) == "Soorya G"
    assert f2.resolve_text(rec) == "Soorya G"


# -----------------------------------------------------------------------------
# Scenario 11: Reloading a CSV with the same headers
# -----------------------------------------------------------------------------
def test_reloading_csv_with_same_headers():
    lm = LayoutManager()
    lm.add_placeholder_field("Name")
    lm.add_placeholder_field("RollNumber")
    lm.add_placeholder_field("Department")

    # Reload with identical headers (possibly different casing/order)
    new_headers = ["department", "name", "rollnumber"]
    valid, missing = lm.synchronize_with_csv(new_headers)

    assert len(missing) == 0
    assert len(valid) == 3


# -----------------------------------------------------------------------------
# Scenario 12: Reloading a CSV with changed headers
# -----------------------------------------------------------------------------
def test_reloading_csv_with_changed_headers():
    lm = LayoutManager()
    lm.add_placeholder_field("Name")
    lm.add_placeholder_field("OldDepartment")

    # New CSV dropped OldDepartment and added Branch
    new_headers = ["Name", "Branch"]
    valid, missing = lm.synchronize_with_csv(new_headers)

    assert len(valid) == 1
    assert len(missing) == 1
    assert any("OldDepartment" in m for m in missing)
    # Field mapping was not silently corrupted or mapped to column 0
    old_dept_field = lm.fields[1]
    assert old_dept_field.column_name == "OldDepartment"


# -----------------------------------------------------------------------------
# Scenario 13: Saving and loading placeholder-based presets
# -----------------------------------------------------------------------------
def test_saving_and_loading_placeholder_based_presets(tmp_path):
    lm = LayoutManager()
    lm.add_placeholder_field("Name", x=0.5, y=0.4)
    lm.add_placeholder_field("RollNumber", x=0.5, y=0.6)
    f3 = lm.add_field(name="CustomText", is_static=False)
    f3.template_text = "Awarded to {{Name}} for {{EventName}}"

    preset = lm.export_to_preset(name="TestPresetV2")
    preset_dict = preset.to_dict()

    assert preset_dict["version"] == "2.0"
    assert len(preset_dict["fields"]) == 3
    assert preset_dict["fields"][0]["placeholder"] == "{{Name}}"
    assert preset_dict["fields"][2]["template_text"] == "Awarded to {{Name}} for {{EventName}}"

    # Save to disk and reload
    preset_file = tmp_path / "preset_v2.json"
    with open(preset_file, "w", encoding="utf-8") as fp:
        json.dump(preset_dict, fp)

    loaded = LayoutPreset.from_file(str(preset_file))
    lm2 = LayoutManager()
    lm2.load_preset(loaded)

    assert len(lm2.fields) == 3
    assert lm2.fields[0].column_name == "Name"
    assert lm2.fields[0].placeholder == "{{Name}}"
    assert lm2.fields[2].template_text == "Awarded to {{Name}} for {{EventName}}"


# -----------------------------------------------------------------------------
# Scenario 14: Exporting different participant values correctly
# -----------------------------------------------------------------------------
def test_exporting_different_participant_values_correctly():
    template = Image.new("RGB", (800, 600), color=(255, 255, 255))
    lm = LayoutManager()
    lm.add_placeholder_field("Name", x=0.5, y=0.5)

    rec1 = {"Name": "Participant Alpha"}
    rec2 = {"Name": "Participant Beta"}

    renderer = Renderer()
    img1 = renderer.render_certificate(template, lm.fields, record=rec1)
    img2 = renderer.render_certificate(template, lm.fields, record=rec2)

    # Rendered images must be distinct
    assert img1.tobytes() != img2.tobytes()
    assert lm.fields[0].resolve_text(rec1) == "Participant Alpha"
    assert lm.fields[0].resolve_text(rec2) == "Participant Beta"


# -----------------------------------------------------------------------------
# Scenario 15: Ensuring no unresolved placeholders remain in generated output
# -----------------------------------------------------------------------------
def test_ensuring_no_unresolved_placeholders_remain_in_generated_output():
    field = TextField(
        name="CombinedText",
        template_text="Awarded to {{Name}} for {{UnknownEvent}} at {{UnknownCollege}}.",
        is_static=False,
    )
    record = {"Name": "Soorya G"}  # UnknownEvent and UnknownCollege missing

    resolved = field.resolve_text(record)
    assert "{{Name}}" not in resolved
    assert "{{UnknownEvent}}" not in resolved
    assert "{{UnknownCollege}}" not in resolved
    assert resolved == "Awarded to Soorya G for  at ."
