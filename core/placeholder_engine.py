"""
Placeholder Engine module for AURELIA — Bulk Certificate Generator.
Handles dynamic {{ColumnName}} syntax generation, extraction, validation,
and safe regex-based replacement against recipient record dictionaries.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Set, Tuple, Optional


class PlaceholderEngine:
    """Core parser and substitution engine for certificate placeholders."""

    # Matches {{ColumnName}} syntax safely
    PLACEHOLDER_REGEX = re.compile(r'\{\{([^{}]+)\}\}')

    @classmethod
    def generate_placeholder(cls, column_name: str) -> str:
        """
        Generates standard canonical placeholder syntax from a column header.
        Example: 'Roll Number' -> '{{Roll Number}}'
        """
        clean_col = column_name.strip()
        return f"{{{{{clean_col}}}}}"

    @classmethod
    def extract_placeholders(cls, text: str) -> List[str]:
        """
        Extracts all column names referenced inside {{...}} in a string.
        Example: 'Awarded to {{Name}} for {{Event}}' -> ['Name', 'Event']
        """
        if not text:
            return []
        matches = cls.PLACEHOLDER_REGEX.findall(text)
        return [m.strip() for m in matches if m.strip()]

    @classmethod
    def resolve_string(
        cls,
        template_text: str,
        record: Optional[Dict[str, Any]] = None,
        available_columns: Optional[Set[str]] = None,
        missing_placeholder_fallback: Optional[str] = None,
    ) -> str:
        """
        Substitutes all {{ColumnName}} occurrences with record values.
        Preserves static text, spacing, Unicode characters, and leading zeros.
        Never uses eval or exec.
        
        Args:
            template_text: Source string containing literal text and {{Column}} placeholders.
            record: Dict mapping column names to cell values.
            available_columns: Optional set of known valid columns for diagnostic checking.
            missing_placeholder_fallback: If provided, replaces missing placeholders with this string.
                                         If None, leaves unresolved placeholders intact or warns.
        """
        if not template_text:
            return ""

        if record is None:
            # When no record is present, return the template as-is
            return template_text

        # Normalized lookup dict mapping lower-cased & stripped keys to original values
        # To tolerate minor casing/whitespace mismatches safely
        normalized_record = {k.strip(): ("" if v is None else str(v)) for k, v in record.items()}
        lower_record = {k.strip().lower(): ("" if v is None else str(v)) for k, v in record.items()}

        def replace_match(match: re.Match) -> str:
            raw_var = match.group(1).strip()
            # 1. Exact match
            if raw_var in normalized_record:
                return normalized_record[raw_var]

            # 2. Case-insensitive match fallback
            var_lower = raw_var.lower()
            if var_lower in lower_record:
                return lower_record[var_lower]

            # 3. Missing/Unresolved placeholder handling
            if missing_placeholder_fallback is not None:
                return missing_placeholder_fallback

            # Keep original placeholder so user/validator knows it's unmapped
            return match.group(0)

        return cls.PLACEHOLDER_REGEX.sub(replace_match, template_text)

    @classmethod
    def find_unresolved(
        cls,
        text: str,
        available_columns: Set[str],
    ) -> List[str]:
        """
        Identifies any {{...}} placeholder names in text that are NOT present in available_columns.
        """
        if not text:
            return []

        referenced = cls.extract_placeholders(text)
        avail_normalized = {c.strip().lower() for c in available_columns}

        unresolved = []
        for ref in referenced:
            if ref.lower() not in avail_normalized:
                unresolved.append(ref)

        return unresolved

    @classmethod
    def create_dynamic_placeholders_dict(
        cls,
        columns: List[str],
        sample_record: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """
        Builds dynamic placeholder metadata list for the UI.
        Returns a list of dicts:
        [
            {
                'column': 'RollNumber',
                'placeholder': '{{RollNumber}}',
                'sample_value': '23ADR154',
            },
            ...
        ]
        """
        result = []
        sample_record = sample_record or {}

        for col in columns:
            clean_col = col.strip()
            placeholder = cls.generate_placeholder(clean_col)
            val = sample_record.get(clean_col, "")
            if val is None:
                val = ""
            result.append({
                "column": clean_col,
                "placeholder": placeholder,
                "sample_value": str(val),
            })

        return result
