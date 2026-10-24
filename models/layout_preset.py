"""
LayoutPreset data model for AURELIA — Bulk Certificate Generator.
Defines reusable layout configurations that can be serialized to JSON.
"""

from __future__ import annotations
import json
import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from models.text_field import TextField
from models.strike_line import StrikeLine


@dataclass
class LayoutPreset:
    """
    Encapsulates a complete reusable certificate typography, field, and strike-through line layout.
    """
    name: str = "Default Layout"
    version: str = "2.0"
    description: str = "Certificate layout preset"
    template_width: int = 1920
    template_height: int = 1080
    template_name: Optional[str] = None
    fields: List[TextField] = field(default_factory=list)
    lines: List[StrikeLine] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary suitable for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "template_width": self.template_width,
            "template_height": self.template_height,
            "template_name": self.template_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "fields": [f.to_dict() for f in self.fields],
            "lines": [l.to_dict() for l in self.lines],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize preset to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayoutPreset:
        """Load and validate preset from dictionary with backwards compatibility for versions 1 and 2."""
        cls.validate_dict(data)
        
        raw_fields = data.get("fields", [])
        loaded_fields = [TextField.from_dict(f) for f in raw_fields if isinstance(f, dict)]

        raw_lines = data.get("lines", [])
        loaded_lines = [StrikeLine.from_dict(l) for l in raw_lines if isinstance(l, dict)]
        
        return cls(
            name=str(data.get("name", "Untitled Preset")),
            version=str(data.get("version", "2.0")),
            description=str(data.get("description", "")),
            template_width=int(data.get("template_width", 1920)),
            template_height=int(data.get("template_height", 1080)),
            template_name=data.get("template_name"),
            fields=loaded_fields,
            lines=loaded_lines,
            created_at=str(data.get("created_at", datetime.datetime.now().isoformat())),
            updated_at=str(data.get("updated_at", datetime.datetime.now().isoformat())),
        )

    @classmethod
    def from_json(cls, json_str: str) -> LayoutPreset:
        """Parse JSON string into LayoutPreset instance."""
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise ValueError("Preset JSON root must be an object/dictionary.")
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, filepath: str) -> LayoutPreset:
        """Loads and parses a LayoutPreset directly from a JSON file path."""
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    @staticmethod
    def validate_dict(data: Dict[str, Any]) -> None:
        """Validate preset schema structure before instantiating."""
        if not isinstance(data, dict):
            raise ValueError("Invalid preset data: root must be a dictionary.")
        if "name" not in data or not str(data["name"]).strip():
            raise ValueError("Preset must contain a non-empty 'name' field.")
        if "fields" in data and not isinstance(data["fields"], list):
            raise ValueError("Preset 'fields' attribute must be a list.")
