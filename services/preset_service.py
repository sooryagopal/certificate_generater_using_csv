"""
Preset Service module for AURELIA — Bulk Certificate Generator.
Manages disk storage, schema validation, importing, exporting, and listing
of reusable certificate layout presets in JSON format.
"""

from __future__ import annotations
import os
import json
import glob
from typing import List, Optional, Tuple
from models.layout_preset import LayoutPreset


class PresetError(Exception):
    """Exception for layout preset operations."""
    pass


class PresetService:
    """Manages preset library on filesystem."""

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            # Standard user config directory
            home = os.path.expanduser("~")
            self.storage_dir = os.path.join(home, ".config", "aurelia", "presets")
        os.makedirs(self.storage_dir, exist_ok=True)

    def list_presets(self) -> List[str]:
        """Returns list of preset names found in storage directory."""
        files = glob.glob(os.path.join(self.storage_dir, "*.json"))
        names = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    if isinstance(data, dict) and "name" in data:
                        names.append(data["name"])
                    else:
                        base = os.path.splitext(os.path.basename(f))[0]
                        names.append(base)
            except Exception:
                continue
        return sorted(names)

    def _get_preset_path(self, name: str) -> str:
        """Sanitizes name to filename in storage dir."""
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()
        return os.path.join(self.storage_dir, f"{safe_name}.json")

    def save_preset(self, preset: LayoutPreset) -> str:
        """Saves or updates preset to storage directory."""
        path = self._get_preset_path(preset.name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(preset.to_json(indent=2))
            return path
        except Exception as e:
            raise PresetError(f"Failed to save preset '{preset.name}': {str(e)}") from e

    def load_preset_by_name(self, name: str) -> LayoutPreset:
        """Loads preset from storage directory by name."""
        # Try direct name lookup first
        path = self._get_preset_path(name)
        if os.path.exists(path):
            return self.load_preset_from_file(path)

        # Iterate files to match metadata name
        for f in glob.glob(os.path.join(self.storage_dir, "*.json")):
            try:
                preset = self.load_preset_from_file(f)
                if preset.name == name:
                    return preset
            except Exception:
                continue

        raise PresetError(f"Preset '{name}' was not found.")

    def load_preset_from_file(self, filepath: str) -> LayoutPreset:
        """Loads and strictly validates a preset JSON file."""
        if not os.path.exists(filepath):
            raise PresetError(f"Preset file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            preset = LayoutPreset.from_json(content)
            return preset
        except Exception as e:
            raise PresetError(f"Invalid preset file: {str(e)}") from e

    def delete_preset(self, name: str) -> bool:
        """Deletes preset file matching name."""
        path = self._get_preset_path(name)
        if os.path.exists(path):
            os.remove(path)
            return True

        for f in glob.glob(os.path.join(self.storage_dir, "*.json")):
            try:
                preset = self.load_preset_from_file(f)
                if preset.name == name:
                    os.remove(f)
                    return True
            except Exception:
                continue
        return False

    def duplicate_preset(self, name: str, new_name: str) -> LayoutPreset:
        """Clones an existing preset under a new name."""
        original = self.load_preset_by_name(name)
        clone = LayoutPreset(
            name=new_name,
            version=original.version,
            description=f"Copy of {original.name}",
            template_width=original.template_width,
            template_height=original.template_height,
            template_name=original.template_name,
            fields=[f.copy() for f in original.fields],
        )
        self.save_preset(clone)
        return clone

    def export_preset_to_file(self, name: str, target_path: str) -> str:
        """Exports a preset to an external JSON path."""
        preset = self.load_preset_by_name(name)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(preset.to_json(indent=2))
        return target_path

    def import_preset_from_file(self, filepath: str) -> LayoutPreset:
        """Imports an external JSON preset into the user preset library."""
        preset = self.load_preset_from_file(filepath)
        self.save_preset(preset)
        return preset
