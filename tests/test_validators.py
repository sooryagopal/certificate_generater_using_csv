"""
Unit tests for PreFlightValidator in AURELIA.
Tests diagnostic rules: missing CSV/template, missing column mappings, and blank row tracking.
"""

from PIL import Image
from models.text_field import TextField
from core.csv_reader import CSVData
from core.template_loader import TemplateData
from core.validators import PreFlightValidator


def test_missing_prerequisites():
    # 1. Everything None
    rep = PreFlightValidator.validate_all(
        csv_data=None,
        template_data=None,
        fields=[],
        output_dir=None,
        filename_pattern="{Name}",
    )
    assert not rep.is_valid
    assert len(rep.errors) >= 3


def test_column_mapping_validation(tmp_path):
    csv = CSVData(
        filepath="test.csv",
        columns=["Name", "RollNumber"],
        records=[{"Name": "Soorya", "RollNumber": "101"}],
        encoding="utf-8",
        delimiter=",",
        warnings=[],
    )
    img = Image.new("RGB", (2000, 1500), "#000000")
    tpl = TemplateData(filepath="tpl.png", image=img)

    # Field maps to non-existent column "Department"
    bad_field = TextField(name="Dept Field", column_name="Department")
    rep = PreFlightValidator.validate_all(
        csv_data=csv,
        template_data=tpl,
        fields=[bad_field],
        output_dir=str(tmp_path),
        filename_pattern="{Name}",
    )
    assert not rep.is_valid
    assert any("Department" in err for err in rep.errors)


def test_blank_mapped_row_warning(tmp_path):
    csv = CSVData(
        filepath="test.csv",
        columns=["Name", "RollNumber"],
        records=[
            {"Name": "Alice", "RollNumber": "101"},
            {"Name": "", "RollNumber": "102"},       # Row 2 has blank Name
            {"Name": "Charlie", "RollNumber": ""},   # Row 3 has blank RollNumber
        ],
        encoding="utf-8",
        delimiter=",",
        warnings=[],
    )
    img = Image.new("RGB", (2000, 1500), "#000000")
    tpl = TemplateData(filepath="tpl.png", image=img)

    fields = [
        TextField(name="Name", column_name="Name"),
        TextField(name="Roll", column_name="RollNumber"),
    ]

    rep = PreFlightValidator.validate_all(
        csv_data=csv,
        template_data=tpl,
        fields=fields,
        output_dir=str(tmp_path),
        filename_pattern="{Name}_{row}",
    )

    assert rep.is_valid  # Warnings are non-blocking
    assert 2 in rep.problematic_rows
    assert 3 in rep.problematic_rows
    assert any("empty values" in w.lower() for w in rep.warnings)
