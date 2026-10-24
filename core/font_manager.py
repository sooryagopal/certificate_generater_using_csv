"""
Font Manager module for AURELIA — Bulk Certificate Generator.
Scans system fonts across macOS, Windows, and Linux.
Provides TTF/OTF caching, fallback mechanisms, and Unicode/Tamil font resolution.
"""

from __future__ import annotations
import os
import sys
import glob
from typing import Dict, List, Optional, Tuple
from PIL import ImageFont


class FontManager:
    """Discovers, caches, and resolves fonts for certificate text rendering."""

    _instance: Optional[FontManager] = None
    _font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
    _system_fonts: Dict[str, str] = {}  # {Family Name: Path}
    _initialized: bool = False

    FONT_SIZE_PRESETS = {
        "Title": 72,
        "Header": 52,
        "Large": 40,
        "Medium": 32,
        "Small": 24,
        "Fine Print": 18,
    }

    def __new__(cls) -> FontManager:
        if cls._instance is None:
            cls._instance = super(FontManager, cls).__new__(cls)
            cls._instance._scan_system_fonts()
        return cls._instance

    def _scan_system_fonts(self) -> None:
        """Scan standard operating system directories for TTF and OTF font files."""
        if self._initialized:
            return

        search_paths: List[str] = []
        if sys.platform == "darwin":  # macOS
            search_paths = [
                "/System/Library/Fonts",
                "/System/Library/Fonts/Supplemental",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]
        elif sys.platform == "win32":  # Windows
            windir = os.environ.get("WINDIR", "C:\\Windows")
            search_paths = [
                os.path.join(windir, "Fonts"),
                os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts"),
            ]
        else:  # Linux & BSD
            search_paths = [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts"),
            ]

        discovered: Dict[str, str] = {}
        extensions = ("*.ttf", "*.otf", "*.ttc")

        for base_dir in search_paths:
            if not os.path.exists(base_dir):
                continue
            for ext in extensions:
                for font_path in glob.glob(os.path.join(base_dir, "**", ext), recursive=True):
                    # Derive a clean family display name from file name
                    fname = os.path.basename(font_path)
                    root_name, _ = os.path.splitext(fname)
                    clean_name = root_name.replace("-", " ").replace("_", " ")
                    if clean_name not in discovered:
                        discovered[clean_name] = font_path

        self._system_fonts = discovered
        self._initialized = True

    def get_available_font_names(self) -> List[str]:
        """Returns sorted list of all discovered font names."""
        common_defaults = ["Arial", "Helvetica", "Times New Roman", "Georgia", "Courier New", "Verdana", "Trebuchet MS"]
        all_names = set(self._system_fonts.keys())
        # Sort so common fonts appear first, then alphabetical
        sorted_fonts = sorted(
            list(all_names),
            key=lambda x: (0 if any(c.lower() in x.lower() for c in common_defaults) else 1, x.lower()),
        )
        return sorted_fonts

    def resolve_font_path(self, font_family: str, font_path: Optional[str] = None) -> Optional[str]:
        """Resolves font path from family name or custom path."""
        if font_path and os.path.exists(font_path):
            return font_path

        if font_family in self._system_fonts:
            return self._system_fonts[font_family]

        # Case-insensitive search
        family_lower = font_family.lower()
        for name, path in self._system_fonts.items():
            if name.lower() == family_lower:
                return path

        # Partial match
        for name, path in self._system_fonts.items():
            if family_lower in name.lower():
                return path

        return None

    def get_font(
        self,
        font_family: str = "Arial",
        font_path: Optional[str] = None,
        font_size: int = 36,
        bold: bool = False,
        italic: bool = False,
    ) -> ImageFont.FreeTypeFont:
        """
        Retrieves a PIL ImageFont instance with caching and reliable fallbacks.
        """
        font_size = max(6, int(font_size))
        cache_key = (f"{font_path or font_family}_{bold}_{italic}", font_size)

        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        resolved_path = self.resolve_font_path(font_family, font_path)

        # If bold/italic was requested and no explicit path, try finding variant
        if resolved_path and not font_path:
            resolved_path = self._find_styled_variant(resolved_path, bold, italic)

        font_obj = None
        if resolved_path and os.path.exists(resolved_path):
            try:
                font_obj = ImageFont.truetype(resolved_path, size=font_size)
            except Exception:
                font_obj = None

        if font_obj is None:
            # Fallback to system default or any available TTF
            font_obj = self._get_fallback_font(font_size)

        self._font_cache[cache_key] = font_obj
        return font_obj

    def _find_styled_variant(self, base_path: str, bold: bool, italic: bool) -> str:
        """Attempts to locate bold, italic, or bold-italic variants of a font family."""
        if not bold and not italic:
            return base_path

        dir_name = os.path.dirname(base_path)
        base_name, ext = os.path.splitext(os.path.basename(base_path))

        candidates = []
        if bold and italic:
            candidates.extend([f"{base_name}BoldItalic{ext}", f"{base_name}-BoldItalic{ext}", f"{base_name}_BoldItalic{ext}", f"{base_name}BI{ext}"])
        elif bold:
            candidates.extend([f"{base_name}Bold{ext}", f"{base_name}-Bold{ext}", f"{base_name}_Bold{ext}", f"{base_name}B{ext}"])
        elif italic:
            candidates.extend([f"{base_name}Italic{ext}", f"{base_name}-Italic{ext}", f"{base_name}_Italic{ext}", f"{base_name}I{ext}", f"{base_name}Oblique{ext}"])

        for cand in candidates:
            cand_path = os.path.join(dir_name, cand)
            if os.path.exists(cand_path):
                return cand_path

        return base_path

    def _get_fallback_font(self, font_size: int) -> ImageFont.FreeTypeFont:
        """Finds any valid TTF font on the system or loads PIL default."""
        fallback_names = [
            "Arial", "Helvetica", "DejaVuSans", "LiberationSans", "Verdana",
            "AppleGothic", "NotoSans", "Times New Roman"
        ]
        for name in fallback_names:
            path = self.resolve_font_path(name)
            if path and os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=font_size)
                except Exception:
                    continue

        # If any system font is found
        for path in self._system_fonts.values():
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=font_size)
                except Exception:
                    continue

        return ImageFont.load_default()
