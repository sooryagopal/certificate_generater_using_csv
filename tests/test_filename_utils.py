"""
Unit tests for Filename Utilities in AURELIA.
Tests template variable expansion, OS sanitization, path traversal defense, and collision handling.
"""

import os
import pytest
from core.filename_utils import FilenameUtils, CollisionPolicy


def test_filename_pattern_formatting():
    record = {"Name": "Soorya G", "RollNumber": "23ADR154", "EventName": "NEWELLS 3.0"}
    
    # Standard multi-column
    res1 = FilenameUtils.format_filename("{Name}_{RollNumber}", record, row_number=1)
    assert res1 == "Soorya_G_23ADR154"

    # Row number placeholder
    res2 = FilenameUtils.format_filename("Cert_{row}_{RollNumber}", record, row_number=5)
    assert res2 == "Cert_5_23ADR154"

    # Zero-padded row format
    res3 = FilenameUtils.format_filename("Cert_{row:03d}_{Name}", record, row_number=4)
    assert res3 == "Cert_004_Soorya_G"


def test_filename_sanitization():
    # Windows & Mac forbidden characters: < > : " / \ | ? *
    dangerous = 'John: "The Great" <Winner>?/\\|*Done'
    sanitized = FilenameUtils.sanitize_filename(dangerous)
    for bad_char in ':"><?/\\|*':
        assert bad_char not in sanitized

    # Leading/trailing dots and spaces
    assert FilenameUtils.sanitize_filename("...  test file ... ") == "test_file"

    # Windows reserved filenames (CON, PRN, etc.)
    assert FilenameUtils.sanitize_filename("CON") == "file_CON"
    assert FilenameUtils.sanitize_filename("NUL") == "file_NUL"


def test_path_traversal_prevention(tmp_path):
    output_dir = tmp_path / "certs"
    output_dir.mkdir()

    # Attempt directory traversal via "../../../etc/passwd"
    traversal_base = "../../../etc/passwd"
    target_path, should_skip = FilenameUtils.resolve_destination(
        output_dir=str(output_dir),
        base_name=traversal_base,
        extension=".pdf",
        policy=CollisionPolicy.OVERWRITE,
    )

    # Must reside strictly within output_dir
    assert not should_skip
    assert os.path.dirname(os.path.abspath(target_path)) == os.path.abspath(str(output_dir))


def test_collision_policies(tmp_path):
    output_dir = tmp_path / "collision_test"
    output_dir.mkdir()

    # Create dummy existing file
    existing = output_dir / "Certificate_1.pdf"
    existing.write_text("dummy")

    # 1. Policy: APPEND_ROW
    path_row, skip_row = FilenameUtils.resolve_destination(
        output_dir=str(output_dir),
        base_name="Certificate_1",
        extension=".pdf",
        policy=CollisionPolicy.APPEND_ROW,
        row_number=12,
    )
    assert not skip_row
    assert os.path.basename(path_row) == "Certificate_1_row12.pdf"

    # 2. Policy: APPEND_UNIQUE
    path_uniq, skip_uniq = FilenameUtils.resolve_destination(
        output_dir=str(output_dir),
        base_name="Certificate_1",
        extension=".pdf",
        policy=CollisionPolicy.APPEND_UNIQUE,
    )
    assert not skip_uniq
    assert os.path.basename(path_uniq) == "Certificate_1_1.pdf"

    # 3. Policy: SKIP
    path_skip, should_skip = FilenameUtils.resolve_destination(
        output_dir=str(output_dir),
        base_name="Certificate_1",
        extension=".pdf",
        policy=CollisionPolicy.SKIP,
    )
    assert should_skip
    assert path_skip is None

    # 4. Policy: OVERWRITE
    path_ow, skip_ow = FilenameUtils.resolve_destination(
        output_dir=str(output_dir),
        base_name="Certificate_1",
        extension=".pdf",
        policy=CollisionPolicy.OVERWRITE,
    )
    assert not skip_ow
    assert os.path.basename(path_ow) == "Certificate_1.pdf"
