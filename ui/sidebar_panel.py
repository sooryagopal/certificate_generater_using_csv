"""
Left Sidebar Panel for AURELIA — Bulk Certificate Generator.
Coordinates Step 1 (CSV Upload), Step 2 (Template Upload), Step 3 (Presets),
Step 4 (Output Folder & Filename Configuration), and Step 5 (Validation & Generation CTA).
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Optional, Callable, Any, List
import customtkinter as ctk

from ui.theme import AureliaTheme
from core.csv_reader import CSVReader, CSVData
from core.template_loader import TemplateLoader, TemplateData
from core.layout_manager import LayoutManager
from core.filename_utils import CollisionPolicy
from services.preset_service import PresetService
from services.settings_service import SettingsService
from ui.dialogs import CSVPreviewDialog


class SidebarPanel(ctk.CTkFrame):
    """Left sidebar guiding user through workflow steps."""

    def __init__(
        self,
        master: Any,
        layout_manager: LayoutManager,
        preset_service: PresetService,
        settings_service: SettingsService,
        on_csv_loaded: Callable[[CSVData], None],
        on_template_loaded: Callable[[TemplateData], None],
        on_run_preflight: Callable[[], None],
        on_start_generation: Callable[[], None],
        **kwargs: Any,
    ):
        super().__init__(master, fg_color=AureliaTheme.BG_PANEL, corner_radius=0, width=330, **kwargs)

        self.layout_manager = layout_manager
        self.preset_service = preset_service
        self.settings_service = settings_service
        self.on_csv_loaded = on_csv_loaded
        self.on_template_loaded = on_template_loaded
        self.on_run_preflight = on_run_preflight
        self.on_start_generation = on_start_generation

        # State
        self.csv_data: Optional[CSVData] = None
        self.template_data: Optional[TemplateData] = None
        self.output_dir: str = self.settings_service.get("last_output_dir", "") or os.path.abspath("output")

        self._build_ui()

    def _build_ui(self) -> None:
        """Constructs scrollable workflow sections."""
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------------------------------------------------------------
        # STEP 1: CSV Upload
        # ---------------------------------------------------------------------
        self._build_section_header("1. RECIPIENT DATA (CSV)")

        self.btn_upload_csv = ctk.CTkButton(
            self.scroll, text="Upload CSV File...", height=34,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER_LIGHT,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_upload_csv,
        )
        self.btn_upload_csv.pack(fill="x", padx=4, pady=4)

        # CSV Status Card
        self.card_csv = ctk.CTkFrame(self.scroll, fg_color=AureliaTheme.BG_PANEL_ALT, corner_radius=6)
        self.card_csv.pack(fill="x", padx=4, pady=4)

        self.lbl_csv_status = ctk.CTkLabel(
            self.card_csv, text="No CSV file loaded",
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11),
            wraplength=280, justify="left",
        )
        self.lbl_csv_status.pack(anchor="w", padx=10, pady=8)

        # CSV Action Row (Preview Table & Delimiter)
        self.csv_action_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.csv_action_row.pack(fill="x", padx=4, pady=2)

        self.btn_preview_csv = ctk.CTkButton(
            self.csv_action_row, text="View Table", width=95, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11),
            state="disabled", command=self._on_preview_csv_table,
        )
        self.btn_preview_csv.pack(side="left")

        self.combo_delim = ctk.CTkComboBox(
            self.csv_action_row, values=["Auto Delimiter", "Comma (,)", "Semicolon (;)", "Tab (\\t)", "Pipe (|)"],
            width=160, height=26, fg_color=AureliaTheme.BG_INPUT,
            dropdown_fg_color=AureliaTheme.BG_PANEL_ALT, font=ctk.CTkFont(size=11),
            command=self._on_delimiter_changed,
        )
        self.combo_delim.pack(side="right")

        # Detected Columns Visual Section Box
        self.frame_columns_box = ctk.CTkFrame(self.scroll, fg_color=AureliaTheme.BG_PANEL_ALT, corner_radius=6)
        self.frame_columns_box.pack(fill="x", padx=4, pady=(6, 2))

        self.lbl_columns_title = ctk.CTkLabel(
            self.frame_columns_box,
            text="DETECTED CSV COLUMNS (0)",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        self.lbl_columns_title.pack(anchor="w", padx=8, pady=(6, 2))

        self.frame_columns_chips = ctk.CTkFrame(self.frame_columns_box, fg_color="transparent")
        self.frame_columns_chips.pack(fill="x", padx=6, pady=2)

        self.lbl_no_cols = ctk.CTkLabel(
            self.frame_columns_chips,
            text="Upload a CSV file to view detected columns.",
            font=ctk.CTkFont(size=10),
            text_color=AureliaTheme.TEXT_DISABLED,
        )
        self.lbl_no_cols.pack(anchor="w", padx=2, pady=4)

        # Auto-create fields button
        self.btn_auto_create_fields = ctk.CTkButton(
            self.frame_columns_box,
            text="⚡ Auto-Create Fields from Columns",
            height=26,
            fg_color=AureliaTheme.BG_MAIN,
            hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.GOLD_PRIMARY,
            font=ctk.CTkFont(size=10, weight="bold"),
            state="disabled",
            command=self._on_auto_create_all_fields,
        )
        self.btn_auto_create_fields.pack(fill="x", padx=6, pady=(2, 6))

        # ---------------------------------------------------------------------
        # STEP 2: Template Upload
        # ---------------------------------------------------------------------
        self._build_section_header("2. CERTIFICATE TEMPLATE")

        self.btn_upload_tpl = ctk.CTkButton(
            self.scroll, text="Upload Template (PNG, JPG, PDF)...", height=34,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER_LIGHT,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_upload_template,
        )
        self.btn_upload_tpl.pack(fill="x", padx=4, pady=4)

        # Template Status Card
        self.card_tpl = ctk.CTkFrame(self.scroll, fg_color=AureliaTheme.BG_PANEL_ALT, corner_radius=6)
        self.card_tpl.pack(fill="x", padx=4, pady=4)

        self.lbl_tpl_status = ctk.CTkLabel(
            self.card_tpl, text="No Template loaded",
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11),
            wraplength=280, justify="left",
        )
        self.lbl_tpl_status.pack(anchor="w", padx=10, pady=8)

        # PDF Page Selector (hidden by default)
        self.frame_pdf_pages = ctk.CTkFrame(self.scroll, fg_color="transparent")
        ctk.CTkLabel(self.frame_pdf_pages, text="PDF Page:", font=ctk.CTkFont(size=11), text_color=AureliaTheme.TEXT_MUTED).pack(side="left", padx=4)
        self.combo_pdf_pages = ctk.CTkComboBox(
            self.frame_pdf_pages, values=["Page 1"], width=100, height=24,
            fg_color=AureliaTheme.BG_INPUT, command=self._on_pdf_page_changed,
        )
        self.combo_pdf_pages.pack(side="left", padx=4)

        # ---------------------------------------------------------------------
        # STEP 3: Presets Library
        # ---------------------------------------------------------------------
        self._build_section_header("3. LAYOUT PRESETS")

        preset_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        preset_row.pack(fill="x", padx=4, pady=2)

        preset_names = self.preset_service.list_presets() or ["(No Saved Presets)"]
        self.combo_presets = ctk.CTkComboBox(
            preset_row, values=preset_names, width=170, height=28,
            fg_color=AureliaTheme.BG_INPUT, dropdown_fg_color=AureliaTheme.BG_PANEL_ALT,
            command=self._on_preset_selected,
        )
        self.combo_presets.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_save_preset = ctk.CTkButton(
            preset_row, text="Save", width=50, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=self._on_save_preset,
        )
        self.btn_save_preset.pack(side="left", padx=2)

        self.btn_preset_menu = ctk.CTkButton(
            preset_row, text="More ▾", width=55, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, command=self._on_preset_more_options,
        )
        self.btn_preset_menu.pack(side="right")

        # ---------------------------------------------------------------------
        # STEP 4: Output & Filename Configuration
        # ---------------------------------------------------------------------
        self._build_section_header("4. OUTPUT DESTINATION & NAMING")

        # Output Folder Picker
        ctk.CTkLabel(self.scroll, text="Output Directory:", font=ctk.CTkFont(size=11), text_color=AureliaTheme.TEXT_MUTED).pack(anchor="w", padx=4)

        dest_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        dest_frame.pack(fill="x", padx=4, pady=2)

        self.entry_dest = ctk.CTkEntry(dest_frame, placeholder_text="Select destination folder...", fg_color=AureliaTheme.BG_INPUT)
        self.entry_dest.insert(0, self.output_dir)
        self.entry_dest.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_browse_dest = ctk.CTkButton(
            dest_frame, text="Browse...", width=70, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=self._on_browse_output_dir,
        )
        self.btn_browse_dest.pack(side="right")

        # Subfolder & Batch Name
        self.chk_subfolder = ctk.CTkCheckBox(
            self.scroll, text="Create subfolder for this batch", checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
        )
        self.chk_subfolder.select()
        self.chk_subfolder.pack(anchor="w", padx=4, pady=(6, 2))

        self.entry_batch_name = ctk.CTkEntry(self.scroll, placeholder_text="Batch Folder Name (e.g. NEWELLS_3.0)", fg_color=AureliaTheme.BG_INPUT)
        self.entry_batch_name.insert(0, "Certificates_Batch")
        self.entry_batch_name.pack(fill="x", padx=4, pady=2)

        # Filename Pattern
        ctk.CTkLabel(self.scroll, text="Filename Pattern:", font=ctk.CTkFont(size=11), text_color=AureliaTheme.TEXT_MUTED).pack(anchor="w", padx=4, pady=(6, 0))

        default_pat = self.settings_service.get("default_filename_pattern", "{Name}_{RollNumber}")
        self.entry_pattern = ctk.CTkEntry(self.scroll, placeholder_text="{Name}_{RollNumber}", fg_color=AureliaTheme.BG_INPUT)
        self.entry_pattern.insert(0, default_pat)
        self.entry_pattern.pack(fill="x", padx=4, pady=2)

        # Quick tag insert helper buttons
        self.tag_helper_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.tag_helper_frame.pack(fill="x", padx=4, pady=2)
        self._refresh_tag_helpers()

        # Export Format
        ctk.CTkLabel(self.scroll, text="Export Format:", font=ctk.CTkFont(size=11), text_color=AureliaTheme.TEXT_MUTED).pack(anchor="w", padx=4, pady=(6, 0))

        self.combo_format = ctk.CTkComboBox(
            self.scroll,
            values=[
                "Individual PDF Certificates",
                "Individual PNG Certificates",
                "Individual JPG Certificates",
                "Individual PDF + PNG Images",
                "Individual PDF + JPG Images",
                "Combined Multi-Page PDF Only",
            ],
            fg_color=AureliaTheme.BG_INPUT, dropdown_fg_color=AureliaTheme.BG_PANEL_ALT,
        )
        self.combo_format.pack(fill="x", padx=4, pady=2)
        self.combo_format.set("Individual PDF Certificates")

        # Checkbox for combined PDF
        self.chk_combined_pdf = ctk.CTkCheckBox(
            self.scroll, text="Also compile combined multi-page PDF", checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
        )
        self.chk_combined_pdf.select()
        self.chk_combined_pdf.pack(anchor="w", padx=4, pady=4)

        # Collision Policy
        ctk.CTkLabel(self.scroll, text="Filename Collision Policy:", font=ctk.CTkFont(size=11), text_color=AureliaTheme.TEXT_MUTED).pack(anchor="w", padx=4, pady=(4, 0))

        self.combo_collision = ctk.CTkComboBox(
            self.scroll,
            values=["Append Row Number", "Append Unique Suffix", "Skip Existing Files", "Overwrite Existing"],
            fg_color=AureliaTheme.BG_INPUT, dropdown_fg_color=AureliaTheme.BG_PANEL_ALT,
        )
        self.combo_collision.pack(fill="x", padx=4, pady=2)
        self.combo_collision.set("Append Row Number")

        # ---------------------------------------------------------------------
        # STEP 5: Pre-Flight Check & Generate CTA
        # ---------------------------------------------------------------------
        self._build_section_header("5. AUDIT & EXECUTION")

        self.btn_preflight = ctk.CTkButton(
            self.scroll, text="🔍 Pre-Flight Diagnostic Check", height=32,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER_LIGHT,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=self.on_run_preflight,
        )
        self.btn_preflight.pack(fill="x", padx=4, pady=4)

        # Prominent Gold CTA Button
        self.btn_generate = ctk.CTkButton(
            self.scroll,
            text="⚡ GENERATE CERTIFICATES",
            height=46,
            corner_radius=8,
            fg_color=AureliaTheme.GOLD_PRIMARY,
            hover_color=AureliaTheme.GOLD_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_start_generation,
        )
        self.btn_generate.pack(fill="x", padx=4, pady=(8, 16))

    def _build_section_header(self, title: str) -> None:
        """Draws consistent section divider with gold heading."""
        sep = ctk.CTkFrame(self.scroll, height=1, fg_color=AureliaTheme.BORDER)
        sep.pack(fill="x", padx=4, pady=(14, 6))

        lbl = ctk.CTkLabel(
            self.scroll, text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        lbl.pack(anchor="w", padx=4, pady=(0, 4))

    def _refresh_tag_helpers(self) -> None:
        """Populates quick tag injection buttons based on detected CSV columns."""
        for child in self.tag_helper_frame.winfo_children():
            child.destroy()

        cols = ["row"]
        if self.csv_data:
            cols.extend(self.csv_data.columns[:4])

        ctk.CTkLabel(self.tag_helper_frame, text="Insert tag: ", text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10)).pack(side="left")
        for c in cols:
            b = ctk.CTkButton(
                self.tag_helper_frame, text=f"{{{c}}}", width=42, height=18,
                fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
                text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=9),
                command=lambda tag=f"{{{c}}}": self._insert_tag_to_pattern(tag),
            )
            b.pack(side="left", padx=1)

    def _insert_tag_to_pattern(self, tag: str) -> None:
        curr = self.entry_pattern.get()
        self.entry_pattern.delete(0, "end")
        self.entry_pattern.insert(0, f"{curr}_{tag}" if curr else tag)

    # -------------------------------------------------------------------------
    # CSV Upload & Delimiter
    # -------------------------------------------------------------------------

    def _on_upload_csv(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Select CSV Recipient File",
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not filepath:
            return

        self._load_csv_file(filepath)

    def _load_csv_file(self, filepath: str, forced_delim: Optional[str] = None) -> None:
        try:
            data = CSVReader.load_csv(filepath, forced_delimiter=forced_delim)
            self.csv_data = data
            self.settings_service.add_recent_csv(filepath)

            # Update UI Card
            status_lines = [
                f"📄 {data.filename}",
                f"Records: {data.row_count} | Delimiter: '{data.delimiter}' | {data.encoding}",
                f"Columns ({len(data.columns)}): {', '.join(data.columns[:5])}{'...' if len(data.columns) > 5 else ''}",
            ]
            self.lbl_csv_status.configure(text="\n".join(status_lines), text_color=AureliaTheme.TEXT_MAIN)
            self.btn_preview_csv.configure(state="normal", text_color=AureliaTheme.TEXT_MAIN)

            # Render detected columns
            self._render_detected_columns_chips()

            # Update tag helpers
            self._refresh_tag_helpers()

            # Notify MainWindow
            self.on_csv_loaded(data)

        except Exception as e:
            messagebox.showerror("CSV Loading Error", str(e))

    def _render_detected_columns_chips(self) -> None:
        """Renders interactive badges for all detected CSV columns in the sidebar."""
        for child in self.frame_columns_chips.winfo_children():
            child.destroy()

        if not self.csv_data or not self.csv_data.columns:
            lbl = ctk.CTkLabel(
                self.frame_columns_chips,
                text="Upload a CSV file to view detected columns.",
                font=ctk.CTkFont(size=10),
                text_color=AureliaTheme.TEXT_DISABLED,
            )
            lbl.pack(anchor="w", padx=2, pady=4)
            self.btn_auto_create_fields.configure(state="disabled")
            self.lbl_columns_title.configure(text="DETECTED CSV COLUMNS (0)")
            return

        cols = self.csv_data.columns
        self.lbl_columns_title.configure(text=f"DETECTED CSV COLUMNS ({len(cols)})")
        self.btn_auto_create_fields.configure(state="normal")

        # Instruction subtitle
        ctk.CTkLabel(
            self.frame_columns_chips,
            text="Click a column to add/map on certificate:",
            font=ctk.CTkFont(size=9),
            text_color=AureliaTheme.TEXT_MUTED,
        ).pack(anchor="w", padx=2, pady=(0, 2))

        # Flow of column buttons
        row_frame = None
        for i, col in enumerate(cols):
            if i % 2 == 0:
                row_frame = ctk.CTkFrame(self.frame_columns_chips, fg_color="transparent")
                row_frame.pack(fill="x", pady=1)

            btn = ctk.CTkButton(
                row_frame,
                text=f"+ {col}",
                height=24,
                fg_color=AureliaTheme.BG_INPUT,
                hover_color=AureliaTheme.GOLD_MUTED,
                text_color=AureliaTheme.GOLD_PRIMARY,
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda c=col: self._on_column_chip_clicked(c),
            )
            btn.pack(side="left", padx=2, expand=True, fill="x")

    def _on_column_chip_clicked(self, column_name: str) -> None:
        """Adds a field for this column or binds the currently selected dynamic field."""
        selected = self.layout_manager.get_selected_field()
        if selected and not selected.is_static and (not selected.column_name or selected.column_name not in (self.csv_data.columns if self.csv_data else [])):
            self.layout_manager.update_field_property(
                selected.id,
                column_name=column_name,
                name=column_name,
                placeholder=f"{{{{{column_name}}}}}",
            )
        else:
            self.layout_manager.add_placeholder_field(column_name=column_name)

    def _on_auto_create_all_fields(self) -> None:
        """Automatically creates beautifully styled fields for all detected CSV columns."""
        if not self.csv_data or not self.csv_data.columns:
            return

        cols = self.csv_data.columns
        confirm = messagebox.askyesno(
            "Auto-Create Fields",
            f"Are you sure you want to insert all {len(cols)} detected CSV columns as text fields on the certificate?\n\n"
            "This will reset the canvas layout and arrange each column in a structured vertical template.",
        )
        if not confirm:
            return

        self.layout_manager.insert_all_columns(cols)
        messagebox.showinfo(
            "Auto-Generated Fields",
            f"Successfully read {len(cols)} columns from CSV and generated certificate text fields!"
        )

    def _on_delimiter_changed(self, choice: str) -> None:
        if not self.csv_data:
            return
        delim_map = {
            "Auto Delimiter": None,
            "Comma (,)": ",",
            "Semicolon (;)": ";",
            "Tab (\\t)": "\t",
            "Pipe (|)": "|",
        }
        forced = delim_map.get(choice)
        self._load_csv_file(self.csv_data.filepath, forced_delim=forced)

    def _on_preview_csv_table(self) -> None:
        if self.csv_data:
            CSVPreviewDialog(self.winfo_toplevel(), self.csv_data.columns, self.csv_data.records)

    # -------------------------------------------------------------------------
    # Template Upload
    # -------------------------------------------------------------------------

    def _on_upload_template(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Select Certificate Graphic Template",
            filetypes=[
                ("Image & PDF Templates", "*.png *.jpg *.jpeg *.webp *.pdf"),
                ("Images", "*.png *.jpg *.jpeg *.webp"),
                ("PDF Documents", "*.pdf"),
                ("All Files", "*.*"),
            ],
        )
        if not filepath:
            return

        self._load_template_file(filepath)

    def _load_template_file(self, filepath: str, page_index: int = 0) -> None:
        try:
            tpl = TemplateLoader.load_template(filepath, page_index=page_index, dpi=300)
            self.template_data = tpl
            self.settings_service.add_recent_template(filepath)

            # Update UI Card
            status_lines = [
                f"🖼 {tpl.filename}",
                f"Dimensions: {tpl.width} × {tpl.height} px ({tpl.orientation})",
                f"Format: {'PDF Page ' + str(page_index + 1) if tpl.is_pdf else 'Raster Image'}",
            ]
            if tpl.warnings:
                status_lines.append(f"⚠️ {tpl.warnings[0]}")

            text_color = AureliaTheme.WARNING if tpl.is_low_resolution else AureliaTheme.TEXT_MAIN
            self.lbl_tpl_status.configure(text="\n".join(status_lines), text_color=text_color)

            # PDF Page Selector
            if tpl.is_pdf and tpl.total_pages > 1:
                self.frame_pdf_pages.pack(fill="x", padx=4, pady=4)
                pages_list = [f"Page {i+1}" for i in range(tpl.total_pages)]
                self.combo_pdf_pages.configure(values=pages_list)
                self.combo_pdf_pages.set(f"Page {page_index + 1}")
            else:
                self.frame_pdf_pages.pack_forget()

            self.on_template_loaded(tpl)

        except Exception as e:
            messagebox.showerror("Template Loading Error", str(e))

    def _on_pdf_page_changed(self, choice: str) -> None:
        if not self.template_data or not self.template_data.is_pdf:
            return
        page_idx = int(choice.replace("Page ", "")) - 1
        self._load_template_file(self.template_data.filepath, page_index=page_idx)

    # -------------------------------------------------------------------------
    # Presets Actions
    # -------------------------------------------------------------------------

    def _on_preset_selected(self, name: str) -> None:
        if name and name != "(No Saved Presets)":
            try:
                preset = self.preset_service.load_preset_by_name(name)
                self.layout_manager.load_preset(preset)
            except Exception as e:
                messagebox.showerror("Preset Load Error", str(e))

    def _on_save_preset(self) -> None:
        name = simpledialog.askstring("Save Preset", "Enter a name for this certificate layout preset:")
        if not name or not name.strip():
            return

        w = self.template_data.width if self.template_data else 1920
        h = self.template_data.height if self.template_data else 1080
        tpl_name = self.template_data.filename if self.template_data else None

        preset = self.layout_manager.export_to_preset(
            name=name.strip(),
            template_w=w,
            template_h=h,
            template_name=tpl_name,
        )
        self.preset_service.save_preset(preset)
        self.refresh_presets_list(select_name=preset.name)
        messagebox.showinfo("Preset Saved", f"Layout preset '{preset.name}' has been saved.")

    def _on_preset_more_options(self) -> None:
        curr = self.combo_presets.get()
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Duplicate Current Preset...", command=self._duplicate_current_preset)
        menu.add_command(label="Delete Current Preset", command=self._delete_current_preset)
        menu.add_separator()
        menu.add_command(label="Export Preset to JSON File...", command=self._export_preset_json)
        menu.add_command(label="Import Preset from JSON File...", command=self._import_preset_json)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def _duplicate_current_preset(self) -> None:
        curr = self.combo_presets.get()
        if not curr or curr == "(No Saved Presets)":
            return
        new_name = simpledialog.askstring("Duplicate Preset", f"Enter duplicate name for '{curr}':")
        if new_name and new_name.strip():
            clone = self.preset_service.duplicate_preset(curr, new_name.strip())
            self.refresh_presets_list(select_name=clone.name)

    def _delete_current_preset(self) -> None:
        curr = self.combo_presets.get()
        if not curr or curr == "(No Saved Presets)":
            return
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete preset '{curr}'?"):
            self.preset_service.delete_preset(curr)
            self.refresh_presets_list()

    def _export_preset_json(self) -> None:
        curr = self.combo_presets.get()
        if not curr or curr == "(No Saved Presets)":
            return
        path = filedialog.asksaveasfilename(
            title="Export Preset to JSON",
            defaultextension=".json",
            initialfile=f"{curr}.json",
            filetypes=[("JSON Files", "*.json")],
        )
        if path:
            self.preset_service.export_preset_to_file(curr, path)
            messagebox.showinfo("Export Successful", f"Preset exported to {path}")

    def _import_preset_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Import Preset from JSON",
            filetypes=[("JSON Files", "*.json")],
        )
        if path:
            try:
                preset = self.preset_service.import_preset_from_file(path)
                self.refresh_presets_list(select_name=preset.name)
                messagebox.showinfo("Import Successful", f"Preset '{preset.name}' imported.")
            except Exception as e:
                messagebox.showerror("Import Failed", str(e))

    def refresh_presets_list(self, select_name: Optional[str] = None) -> None:
        names = self.preset_service.list_presets()
        self.combo_presets.configure(values=names or ["(No Saved Presets)"])
        if select_name and select_name in names:
            self.combo_presets.set(select_name)
        elif names:
            self.combo_presets.set(names[0])

    # -------------------------------------------------------------------------
    # Output Directory & Settings
    # -------------------------------------------------------------------------

    def _on_browse_output_dir(self) -> None:
        dir_path = filedialog.askdirectory(
            title="Select Output Directory for Generated Certificates",
            initialdir=self.output_dir or os.getcwd(),
        )
        if dir_path:
            self.output_dir = dir_path
            self.entry_dest.delete(0, "end")
            self.entry_dest.insert(0, dir_path)
            self.settings_service.set("last_output_dir", dir_path)

    # -------------------------------------------------------------------------
    # Getters for Execution
    # -------------------------------------------------------------------------

    def get_output_dir(self) -> str:
        return self.entry_dest.get().strip()

    def get_batch_name(self) -> str:
        return self.entry_batch_name.get().strip() or "Certificates"

    def get_filename_pattern(self) -> str:
        return self.entry_pattern.get().strip() or "{Name}_{RollNumber}"

    def get_export_mode(self) -> str:
        choice = self.combo_format.get()
        mapping = {
            "Individual PDF Certificates": "pdf",
            "Individual PNG Certificates": "png",
            "Individual JPG Certificates": "jpg",
            "Individual PDF + PNG Images": "pdf_png",
            "Individual PDF + JPG Images": "pdf_jpg",
            "Combined Multi-Page PDF Only": "combined_pdf",
        }
        return mapping.get(choice, "pdf")

    def get_include_combined_pdf(self) -> bool:
        return bool(self.chk_combined_pdf.get())

    def get_create_subfolder(self) -> bool:
        return bool(self.chk_subfolder.get())

    def get_collision_policy(self) -> str:
        choice = self.combo_collision.get()
        mapping = {
            "Append Row Number": CollisionPolicy.APPEND_ROW,
            "Append Unique Suffix": CollisionPolicy.APPEND_UNIQUE,
            "Skip Existing Files": CollisionPolicy.SKIP,
            "Overwrite Existing": CollisionPolicy.OVERWRITE,
        }
        return mapping.get(choice, CollisionPolicy.APPEND_ROW)
