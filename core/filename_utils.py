"""
Filename Utilities module for AURELIA — Bulk Certificate Generator.
Expands customizable template patterns (e.g. {Name}_{RollNumber}_{row}),
sanitizes filenames across OS platforms, prevents path traversal attacks,
and resolves filename collisions safely.
"""

from __future__ import annotations
import os
import re
from typing import Dict, Any, Set, Tuple


class CollisionPolicy:
    """Strategy for handling output filename collisions."""
    APPEND_ROW = "append_row"        # e.g., Certificate_row12.pdf
    APPEND_UNIQUE = "append_unique"  # e.g., Certificate_1.pdf, Certificate_2.pdf
    SKIP = "skip"                    # Skip existing files
    OVERWRITE = "overwrite"          # Overwrite existing files


class FilenameUtils:
    """Sanitizer, formatter, and collision resolver for certificate output files."""

    # Windows and POSIX forbidden characters
    FORBIDDEN_CHARS = re.compile(r'[\\/*?:"<>|]')
    CONTROL_CHARS = re.compile(r'[\x00-\x1f\x7f-\x9f]')

    @classmethod
    def sanitize_filename(cls, name: str, fallback: str = "certificate") -> str:
        """
        Strips dangerous and forbidden characters from a filename string.
        Guarantees safe naming on macOS, Windows, and Linux.
        """
        if not name or not str(name).strip():
            return fallback

        # Replace path separators and forbidden symbols with underscore
        clean = cls.FORBIDDEN_CHARS.sub("_", str(name))
        # Remove control characters
        clean = cls.CONTROL_CHARS.sub("", clean)

        # Replace consecutive underscores/spaces
        clean = re.sub(r'[\s_]+', '_', clean)
        # Strip leading/trailing underscores, dots, and spaces
        clean = clean.strip(" ._")

        # Windows reserved filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
        root_name, ext = os.path.splitext(clean)
        if root_name.upper() in reserved_names:
            clean = f"file_{clean}"

        # Truncate length to avoid OS max path limitations
        if len(clean) > 200:
            clean = clean[:200].rstrip(" ._")

        return clean or fallback

    @classmethod
    def format_filename(
        cls,
        pattern: str,
        record: Dict[str, Any],
        row_number: int,
        fallback_prefix: str = "Certificate",
    ) -> str:
        """
        Expands template patterns like '{Name}_{RollNumber}' using CSV record values.
        Always supports '{row}' (1-indexed) and '{index}' (0-indexed).
        """
        if not pattern or not pattern.strip():
            pattern = "{Name}_{RollNumber}" if ("Name" in record and "RollNumber" in record) else f"{fallback_prefix}_{{row}}"

        # Provide built-in row placeholders
        context = {
            "row": str(row_number),
            "index": str(row_number - 1),
            **{k: ("" if v is None else str(v)) for k, v in record.items()},
        }

        # Safe template replacement using regex to prevent KeyError crashes
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1).strip()
            # Support format specs like {row:03d}
            if ":" in var_name:
                key, fmt = var_name.split(":", 1)
                val = context.get(key, "")
                try:
                    if fmt.endswith("d"):
                        return f"{int(val):{fmt}}"
                except Exception:
                    pass
                return str(val)
            return context.get(var_name, "")

        expanded = re.sub(r'\{([^{}]+)\}', replace_var, pattern)
        sanitized = cls.sanitize_filename(expanded, fallback=f"{fallback_prefix}_{row_number}")
        return sanitized

    @classmethod
    def resolve_destination(
        cls,
        output_dir: str,
        base_name: str,
        extension: str,
        policy: str = CollisionPolicy.APPEND_ROW,
        row_number: int = 1,
        existing_names: Optional[Set[str]] = None,
    ) -> Tuple[Optional[str], bool]:
        """
        Determines the final safe absolute file path in output_dir.
        Checks for path traversal and applies collision policy.
        
        Returns:
            (target_filepath, should_skip)
            If should_skip is True, generation for this file should be skipped.
        """
        clean_ext = extension if extension.startswith(".") else f".{extension}"
        sanitized_base = cls.sanitize_filename(base_name)
        initial_filename = f"{sanitized_base}{clean_ext}"

        # Path traversal guard
        output_dir_abs = os.path.abspath(output_dir)
        target_path = os.path.abspath(os.path.join(output_dir_abs, initial_filename))

        # Check that target_path is strictly within output_dir_abs
        try:
            common = os.path.commonpath([output_dir_abs, target_path])
            if common != output_dir_abs:
                # Traversal attempted: flatten into safe filename
                initial_filename = f"{cls.sanitize_filename(os.path.basename(initial_filename))}"
                target_path = os.path.abspath(os.path.join(output_dir_abs, initial_filename))
        except Exception:
            initial_filename = f"certificate_{row_number}{clean_ext}"
            target_path = os.path.abspath(os.path.join(output_dir_abs, initial_filename))

        # Collision detection (against disk and against existing_names in current batch)
        file_exists = os.path.exists(target_path) or (existing_names is not None and initial_filename in existing_names)

        if not file_exists:
            if existing_names is not None:
                existing_names.add(initial_filename)
            return target_path, False

        # Collision handling policies
        if policy == CollisionPolicy.OVERWRITE:
            if existing_names is not None:
                existing_names.add(initial_filename)
            return target_path, False

        elif policy == CollisionPolicy.SKIP:
            return None, True

        elif policy == CollisionPolicy.APPEND_ROW:
            new_filename = f"{sanitized_base}_row{row_number}{clean_ext}"
            target_path = os.path.join(output_dir_abs, new_filename)
            if existing_names is not None:
                existing_names.add(new_filename)
            return target_path, False

        elif policy == CollisionPolicy.APPEND_UNIQUE:
            counter = 1
            while True:
                candidate_name = f"{sanitized_base}_{counter}{clean_ext}"
                candidate_path = os.path.join(output_dir_abs, candidate_name)
                cand_exists = os.path.exists(candidate_path) or (
                    existing_names is not None and candidate_name in existing_names
                )
                if not cand_exists:
                    if existing_names is not None:
                        existing_names.add(candidate_name)
                    return candidate_path, False
                counter += 1

        # Default fallback
        return target_path, False

    @classmethod
    def validate_pattern(cls, pattern: str, available_columns: Set[str]) -> Tuple[bool, List[str]]:
        """
        Validates pattern syntax and warns if variables are not in CSV columns.
        Returns (is_valid, warnings).
        """
        warnings = []
        if not pattern.strip():
            return False, ["Filename pattern cannot be empty."]

        # Check balanced braces
        if pattern.count("{") != pattern.count("}"):
            return False, ["Mismatched curly braces '{' and '}' in filename pattern."]

        tokens = re.findall(r'\{([^{}]+)\}', pattern)
        for token in tokens:
            key = token.split(":")[0].strip()
            if key not in ("row", "index") and key not in available_columns:
                warnings.append(f"Pattern variable '{{{key}}}' is not found in loaded CSV columns.")

        return True, warnings
