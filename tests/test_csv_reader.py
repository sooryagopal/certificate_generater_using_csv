"""
Unit tests for CSV Reader module in AURELIA.
Tests encodings (UTF-8, UTF-8 BOM, fallback), leading zeroes, delimiters, and header validations.
"""

import os
import pytest
from core.csv_reader import CSVReader, CSVReaderError


def test_utf8_and_utf8_bom_parsing(tmp_path):
    # 1. Plain UTF-8
    csv_utf8 = tmp_path / "utf8.csv"
    csv_utf8.write_text("Name,RollNumber\nAlice,23ADR001\nBob,23ADR002\n", encoding="utf-8")
    data_utf8 = CSVReader.load_csv(str(csv_utf8))
    assert data_utf8.row_count == 2
    assert data_utf8.columns == ["Name", "RollNumber"]
    assert data_utf8.records[0]["Name"] == "Alice"

    # 2. UTF-8 with BOM
    csv_bom = tmp_path / "bom.csv"
    csv_bom.write_text("Name,RollNumber\nCharlie,23ADR003\n", encoding="utf-8-sig")
    data_bom = CSVReader.load_csv(str(csv_bom))
    assert data_bom.row_count == 1
    assert data_bom.columns == ["Name", "RollNumber"]
    assert data_bom.records[0]["Name"] == "Charlie"


def test_preserves_leading_zeros(tmp_path):
    csv_file = tmp_path / "leading_zeros.csv"
    csv_file.write_text("ID,StudentCode,Score\n00142,000789,95\n00001,009900,100\n", encoding="utf-8")
    data = CSVReader.load_csv(str(csv_file))
    assert data.records[0]["ID"] == "00142"
    assert data.records[0]["StudentCode"] == "000789"
    assert data.records[1]["ID"] == "00001"
    assert data.records[1]["StudentCode"] == "009900"


def test_empty_file_and_whitespace_error(tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(CSVReaderError, match="empty"):
        CSVReader.load_csv(str(empty_file))

    ws_file = tmp_path / "whitespace.csv"
    ws_file.write_text("   \n\n  \t  ", encoding="utf-8")
    with pytest.raises(CSVReaderError):
        CSVReader.load_csv(str(ws_file))


def test_duplicate_and_empty_headers(tmp_path):
    csv_file = tmp_path / "headers.csv"
    csv_file.write_text("Name,,Name,Class\nJohn,001,Doe,X\n", encoding="utf-8")
    data = CSVReader.load_csv(str(csv_file))
    assert "Name" in data.columns
    assert "Column_2" in data.columns  # Empty header renamed
    assert "Name_2" in data.columns    # Duplicate header deduplicated
    assert len(data.warnings) >= 2


def test_international_and_tamil_text(tmp_path):
    csv_file = tmp_path / "tamil.csv"
    csv_file.write_text("Name,City,Course\nசூர்யா ஜி,சென்னை,AI\nRené Dupont,Zürich,CS\n", encoding="utf-8")
    data = CSVReader.load_csv(str(csv_file))
    assert data.records[0]["Name"] == "சூர்யா ஜி"
    assert data.records[0]["City"] == "சென்னை"
    assert data.records[1]["Name"] == "René Dupont"


def test_delimiter_sniffing(tmp_path):
    # Semicolon delimited
    csv_semi = tmp_path / "semi.csv"
    csv_semi.write_text("Name;RollNumber;Dept\nSoorya;101;AIDS\nPrathisha;102;AIDS\n", encoding="utf-8")
    data_semi = CSVReader.load_csv(str(csv_semi))
    assert data_semi.delimiter == ";"
    assert data_semi.columns == ["Name", "RollNumber", "Dept"]
    assert data_semi.row_count == 2
