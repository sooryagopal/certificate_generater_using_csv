"""
TextField data model for AURELIA — Bulk Certificate Generator.
Represents a dynamic or static text field with typography, layout, and styling options.
Supports full {{ColumnName}} placeholder interpolation, case transformation,
and backward-compatible preset serialization.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from core.placeholder_engine import PlaceholderEngine


@dataclass
class TextField:
    """
    Represents a customizable text element rendered on the certificate canvas.
    Coordinates (x, y) and max_width are normalized (0.0 to 1.0) relative to
    the certificate template's dimensions to ensure scale-independent rendering.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "New Text Field"
    is_static: bool = False
    static_text: str = ""
    column_name: str = ""
    placeholder: Optional[str] = None  # e.g., "{{Name}}"
    template_text: str = ""            # e.g., "Awarded to {{Name}} for {{EventName}}"
    x: float = 0.50  # 50% across width (center default)
    y: float = 0.50  # 50% down height (center default)
    font_family: str = "Arial"
    font_path: Optional[str] = None
    font_size: int = 42
    text_color: str = "#D4AF37"  # Default elegant gold
    bold: bool = False
    italic: bool = False
    align_h: str = "center"  # 'left', 'center', 'right'
    align_v: str = "center"  # 'top', 'center', 'bottom'
    max_width: Optional[float] = None  # Normalized width for text wrapping (0.0 to 1.0)
    wrap_text: bool = False
    line_spacing: float = 1.2
    letter_spacing: int = 0  # Additional tracking / character spacing in pixels
    rotation: float = 0.0  # Rotation in degrees
    stroke_color: Optional[str] = None  # Text outline color
    stroke_width: int = 0  # Text outline thickness
    bg_color: Optional[str] = None  # Optional background fill box behind text
    is_visible: bool = True
    order: int = 0
    transform_case: str = "none"  # 'none', 'uppercase', 'lowercase', 'titlecase'

    def __post_init__(self) -> None:
        """Ensure placeholder syntax is always set if column_name is present."""
        if self.column_name and not self.placeholder:
            self.placeholder = PlaceholderEngine.generate_placeholder(self.column_name)

    def resolve_text(self, record: Optional[Dict[str, Any]] = None) -> str:
        """
        Resolves the final string to render using record data, single column binding,
        or complex string with embedded {{Placeholders}}.
        Preserves leading zeroes, Unicode characters, and literal formatting.
        Applies case transformations safely.
        """
        raw_text = ""

        # 1. Check if template_text is defined with embedded placeholders
        if self.template_text and "{{" in self.template_text:
            if record is not None:
                raw_text = PlaceholderEngine.resolve_string(self.template_text, record, missing_placeholder_fallback="")
            else:
                raw_text = self.template_text

        # 2. Static text field (may also contain {{Placeholders}})
        elif self.is_static:
            if "{{" in self.static_text and record is not None:
                raw_text = PlaceholderEngine.resolve_string(self.static_text, record, missing_placeholder_fallback="")
            else:
                raw_text = self.static_text or ""

        # 3. Dynamic field bound to a specific CSV column
        elif self.column_name:
            if record is not None:
                # Direct lookup
                val = record.get(self.column_name)
                # Case-insensitive fallback if exact key not found
                if val is None:
                    col_lower = self.column_name.strip().lower()
                    for k, v in record.items():
                        if k.strip().lower() == col_lower:
                            val = v
                            break
                raw_text = "" if val is None else str(val)
            else:
                raw_text = self.placeholder or PlaceholderEngine.generate_placeholder(self.column_name)

        # 4. Fallback when unconfigured
        else:
            raw_text = self.placeholder or PlaceholderEngine.generate_placeholder(self.name)

        # Apply casing transformation
        if self.transform_case == "uppercase":
            return raw_text.upper()
        elif self.transform_case == "lowercase":
            return raw_text.lower()
        elif self.transform_case == "titlecase":
            return raw_text.title()
        return raw_text

    def copy(self) -> TextField:
        """Create a deep copy of this text field with a new unique ID."""
        data = asdict(self)
        data["id"] = uuid.uuid4().hex[:8]
        data["name"] = f"{self.name} (Copy)"
        # Offset slightly for immediate visual feedback
        data["x"] = min(1.0, self.x + 0.02)
        data["y"] = min(1.0, self.y + 0.02)
        return TextField.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize field to dictionary for JSON storage."""
        d = asdict(self)
        d["type"] = "static" if self.is_static else "dynamic"
        d["column"] = self.column_name
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TextField:
        """Instantiate TextField safely from dictionary with backward compatibility for versions 1 and 2."""
        filtered = dict(data)

        # Migration helpers for alternative schema keys
        if "column" in filtered and "column_name" not in filtered:
            filtered["column_name"] = str(filtered["column"])
        if "type" in filtered and "is_static" not in filtered:
            filtered["is_static"] = (filtered["type"] == "static")
        if "color" in filtered and "text_color" not in filtered:
            filtered["text_color"] = str(filtered["color"])
        if "align" in filtered and "align_h" not in filtered:
            filtered["align_h"] = str(filtered["align"])

        valid_keys = set(cls.__dataclass_fields__.keys())
        clean_data = {k: v for k, v in filtered.items() if k in valid_keys}

        # Auto-compute placeholder if missing
        if clean_data.get("column_name") and not clean_data.get("placeholder"):
            clean_data["placeholder"] = PlaceholderEngine.generate_placeholder(clean_data["column_name"])

        # Enforce types and clamping
        if "x" in clean_data:
            clean_data["x"] = max(0.0, min(1.0, float(clean_data["x"])))
        if "y" in clean_data:
            clean_data["y"] = max(0.0, min(1.0, float(clean_data["y"])))
        if "font_size" in clean_data:
            clean_data["font_size"] = max(6, int(clean_data["font_size"]))
        if "line_spacing" in clean_data:
            clean_data["line_spacing"] = max(0.5, float(clean_data["line_spacing"]))
        if "letter_spacing" in clean_data:
            clean_data["letter_spacing"] = int(clean_data["letter_spacing"])
        if "rotation" in clean_data:
            clean_data["rotation"] = float(clean_data["rotation"]) % 360
        if "align_h" in clean_data and clean_data["align_h"] not in ("left", "center", "right"):
            clean_data["align_h"] = "center"
        if "align_v" in clean_data and clean_data["align_v"] not in ("top", "center", "bottom"):
            clean_data["align_v"] = "center"

        return cls(**clean_data)
