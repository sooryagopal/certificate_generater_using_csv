"""
Field Inspector Panel for AURELIA — Bulk Certificate Generator.
Provides controls for adding, deleting, reordering, and fine-tuning
text fields, typography, alignments, positions, and styling.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import colorchooser, filedialog
from typing import Optional, List, Callable, Any
import customtkinter as ctk

from ui.theme import AureliaTheme
from models.text_field import TextField
from core.layout_manager import LayoutManager
from core.font_manager import FontManager


class FieldPanel(ctk.CTkFrame):
    """Right sidebar panel for inspecting and styling certificate fields."""

    def __init__(
        self,
        master: Any,
        layout_manager: LayoutManager,
        on_change: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ):
        super().__init__(master, fg_color=AureliaTheme.BG_PANEL, corner_radius=0, width=340, **kwargs)

        self.layout_manager = layout_manager
        self.on_change = on_change
        self.font_manager = FontManager()

        self.available_columns: List[str] = []
        self._updating_ui: bool = False

        self._build_ui()
        self.refresh_field_list()

    def set_csv_columns(self, columns: List[str]) -> None:
        """Updates available CSV column options in dropdowns and quick-select chips."""
        self.available_columns = columns
        values = columns if columns else ["(No CSV Columns)"]
        self.combo_column.configure(values=values)
        if self.available_columns:
            curr = self.combo_column.get()
            if not curr or curr == "(No CSV Columns)" or curr not in self.available_columns:
                self.combo_column.set(self.available_columns[0])
        else:
            self.combo_column.set("(No CSV Columns)")
        self._refresh_column_chips()
        self.refresh_field_list()

    def _build_ui(self) -> None:
        """Builds scrollable inspector controls."""
        # Top Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=14, pady=(14, 8))

        lbl_title = ctk.CTkLabel(
            header_frame,
            text="TEXT FIELDS",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        lbl_title.pack(side="left")

        # Field Action Buttons
        btn_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_add = ctk.CTkButton(
            btn_box, text="+ Add", width=54, height=26,
            fg_color=AureliaTheme.GOLD_PRIMARY, hover_color=AureliaTheme.GOLD_HOVER,
            text_color="#000000", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_add_field,
        )
        self.btn_add.pack(side="left", padx=2)

        self.btn_dup = ctk.CTkButton(
            btn_box, text="Duplicate", width=64, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=self._on_duplicate_field,
        )
        self.btn_dup.pack(side="left", padx=2)

        self.btn_del = ctk.CTkButton(
            btn_box, text="Delete", width=50, height=26,
            fg_color=AureliaTheme.ERROR_MUTED, hover_color=AureliaTheme.ERROR,
            text_color=AureliaTheme.ERROR, font=ctk.CTkFont(size=11),
            command=self._on_delete_field,
        )
        self.btn_del.pack(side="left", padx=2)

        # Field Listbox / Selector
        self.field_list_container = ctk.CTkScrollableFrame(
            self, fg_color=AureliaTheme.BG_PANEL_ALT, height=110, corner_radius=6
        )
        self.field_list_container.pack(fill="x", padx=14, pady=4)
        self.field_buttons: List[ctk.CTkButton] = []

        # Layer reorder controls
        reorder_frame = ctk.CTkFrame(self, fg_color="transparent")
        reorder_frame.pack(fill="x", padx=14, pady=(2, 8))

        self.btn_move_up = ctk.CTkButton(
            reorder_frame, text="▲ Layer Up", width=80, height=22,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10),
            command=lambda: self._on_reorder(-1),
        )
        self.btn_move_up.pack(side="left", padx=2)

        self.btn_move_down = ctk.CTkButton(
            reorder_frame, text="▼ Layer Down", width=90, height=22,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10),
            command=lambda: self._on_reorder(1),
        )
        self.btn_move_down.pack(side="left", padx=2)

        self.btn_visibility = ctk.CTkButton(
            reorder_frame, text="👁 Toggle Hide", width=95, height=22,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10),
            command=self._on_toggle_visibility,
        )
        self.btn_visibility.pack(side="right", padx=2)

        # Scrollable Settings Container
        self.settings_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.settings_scroll.pack(fill="both", expand=True, padx=10, pady=4)

        self._build_inspector_sections(self.settings_scroll)

    def _build_inspector_sections(self, parent: Any) -> None:
        """Constructs individual field editing parameter controls."""
        # 1. Field Label & Type
        sec_label = ctk.CTkLabel(parent, text="MAPPING & CONTENT", font=ctk.CTkFont(size=11, weight="bold"), text_color=AureliaTheme.GOLD_PRIMARY)
        sec_label.pack(anchor="w", padx=4, pady=(8, 4))

        self.entry_name = ctk.CTkEntry(parent, placeholder_text="Field Identifier Label", fg_color=AureliaTheme.BG_INPUT)
        self.entry_name.pack(fill="x", padx=4, pady=3)
        self.entry_name.bind("<KeyRelease>", lambda e: self._on_prop_change("name", self.entry_name.get()))

        # Dynamic vs Static segmented button
        self.seg_type = ctk.CTkSegmentedButton(
            parent, values=["Dynamic (CSV)", "Static Text"],
            selected_color=AureliaTheme.GOLD_PRIMARY, selected_hover_color=AureliaTheme.GOLD_HOVER,
            unselected_color=AureliaTheme.BG_PANEL_ALT, unselected_hover_color=AureliaTheme.BORDER,
            text_color="#000000",
            command=self._on_type_switched,
        )
        self.seg_type.pack(fill="x", padx=4, pady=4)
        self.seg_type.set("Dynamic (CSV)")

        # Dynamic: CSV Column Dropdown
        self.frame_dynamic = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame_dynamic.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(self.frame_dynamic, text="CSV Column:", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.combo_column = ctk.CTkComboBox(
            self.frame_dynamic, values=["(No CSV Columns)"],
            fg_color=AureliaTheme.BG_INPUT, dropdown_fg_color=AureliaTheme.BG_PANEL_ALT,
            command=lambda val: self._on_prop_change("column_name", val),
        )
        self.combo_column.pack(fill="x", pady=2)

        # Quick-select column chips
        self.lbl_quick_cols = ctk.CTkLabel(
            self.frame_dynamic, text="Quick Select Column:",
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10)
        )
        self.lbl_quick_cols.pack(anchor="w", pady=(4, 1))

        self.column_chips_frame = ctk.CTkFrame(self.frame_dynamic, fg_color="transparent")
        self.column_chips_frame.pack(fill="x", pady=(0, 4))
        self._refresh_column_chips()

        # Multi-placeholder template text row
        template_header = ctk.CTkFrame(self.frame_dynamic, fg_color="transparent")
        template_header.pack(fill="x", pady=(6, 2))
        ctk.CTkLabel(template_header, text="Template / Multi-Tag Text:", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")

        self.btn_insert_ph = ctk.CTkButton(
            template_header, text="+ Tag ▾", width=65, height=22,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.GOLD_PRIMARY, font=ctk.CTkFont(size=10, weight="bold"),
            command=self._show_insert_placeholder_menu,
        )
        self.btn_insert_ph.pack(side="right")

        self.entry_template_text = ctk.CTkEntry(
            self.frame_dynamic,
            placeholder_text="e.g. Awarded to {{Name}} for {{EventName}}",
            fg_color=AureliaTheme.BG_INPUT,
        )
        self.entry_template_text.pack(fill="x", pady=2)
        self.entry_template_text.bind("<KeyRelease>", lambda e: self._on_prop_change("template_text", self.entry_template_text.get()))

        # Static: Fixed Text Input
        self.frame_static = ctk.CTkFrame(parent, fg_color="transparent")
        static_header = ctk.CTkFrame(self.frame_static, fg_color="transparent")
        static_header.pack(fill="x", pady=(2, 2))
        ctk.CTkLabel(static_header, text="Static Text:", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")

        self.btn_static_insert_ph = ctk.CTkButton(
            static_header, text="+ Tag ▾", width=65, height=22,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.GOLD_PRIMARY, font=ctk.CTkFont(size=10, weight="bold"),
            command=self._show_static_insert_placeholder_menu,
        )
        self.btn_static_insert_ph.pack(side="right")

        self.entry_static = ctk.CTkEntry(self.frame_static, placeholder_text="e.g. For Outstanding Performance", fg_color=AureliaTheme.BG_INPUT)
        self.entry_static.pack(fill="x", pady=2)
        self.entry_static.bind("<KeyRelease>", lambda e: self._on_prop_change("static_text", self.entry_static.get()))

        # 2. Typography
        sec_typo = ctk.CTkLabel(parent, text="TYPOGRAPHY", font=ctk.CTkFont(size=11, weight="bold"), text_color=AureliaTheme.GOLD_PRIMARY)
        sec_typo.pack(anchor="w", padx=4, pady=(12, 4))

        # Font Family + Custom TTF Browse
        font_box = ctk.CTkFrame(parent, fg_color="transparent")
        font_box.pack(fill="x", padx=4, pady=2)

        available_fonts = self.font_manager.get_available_font_names()[:40] or ["Arial", "Helvetica", "Times New Roman"]
        self.combo_font = ctk.CTkComboBox(
            font_box, values=available_fonts, width=200,
            fg_color=AureliaTheme.BG_INPUT, dropdown_fg_color=AureliaTheme.BG_PANEL_ALT,
            command=lambda val: self._on_prop_change("font_family", val),
        )
        self.combo_font.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_browse_font = ctk.CTkButton(
            font_box, text="Browse TTF...", width=80, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=self._on_browse_custom_font,
        )
        self.btn_browse_font.pack(side="right")

        # Font Size Slider & Presets
        size_frame = ctk.CTkFrame(parent, fg_color="transparent")
        size_frame.pack(fill="x", padx=4, pady=2)
        self.lbl_font_size = ctk.CTkLabel(size_frame, text="Size: 42 pt", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_font_size.pack(side="left")

        self.slider_font_size = ctk.CTkSlider(
            parent, from_=8, to=140, number_of_steps=132,
            button_color=AureliaTheme.GOLD_PRIMARY, progress_color=AureliaTheme.GOLD_PRIMARY,
            command=self._on_font_size_slide,
        )
        self.slider_font_size.pack(fill="x", padx=4, pady=2)

        # Size Preset Buttons
        preset_box = ctk.CTkFrame(parent, fg_color="transparent")
        preset_box.pack(fill="x", padx=4, pady=2)
        for label, sz in [("Small (24)", 24), ("Medium (36)", 36), ("Large (48)", 48), ("Title (72)", 72)]:
            btn = ctk.CTkButton(
                preset_box, text=label, height=22, width=65,
                fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
                text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10),
                command=lambda s=sz: self._set_font_size(s),
            )
            btn.pack(side="left", padx=2, expand=True)

        # Style & Casing Toggles (Bold, Italic, Case)
        style_box = ctk.CTkFrame(parent, fg_color="transparent")
        style_box.pack(fill="x", padx=4, pady=4)

        self.chk_bold = ctk.CTkCheckBox(
            style_box, text="Bold", width=65, checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=lambda: self._on_prop_change("bold", bool(self.chk_bold.get())),
        )
        self.chk_bold.pack(side="left", padx=2)

        self.chk_italic = ctk.CTkCheckBox(
            style_box, text="Italic", width=65, checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=lambda: self._on_prop_change("italic", bool(self.chk_italic.get())),
        )
        self.chk_italic.pack(side="left", padx=2)

        self.combo_case = ctk.CTkComboBox(
            style_box, values=["none", "uppercase", "lowercase", "titlecase"], width=110, height=24,
            fg_color=AureliaTheme.BG_INPUT, dropdown_fg_color=AureliaTheme.BG_PANEL_ALT,
            font=ctk.CTkFont(size=11),
            command=lambda val: self._on_prop_change("transform_case", val),
        )
        self.combo_case.pack(side="right", padx=2)

        # Color Picker Swatches
        color_frame = ctk.CTkFrame(parent, fg_color="transparent")
        color_frame.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(color_frame, text="Color:", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")

        self.entry_color = ctk.CTkEntry(color_frame, width=80, height=26, fg_color=AureliaTheme.BG_INPUT)
        self.entry_color.pack(side="left", padx=6)
        self.entry_color.bind("<KeyRelease>", lambda e: self._on_color_entry_change())

        self.color_preview = ctk.CTkButton(
            color_frame, text="", width=26, height=26, corner_radius=13,
            fg_color=AureliaTheme.GOLD_PRIMARY, hover_color=AureliaTheme.GOLD_HOVER,
            command=self._on_pick_color,
        )
        self.color_preview.pack(side="left", padx=2)

        # Quick Luxury Swatches
        for swatch_hex in ["#D4AF37", "#F5F1E5", "#FFFFFF", "#151518", "#B99426", "#42B883"]:
            s_btn = ctk.CTkButton(
                color_frame, text="", width=18, height=18, corner_radius=9,
                fg_color=swatch_hex, hover_color=swatch_hex,
                command=lambda c=swatch_hex: self._apply_color(c),
            )
            s_btn.pack(side="left", padx=1)

        # 3. Alignment
        sec_align = ctk.CTkLabel(parent, text="ALIGNMENT & POSITION", font=ctk.CTkFont(size=11, weight="bold"), text_color=AureliaTheme.GOLD_PRIMARY)
        sec_align.pack(anchor="w", padx=4, pady=(12, 4))

        # Horizontal alignment
        self.seg_align_h = ctk.CTkSegmentedButton(
            parent, values=["left", "center", "right"],
            selected_color=AureliaTheme.GOLD_PRIMARY, selected_hover_color=AureliaTheme.GOLD_HOVER,
            unselected_color=AureliaTheme.BG_PANEL_ALT, unselected_hover_color=AureliaTheme.BORDER,
            text_color="#000000",
            command=lambda val: self._on_prop_change("align_h", val),
        )
        self.seg_align_h.pack(fill="x", padx=4, pady=2)

        # Position X and Y Sliders
        pos_x_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pos_x_frame.pack(fill="x", padx=4, pady=2)
        self.lbl_pos_x = ctk.CTkLabel(pos_x_frame, text="X Position: 50%", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_pos_x.pack(side="left")

        self.slider_pos_x = ctk.CTkSlider(
            parent, from_=0.0, to=1.0, number_of_steps=200,
            button_color=AureliaTheme.GOLD_PRIMARY, progress_color=AureliaTheme.GOLD_PRIMARY,
            command=lambda v: self._on_pos_slide("x", v),
        )
        self.slider_pos_x.pack(fill="x", padx=4, pady=2)

        pos_y_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pos_y_frame.pack(fill="x", padx=4, pady=2)
        self.lbl_pos_y = ctk.CTkLabel(pos_y_frame, text="Y Position: 50%", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_pos_y.pack(side="left")

        self.slider_pos_y = ctk.CTkSlider(
            parent, from_=0.0, to=1.0, number_of_steps=200,
            button_color=AureliaTheme.GOLD_PRIMARY, progress_color=AureliaTheme.GOLD_PRIMARY,
            command=lambda v: self._on_pos_slide("y", v),
        )
        self.slider_pos_y.pack(fill="x", padx=4, pady=2)

        # Center on Certificate Action
        btn_center = ctk.CTkButton(
            parent, text="Center on Certificate", height=24,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=self._center_selected_field,
        )
        btn_center.pack(fill="x", padx=4, pady=4)

        # 4. Advanced Typography (Wrapping, Tracking, Rotation)
        sec_adv = ctk.CTkLabel(parent, text="ADVANCED STYLING", font=ctk.CTkFont(size=11, weight="bold"), text_color=AureliaTheme.GOLD_PRIMARY)
        sec_adv.pack(anchor="w", padx=4, pady=(12, 4))

        # Text Wrapping
        self.chk_wrap = ctk.CTkCheckBox(
            parent, text="Wrap Text to Max Width", checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=lambda: self._on_prop_change("wrap_text", bool(self.chk_wrap.get())),
        )
        self.chk_wrap.pack(anchor="w", padx=4, pady=2)

        self.lbl_max_width = ctk.CTkLabel(parent, text="Max Width: 80%", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_max_width.pack(anchor="w", padx=4)
        self.slider_max_width = ctk.CTkSlider(
            parent, from_=0.10, to=1.0, number_of_steps=90,
            button_color=AureliaTheme.GOLD_PRIMARY, progress_color=AureliaTheme.GOLD_PRIMARY,
            command=lambda v: self._on_max_width_slide(v),
        )
        self.slider_max_width.pack(fill="x", padx=4, pady=2)

        # Letter Spacing / Tracking
        self.lbl_spacing = ctk.CTkLabel(parent, text="Character Tracking: 0 px", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_spacing.pack(anchor="w", padx=4)
        self.slider_spacing = ctk.CTkSlider(
            parent, from_=0, to=30, number_of_steps=30,
            button_color=AureliaTheme.GOLD_PRIMARY, progress_color=AureliaTheme.GOLD_PRIMARY,
            command=lambda v: self._on_spacing_slide(v),
        )
        self.slider_spacing.pack(fill="x", padx=4, pady=2)

        # Rotation
        self.lbl_rotation = ctk.CTkLabel(parent, text="Rotation: 0°", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11))
        self.lbl_rotation.pack(anchor="w", padx=4)
        self.slider_rotation = ctk.CTkSlider(
            parent, from_=-180, to=180, number_of_steps=360,
            button_color=AureliaTheme.GOLD_PRIMARY, progress_color=AureliaTheme.GOLD_PRIMARY,
            command=lambda v: self._on_rotation_slide(v),
        )
        self.slider_rotation.pack(fill="x", padx=4, pady=(2, 14))

    # -------------------------------------------------------------------------
    # Synchronization with Active Layout
    # -------------------------------------------------------------------------

    def refresh_field_list(self) -> None:
        """Re-populates the list of field buttons."""
        for btn in self.field_buttons:
            btn.destroy()
        self.field_buttons.clear()

        selected_id = self.layout_manager.selected_field_id

        for f in self.layout_manager.fields:
            status_symbol = "●" if f.is_visible else "○"
            type_symbol = "§" if f.is_static else "⌘"
            btn_text = f"{status_symbol} {type_symbol} {f.name}"

            is_selected = (f.id == selected_id)
            fg_color = AureliaTheme.GOLD_MUTED if is_selected else AureliaTheme.BG_PANEL
            text_color = AureliaTheme.TEXT_MAIN if f.is_visible else AureliaTheme.TEXT_DISABLED

            btn = ctk.CTkButton(
                self.field_list_container,
                text=btn_text,
                anchor="w",
                height=26,
                fg_color=fg_color,
                hover_color=AureliaTheme.BORDER,
                text_color=text_color,
                font=ctk.CTkFont(size=11, weight="bold" if is_selected else "normal"),
                command=lambda field_id=f.id: self._select_field(field_id),
            )
            btn.pack(fill="x", pady=1)
            self.field_buttons.append(btn)

        self.load_selected_field()

    def load_selected_field(self) -> None:
        """Pulls attributes from currently selected field into UI inputs."""
        field_obj = self.layout_manager.get_selected_field()
        if not field_obj:
            return

        self._updating_ui = True
        try:
            self.entry_name.delete(0, "end")
            self.entry_name.insert(0, field_obj.name)

            if field_obj.is_static:
                self.seg_type.set("Static Text")
                self.frame_dynamic.pack_forget()
                self.frame_static.pack(fill="x", padx=4, pady=2)
                self.entry_static.delete(0, "end")
                self.entry_static.insert(0, field_obj.static_text)
            else:
                self.seg_type.set("Dynamic (CSV)")
                self.frame_static.pack_forget()
                self.frame_dynamic.pack(fill="x", padx=4, pady=2)
                self.entry_template_text.delete(0, "end")
                self.entry_template_text.insert(0, field_obj.template_text or "")
                if self.available_columns:
                    col_to_set = field_obj.column_name if field_obj.column_name in self.available_columns else self.available_columns[0]
                    self.combo_column.set(col_to_set)
                    if not field_obj.column_name or field_obj.column_name not in self.available_columns:
                        field_obj.column_name = col_to_set
                else:
                    self.combo_column.set("(No CSV Columns)")
                self._refresh_column_chips()

            # Font
            self.combo_font.set(field_obj.font_family)
            self.lbl_font_size.configure(text=f"Size: {field_obj.font_size} pt")
            self.slider_font_size.set(field_obj.font_size)

            # Style
            if field_obj.bold:
                self.chk_bold.select()
            else:
                self.chk_bold.deselect()

            if field_obj.italic:
                self.chk_italic.select()
            else:
                self.chk_italic.deselect()

            self.combo_case.set(field_obj.transform_case)

            # Color
            self.entry_color.delete(0, "end")
            self.entry_color.insert(0, field_obj.text_color)
            self.color_preview.configure(fg_color=field_obj.text_color, hover_color=field_obj.text_color)

            # Alignment & Position
            self.seg_align_h.set(field_obj.align_h)
            self.lbl_pos_x.configure(text=f"X Position: {int(field_obj.x * 100)}%")
            self.slider_pos_x.set(field_obj.x)
            self.lbl_pos_y.configure(text=f"Y Position: {int(field_obj.y * 100)}%")
            self.slider_pos_y.set(field_obj.y)

            # Advanced
            if field_obj.wrap_text:
                self.chk_wrap.select()
            else:
                self.chk_wrap.deselect()

            max_w_val = field_obj.max_width if field_obj.max_width else 0.80
            self.lbl_max_width.configure(text=f"Max Width: {int(max_w_val * 100)}%")
            self.slider_max_width.set(max_w_val)

            self.lbl_spacing.configure(text=f"Character Tracking: {field_obj.letter_spacing} px")
            self.slider_spacing.set(field_obj.letter_spacing)

            self.lbl_rotation.configure(text=f"Rotation: {int(field_obj.rotation)}°")
            self.slider_rotation.set(field_obj.rotation)

        finally:
            self._updating_ui = False

    # -------------------------------------------------------------------------
    # Internal Handlers
    # -------------------------------------------------------------------------

    def _select_field(self, field_id: str) -> None:
        self.layout_manager.select_field(field_id)
        self.refresh_field_list()
        if self.on_change:
            self.on_change()

    def _on_prop_change(self, prop: str, value: Any) -> None:
        if self._updating_ui:
            return
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.update_field_property(selected.id, **{prop: value})
            if prop in ("name", "is_static", "is_visible"):
                self.refresh_field_list()
            if self.on_change:
                self.on_change()

    def _refresh_column_chips(self) -> None:
        """Renders quick-select chip buttons for all detected CSV columns."""
        if not hasattr(self, "column_chips_frame"):
            return

        for child in self.column_chips_frame.winfo_children():
            child.destroy()

        if not self.available_columns:
            lbl = ctk.CTkLabel(
                self.column_chips_frame, text="Upload a CSV to view columns",
                text_color=AureliaTheme.TEXT_DISABLED, font=ctk.CTkFont(size=10)
            )
            lbl.pack(anchor="w")
            return

        selected_col = self.combo_column.get()
        row_frame = None
        for i, col in enumerate(self.available_columns):
            if i % 3 == 0:
                row_frame = ctk.CTkFrame(self.column_chips_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=1)

            is_active = (col == selected_col)
            btn = ctk.CTkButton(
                row_frame,
                text=col,
                height=22,
                fg_color=AureliaTheme.GOLD_PRIMARY if is_active else AureliaTheme.BG_INPUT,
                hover_color=AureliaTheme.GOLD_HOVER if is_active else AureliaTheme.BORDER,
                text_color="#000000" if is_active else AureliaTheme.TEXT_MAIN,
                font=ctk.CTkFont(size=10, weight="bold" if is_active else "normal"),
                command=lambda c=col: self._assign_column(c),
            )
            btn.pack(side="left", padx=1, expand=True, fill="x")

    def _assign_column(self, col_name: str) -> None:
        """Assigns column to current field and updates label."""
        self.combo_column.set(col_name)
        selected = self.layout_manager.get_selected_field()
        if selected:
            new_name = selected.name
            if not selected.name or "Field" in selected.name or selected.name in self.available_columns:
                new_name = col_name
            self.entry_name.delete(0, "end")
            self.entry_name.insert(0, new_name)
            self.layout_manager.update_field_property(selected.id, column_name=col_name, name=new_name)
            self._refresh_column_chips()
            self.refresh_field_list()
            if self.on_change:
                self.on_change()

    def _on_type_switched(self, choice: str) -> None:
        is_static = (choice == "Static Text")
        self._on_prop_change("is_static", is_static)
        self.load_selected_field()

    def _on_font_size_slide(self, val: float) -> None:
        sz = int(val)
        self.lbl_font_size.configure(text=f"Size: {sz} pt")
        self._on_prop_change("font_size", sz)

    def _set_font_size(self, sz: int) -> None:
        self.slider_font_size.set(sz)
        self.lbl_font_size.configure(text=f"Size: {sz} pt")
        self._on_prop_change("font_size", sz)

    def _on_pos_slide(self, axis: str, val: float) -> None:
        if axis == "x":
            self.lbl_pos_x.configure(text=f"X Position: {int(val * 100)}%")
        else:
            self.lbl_pos_y.configure(text=f"Y Position: {int(val * 100)}%")
        self._on_prop_change(axis, val)

    def _on_max_width_slide(self, val: float) -> None:
        self.lbl_max_width.configure(text=f"Max Width: {int(val * 100)}%")
        self._on_prop_change("max_width", val)

    def _on_spacing_slide(self, val: float) -> None:
        sp = int(val)
        self.lbl_spacing.configure(text=f"Character Tracking: {sp} px")
        self._on_prop_change("letter_spacing", sp)

    def _on_rotation_slide(self, val: float) -> None:
        deg = int(val)
        self.lbl_rotation.configure(text=f"Rotation: {deg}°")
        self._on_prop_change("rotation", deg)

    def _apply_color(self, hex_code: str) -> None:
        self.entry_color.delete(0, "end")
        self.entry_color.insert(0, hex_code)
        self.color_preview.configure(fg_color=hex_code, hover_color=hex_code)
        self._on_prop_change("text_color", hex_code)

    def _on_color_entry_change(self) -> None:
        val = self.entry_color.get().strip()
        if val.startswith("#") and len(val) in (4, 7):
            self.color_preview.configure(fg_color=val, hover_color=val)
            self._on_prop_change("text_color", val)

    def _on_pick_color(self) -> None:
        curr = self.entry_color.get().strip() or "#D4AF37"
        color = colorchooser.askcolor(color=curr, title="AURELIA — Select Text Color")
        if color and color[1]:
            self._apply_color(color[1])

    def _on_browse_custom_font(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Select Custom TTF/OTF Font File",
            filetypes=[("Font Files", "*.ttf *.otf *.ttc"), ("All Files", "*.*")],
        )
        if filepath:
            self.layout_manager.update_field_property(
                self.layout_manager.selected_field_id,
                font_path=filepath,
                font_family=os.path.basename(filepath),
            )
            self.load_selected_field()
            if self.on_change:
                self.on_change()

    def _center_selected_field(self) -> None:
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.update_field_property(selected.id, x=0.50, align_h="center")
            self.load_selected_field()
            if self.on_change:
                self.on_change()

    def _on_add_field(self) -> None:
        col = self.available_columns[0] if self.available_columns else ""
        name = f"Field {len(self.layout_manager.fields) + 1}" if not col else col
        self.layout_manager.add_field(name=name, column_name=col)
        self.refresh_field_list()
        if self.on_change:
            self.on_change()

    def _on_duplicate_field(self) -> None:
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.duplicate_field(selected.id)
            self.refresh_field_list()
            if self.on_change:
                self.on_change()

    def _on_delete_field(self) -> None:
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.delete_field(selected.id)
            self.refresh_field_list()
            if self.on_change:
                self.on_change()

    def _on_reorder(self, direction: int) -> None:
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.move_field_order(selected.id, direction)
            self.refresh_field_list()
            if self.on_change:
                self.on_change()

    def _on_toggle_visibility(self) -> None:
        selected = self.layout_manager.get_selected_field()
        if selected:
            new_vis = not selected.is_visible
            self.layout_manager.update_field_property(selected.id, is_visible=new_vis)
            self.refresh_field_list()
            if self.on_change:
                self.on_change()

    def _show_insert_placeholder_menu(self) -> None:
        """Pops up menu of detected CSV column tags to insert into template_text."""
        if not self.available_columns:
            return
        menu = tk.Menu(self, tearoff=0)
        for col in self.available_columns:
            tag = f"{{{{{col}}}}}"
            menu.add_command(label=f"{col} ({tag})", command=lambda t=tag: self._insert_tag_to_template_text(t))
        menu.tk_popup(self.btn_insert_ph.winfo_rootx(), self.btn_insert_ph.winfo_rooty() + 24)

    def _insert_tag_to_template_text(self, tag: str) -> None:
        curr = self.entry_template_text.get()
        pos = self.entry_template_text.index(tk.INSERT)
        new_text = curr[:pos] + tag + curr[pos:]
        self.entry_template_text.delete(0, "end")
        self.entry_template_text.insert(0, new_text)
        self.entry_template_text.icursor(pos + len(tag))
        self._on_prop_change("template_text", new_text)

    def _show_static_insert_placeholder_menu(self) -> None:
        """Pops up menu of detected CSV column tags to insert into static_text."""
        if not self.available_columns:
            return
        menu = tk.Menu(self, tearoff=0)
        for col in self.available_columns:
            tag = f"{{{{{col}}}}}"
            menu.add_command(label=f"{col} ({tag})", command=lambda t=tag: self._insert_tag_to_static_text(t))
        menu.tk_popup(self.btn_static_insert_ph.winfo_rootx(), self.btn_static_insert_ph.winfo_rooty() + 24)

    def _insert_tag_to_static_text(self, tag: str) -> None:
        curr = self.entry_static.get()
        pos = self.entry_static.index(tk.INSERT)
        new_text = curr[:pos] + tag + curr[pos:]
        self.entry_static.delete(0, "end")
        self.entry_static.insert(0, new_text)
        self.entry_static.icursor(pos + len(tag))
        self._on_prop_change("static_text", new_text)

