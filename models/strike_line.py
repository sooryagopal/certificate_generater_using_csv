"""
StrikeLine data model for AURELIA — Bulk Certificate Generator.
Represents an editable, manual strike-through line overlay on the certificate canvas.
Coordinates (x, y) and length are normalized (0.0 to 1.0) relative to template dimensions.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class StrikeLine:
    """
    Represents an editable horizontal strike-through line placed manually on the certificate.
    x: Normalized center horizontal position (0.0 to 1.0)
    y: Normalized vertical position (0.0 to 1.0)
    length: Normalized line span (0.005 to 1.0)
    thickness: Line stroke width in pixels
    color: Line color hex code
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Strike Line"
    x: float = 0.50
    y: float = 0.55
    length: float = 0.14
    thickness: int = 3
    color: str = "#D4AF37"
    is_visible: bool = True
    order: int = 0

    @property
    def x1(self) -> float:
        """Left normalized coordinate."""
        return max(0.0, self.x - self.length / 2.0)

    @property
    def x2(self) -> float:
        """Right normalized coordinate."""
        return min(1.0, self.x + self.length / 2.0)

    def set_endpoints(self, x1: float, x2: float) -> None:
        """Updates center X and length given two horizontal endpoints."""
        left = max(0.0, min(x1, x2))
        right = min(1.0, max(x1, x2))
        self.length = max(0.005, right - left)
        self.x = (left + right) / 2.0

    def copy(self) -> StrikeLine:
        """Create a deep copy of this strike-through line with a new ID."""
        d = self.to_dict()
        d["id"] = uuid.uuid4().hex[:8]
        d["name"] = f"{self.name} (Copy)"
        d["y"] = min(0.98, self.y + 0.02)
        return StrikeLine.from_dict(d)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize line to dictionary for JSON preset storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StrikeLine:
        """Instantiate StrikeLine safely from dictionary."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        clean = {k: v for k, v in data.items() if k in valid_keys}

        if "x" in clean:
            clean["x"] = max(0.0, min(1.0, float(clean["x"])))
        if "y" in clean:
            clean["y"] = max(0.0, min(1.0, float(clean["y"])))
        if "length" in clean:
            clean["length"] = max(0.005, min(1.0, float(clean["length"])))
        if "thickness" in clean:
            clean["thickness"] = max(1, int(clean["thickness"]))
        if "color" not in clean or not clean["color"]:
            clean["color"] = "#D4AF37"

        return cls(**clean)
