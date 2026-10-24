"""
Theme & Visual Styling definitions for AURELIA — Bulk Certificate Generator.
Defines the luxury Black & Gold color palette, fonts, and widget styling tokens.
"""

from __future__ import annotations
import customtkinter as ctk


class AureliaTheme:
    """Luxury creative studio theme tokens."""

    # Color Palette
    BG_MAIN = "#0B0B0D"           # Pitch black primary background
    BG_PANEL = "#151518"          # Dark charcoal primary container
    BG_PANEL_ALT = "#1D1D21"      # Elevated charcoal secondary surface
    BG_INPUT = "#111114"          # Deep input field background
    BORDER = "#2A2A30"            # Subtle container border
    BORDER_LIGHT = "#3D3D45"      # Hover container border

    # Gold Accents
    GOLD_PRIMARY = "#D4AF37"      # Regal metallic gold
    GOLD_HOVER = "#B99426"        # Deepened gold hover state
    GOLD_MUTED = "#554415"        # Low-contrast gold badge / border
    GOLD_SUBTLE = "#262010"       # Faint gold background highlight

    # Typography Colors
    TEXT_MAIN = "#F5F1E5"         # Warm off-white primary text
    TEXT_MUTED = "#A6A29A"        # Sophisticated subdued secondary text
    TEXT_DISABLED = "#5C5A55"     # Disabled placeholder text

    # State Feedback
    SUCCESS = "#42B883"           # Emerald success indicator
    SUCCESS_MUTED = "#163D2B"
    ERROR = "#FF6B6B"             # Vibrant coral error indicator
    ERROR_MUTED = "#451B1B"
    WARNING = "#F5A623"           # Amber warning indicator

    # Selection & Overlay
    SELECTION_BOX = "#D4AF37"
    HANDLE_FILL = "#F5F1E5"
    GUIDELINE_COLOR = "#D4AF37"

    @classmethod
    def apply_appearance(cls) -> None:
        """Configures CustomTkinter application-wide default dark appearance."""
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

    @classmethod
    def get_font(cls, size: int = 13, weight: str = "normal") -> ctk.CTkFont:
        """Returns standard UI font."""
        return ctk.CTkFont(family="Helvetica", size=size, weight=weight)
