"""
Validators module for AURELIA — Bulk Certificate Generator.
Performs comprehensive pre-flight verification before bulk generation begins.
Separates critical blocking errors from non-blocking advisories/warnings.
"""

from __future__ import annotations
import os
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from models.text_field import TextField
from core.csv_reader import CSVData
from core.template_loader import TemplateData
from core.filename_utils import FilenameUtils
from core.placeholder_engine import PlaceholderEngine


@dataclass
class ValidationReport:
    """Consolidated results of the pre-flight generation audit."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    problematic_rows: Dict[int, List[str]] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_row_issue(self, row_idx: int, issue: str) -> None:
        if row_idx not in self.problematic_rows:
            self.problematic_rows[row_idx] = []
        self.problematic_rows[row_idx].append(issue)


class PreFlightValidator:
    """Validates CSV data, templates, field mappings, fonts, and output paths."""

    @classmethod
    def validate_all(
        cls,
        csv_data: Optional[CSVData],
        template_data: Optional[TemplateData],
        fields: List[TextField],
        output_dir: Optional[str],
        filename_pattern: str,
    ) -> ValidationReport:
        """Executes full diagnostic check on all inputs and configurations."""
        report = ValidationReport()

        # 1. CSV Data check
        if not csv_data:
            report.add_error("No CSV recipient file has been loaded.")
        elif csv_data.row_count == 0:
            report.add_error("The loaded CSV file contains no participant rows.")

        # 2. Template check
        if not template_data:
            report.add_error("No certificate graphic template has been loaded.")
        else:
            if template_data.is_low_resolution:
                report.add_warning(
                    f"Template resolution is low ({template_data.width}x{template_data.height}). "
                    "Exported certificates may appear soft or pixelated in print."
                )

        # 3. Output directory check
        if not output_dir or not str(output_dir).strip():
            report.add_error("No output destination directory has been selected.")
        else:
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    report.add_error(f"Cannot create output directory: {str(e)}")
            elif not os.access(output_dir, os.W_OK):
                report.add_error(f"The selected output directory is not writable: {output_dir}")

        # 4. Fields check
        visible_fields = [f for f in fields if f.is_visible]
        if not fields:
            report.add_error("No text fields have been defined for the certificate.")
        elif not visible_fields:
            report.add_warning("All text fields are currently hidden; certificates will have no text overlays.")

        # 5. Column Mappings & CSV consistency
        if csv_data and csv_data.columns:
            available_cols = set(csv_data.columns)
            mapped_cols: Set[str] = set()

            for f in visible_fields:
                text_to_check = ""
                if f.template_text and "{{" in f.template_text:
                    text_to_check = f.template_text
                elif f.is_static and "{{" in f.static_text:
                    text_to_check = f.static_text

                if text_to_check:
                    unresolved = PlaceholderEngine.find_unresolved(text_to_check, available_cols)
                    if unresolved:
                        report.add_error(
                            f"Field '{f.name}' references unknown placeholder(s): {', '.join(unresolved)}."
                        )
                    for ph in PlaceholderEngine.extract_placeholders(text_to_check):
                        for col in available_cols:
                            if col.strip().lower() == ph.strip().lower():
                                mapped_cols.add(col)
                                break
                elif not f.is_static:
                    if not f.column_name:
                        report.add_warning(f"Field '{f.name}' is dynamic but has no CSV column mapped to it.")
                    elif f.column_name not in available_cols:
                        report.add_error(
                            f"Field '{f.name}' maps to column '{f.column_name}', which does not exist in the loaded CSV."
                        )
                    else:
                        mapped_cols.add(f.column_name)

            # Check for blank values across rows in mapped columns
            blank_records_count = 0
            for idx, record in enumerate(csv_data.records):
                row_num = idx + 1
                row_blanks = []
                for col in mapped_cols:
                    val = record.get(col, "")
                    if val is None or not str(val).strip():
                        row_blanks.append(col)

                if row_blanks:
                    blank_records_count += 1
                    report.add_row_issue(
                        row_num, f"Empty value in mapped column(s): {', '.join(row_blanks)}"
                    )

            if blank_records_count > 0:
                report.add_warning(
                    f"{blank_records_count} record(s) contain empty values for mapped certificate fields."
                )

        # 6. Filename pattern check
        if filename_pattern:
            avail = set(csv_data.columns) if csv_data else set()
            is_valid_pat, pat_warnings = FilenameUtils.validate_pattern(filename_pattern, avail)
            if not is_valid_pat:
                report.add_error(f"Invalid filename pattern: {'; '.join(pat_warnings)}")
            else:
                for pw in pat_warnings:
                    report.add_warning(pw)
        else:
            report.add_warning("Filename pattern is blank; will use default naming scheme.")

        # 7. Field positions check
        for f in visible_fields:
            if f.x < 0.0 or f.x > 1.0 or f.y < 0.0 or f.y > 1.0:
                report.add_warning(f"Field '{f.name}' is positioned outside the certificate boundary ({f.x:.2f}, {f.y:.2f}).")
            if f.font_path and not os.path.exists(f.font_path):
                report.add_warning(f"Custom font file for field '{f.name}' not found: {f.font_path}")

        return report
