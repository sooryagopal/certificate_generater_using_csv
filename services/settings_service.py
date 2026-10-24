"""
Settings Service module for AURELIA — Bulk Certificate Generator.
Persists application preferences, recent files, and defaults in user home directory.
"""

from __future__ import annotations
import os
import json
from typing import Dict, Any, List, Optional


class SettingsService:
    """Stores and retrieves user application configuration."""

    DEFAULT_SETTINGS = {
        "theme": "dark",
        "last_output_dir": "",
        "default_export_format": "pdf",
        "default_filename_pattern": "{Name}_{RollNumber}",
        "collision_policy": "append_row",
        "create_subfolders": True,
        "preview_zoom": 1.0,
        "snap_to_grid": True,
        "recent_csvs": [],
        "recent_templates": [],
        "default_font_family": "Arial",
        "default_font_size": 42,
        "default_font_color": "#D4AF37",
        "target_dpi": 300,
        "image_quality": 95,
    }

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = config_dir
        else:
            home = os.path.expanduser("~")
            self.config_dir = os.path.join(home, ".config", "aurelia")
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_file = os.path.join(self.config_dir, "settings.json")
        self._settings: Dict[str, Any] = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Loads settings from disk, applying default fallbacks."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Merge with defaults
                        merged = self.DEFAULT_SETTINGS.copy()
                        merged.update(data)
                        return merged
            except Exception:
                pass
        return self.DEFAULT_SETTINGS.copy()

    def save(self) -> None:
        """Flushes in-memory settings to JSON file."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save()

    def add_recent_csv(self, filepath: str) -> None:
        """Adds file path to recent CSVs list (up to 10 recents)."""
        recents = self._settings.get("recent_csvs", [])
        if filepath in recents:
            recents.remove(filepath)
        recents.insert(0, filepath)
        self._settings["recent_csvs"] = recents[:10]
        self.save()

    def add_recent_template(self, filepath: str) -> None:
        """Adds file path to recent templates list (up to 10 recents)."""
        recents = self._settings.get("recent_templates", [])
        if filepath in recents:
            recents.remove(filepath)
        recents.insert(0, filepath)
        self._settings["recent_templates"] = recents[:10]
        self.save()

    def reset_to_defaults(self) -> None:
        """Restores default application configuration."""
        self._settings = self.DEFAULT_SETTINGS.copy()
        self.save()
