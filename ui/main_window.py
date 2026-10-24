"""
Main Window for AURELIA — Bulk Certificate Generator.
Integrates Header, Left Workflow Sidebar, Interactive Center Canvas,
Participant Record Switcher, Right Field Inspector, and Status Bar.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any, Tuple
import customtkinter as ctk

from ui.theme import AureliaTheme
from ui.canvas_editor import CanvasEditor
from ui.sidebar_panel import SidebarPanel
from ui.placeholder_panel import PlaceholderPanel
from ui.field_panel import FieldPanel
from ui.dialogs import ValidationDialog, GenerationProgressDialog
from core.layout_manager import LayoutManager
from core.csv_reader import CSVData
from core.template_loader import TemplateData
from core.validators import PreFlightValidator
from services.generation_service import GenerationService, GenerationOptions, GenerationProgress
from services.preset_service import PresetService
from services.settings_service import SettingsService


class MainWindow(ctk.CTk):
    """Main application window for AURELIA Studio."""

    def __init__(self) -> None:
        super().__init__()

        # Appearance & Window Configuration
        AureliaTheme.apply_appearance()
        self.title("AURELIA — Bulk Certificate Generator")
        self.geometry("1400x880")
        self.minsize(1050, 700)
        self.configure(fg_color=AureliaTheme.BG_MAIN)

        # Core Services & State
        self.layout_manager = LayoutManager()
        self.preset_service = PresetService()
        self.settings_service = SettingsService()
        self.generation_service = GenerationService()

        self.csv_data: Optional[CSVData] = None
        self.template_data: Optional[TemplateData] = None
        self.current_record_index: int = 0
        self.current_progress_dialog: Optional[GenerationProgressDialog] = None

        # Build Full UI
        self._build_header()
        self._build_main_body()
        self._build_status_bar()

        # Connect layout change callbacks
        self.layout_manager.register_callback(self._on_layout_manager_updated)

        # Set default initial field
        self.layout_manager.add_field(
            name="Recipient Name",
            column_name="Name",
            x=0.50,
            y=0.45,
            font_size=48,
            text_color="#D4AF37",
        )

        self._bind_global_shortcuts()

    # -------------------------------------------------------------------------
    # UI Layout Construction
    # -------------------------------------------------------------------------

    def _build_header(self) -> None:
        """Top luxury application bar with brand wordmark and quick actions."""
        self.header = ctk.CTkFrame(self, fg_color=AureliaTheme.BG_PANEL, height=56, corner_radius=0)
        self.header.pack(fill="x", side="top")

        # Brand Logo & Wordmark
        brand_box = ctk.CTkFrame(self.header, fg_color="transparent")
        brand_box.pack(side="left", padx=20, pady=8)

        lbl_logo = ctk.CTkLabel(
            brand_box, text="A U R E L I A",
            font=ctk.CTkFont(family="Georgia", size=18, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            brand_box, text="BULK CERTIFICATE GENERATOR STUDIO",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=AureliaTheme.TEXT_MUTED,
        )
        lbl_sub.pack(anchor="w")

        # Quick Actions on Right (Undo, Redo, Reset, Settings)
        action_box = ctk.CTkFrame(self.header, fg_color="transparent")
        action_box.pack(side="right", padx=16, pady=10)

        self.btn_undo = ctk.CTkButton(
            action_box, text="↶ Undo", width=68, height=30,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=self._on_undo,
        )
        self.btn_undo.pack(side="left", padx=3)

        self.btn_redo = ctk.CTkButton(
            action_box, text="↷ Redo", width=68, height=30,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=self._on_redo,
        )
        self.btn_redo.pack(side="left", padx=3)

        btn_reset = ctk.CTkButton(
            action_box, text="Reset Layout", width=95, height=30,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11),
            command=self._on_reset_layout,
        )
        btn_reset.pack(side="left", padx=3)

    def _build_main_body(self) -> None:
        """Constructs layout: Left Sidebar, Placeholders Panel, Center Canvas, Right Inspector."""
        self.body_container = ctk.CTkFrame(self, fg_color=AureliaTheme.BG_MAIN, corner_radius=0)
        self.body_container.pack(fill="both", expand=True)

        # 1. Left Sidebar
        self.sidebar = SidebarPanel(
            self.body_container,
            layout_manager=self.layout_manager,
            preset_service=self.preset_service,
            settings_service=self.settings_service,
            on_csv_loaded=self._on_csv_loaded,
            on_template_loaded=self._on_template_loaded,
            on_run_preflight=self._run_preflight_check,
            on_start_generation=self._prompt_and_generate,
        )
        self.sidebar.pack(side="left", fill="y", padx=(8, 2), pady=8)

        # 2. CSV Placeholders Collapsible Panel
        self.placeholder_panel = PlaceholderPanel(
            self.body_container,
            layout_manager=self.layout_manager,
            on_field_created=self._refresh_all,
            get_canvas_drop_coords=self._resolve_canvas_drop_coords,
        )
        self.placeholder_panel.pack(side="left", fill="y", padx=(2, 4), pady=8)

        # 3. Right Field Panel Inspector
        self.field_panel = FieldPanel(
            self.body_container,
            layout_manager=self.layout_manager,
            on_change=self._on_field_panel_changed,
        )
        self.field_panel.pack(side="right", fill="y", padx=(4, 8), pady=8)

        # 4. Center Workspace (Record Switcher Bar + Canvas Editor)
        self.center_workspace = ctk.CTkFrame(self.body_container, fg_color=AureliaTheme.BG_MAIN, corner_radius=0)
        self.center_workspace.pack(side="left", fill="both", expand=True, padx=4, pady=8)

        self._build_record_switcher(self.center_workspace)

        self.canvas_editor = CanvasEditor(
            self.center_workspace,
            layout_manager=self.layout_manager,
            on_field_selected=self._on_canvas_field_selected,
        )
        self.canvas_editor.pack(fill="both", expand=True)

    def _resolve_canvas_drop_coords(self, screen_x: int, screen_y: int) -> Optional[Tuple[float, float]]:
        """Resolves drop coordinates over the visual canvas editor."""
        if hasattr(self, "canvas_editor"):
            return self.canvas_editor.get_norm_from_screen(screen_x, screen_y)
        return None

    def _build_record_switcher(self, parent: Any) -> None:
        """Toolbar enabling switching preview records to test different participant names."""
        self.record_bar = ctk.CTkFrame(parent, fg_color=AureliaTheme.BG_PANEL, height=40, corner_radius=6)
        self.record_bar.pack(fill="x", padx=12, pady=(0, 6))

        # Record navigation buttons
        self.btn_first_rec = ctk.CTkButton(
            self.record_bar, text="|◀", width=30, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=lambda: self._set_record_index(0),
        )
        self.btn_first_rec.pack(side="left", padx=(10, 2), pady=6)

        self.btn_prev_rec = ctk.CTkButton(
            self.record_bar, text="◀ Prev", width=55, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=lambda: self._set_record_index(self.current_record_index - 1),
        )
        self.btn_prev_rec.pack(side="left", padx=2, pady=6)

        self.lbl_record_info = ctk.CTkLabel(
            self.record_bar, text="Preview: Sample Record",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=AureliaTheme.TEXT_MAIN,
        )
        self.lbl_record_info.pack(side="left", padx=14, pady=6)

        self.btn_next_rec = ctk.CTkButton(
            self.record_bar, text="Next ▶", width=55, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=11),
            command=lambda: self._set_record_index(self.current_record_index + 1),
        )
        self.btn_next_rec.pack(side="left", padx=2, pady=6)

        self.btn_last_rec = ctk.CTkButton(
            self.record_bar, text="▶|", width=30, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=self._jump_to_last_record,
        )
        self.btn_last_rec.pack(side="left", padx=2, pady=6)

        # Refresh Preview Fallback Button
        btn_refresh = ctk.CTkButton(
            self.record_bar, text="🔄 Refresh Preview", width=120, height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=11),
            command=self._refresh_all,
        )
        btn_refresh.pack(side="right", padx=10, pady=6)

    def _build_status_bar(self) -> None:
        """Bottom application status and diagnostic bar."""
        self.status_bar = ctk.CTkFrame(self, fg_color=AureliaTheme.BG_PANEL, height=26, corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")

        self.lbl_status = ctk.CTkLabel(
            self.status_bar, text="Ready. Load CSV and Certificate Template to start.",
            font=ctk.CTkFont(size=11), text_color=AureliaTheme.TEXT_MUTED,
        )
        self.lbl_status.pack(side="left", padx=16, pady=2)

        self.lbl_status_right = ctk.CTkLabel(
            self.status_bar, text="Local Studio • 300 DPI High-Fidelity Rendering",
            font=ctk.CTkFont(size=10), text_color=AureliaTheme.TEXT_DISABLED,
        )
        self.lbl_status_right.pack(side="right", padx=16, pady=2)

    def _bind_global_shortcuts(self) -> None:
        """Attaches system-wide keyboard shortcuts."""
        self.bind("<Control-z>", lambda e: self._on_undo())
        self.bind("<Command-z>", lambda e: self._on_undo())
        self.bind("<Control-y>", lambda e: self._on_redo())
        self.bind("<Command-y>", lambda e: self._on_redo())
        self.bind("<Control-d>", lambda e: self._on_duplicate_shortcut())
        self.bind("<Command-d>", lambda e: self._on_duplicate_shortcut())

    # -------------------------------------------------------------------------
    # Event Handlers & Data Binding
    # -------------------------------------------------------------------------

    def _on_csv_loaded(self, data: CSVData) -> None:
        """Triggered when user successfully loads a CSV file."""
        self.csv_data = data
        self.current_record_index = 0
        first_rec = data.get_record(0)

        # Update field inspector dropdown with real columns
        self.field_panel.set_csv_columns(data.columns)

        # Update CSV Placeholders Panel with detected columns and first record values
        self.placeholder_panel.set_columns(data.columns, first_rec)

        # Synchronize existing layout fields against newly uploaded CSV columns
        if self.layout_manager.fields:
            valid_fields, missing_fields = self.layout_manager.synchronize_with_csv(data.columns)
            if missing_fields:
                msg = (
                    f"CSV reloaded with {len(data.columns)} columns.\n\n"
                    f"The following {len(missing_fields)} field(s) reference columns absent from the new CSV:\n"
                    + "\n".join(f"• {m}" for m in missing_fields[:8])
                    + ("\n• ..." if len(missing_fields) > 8 else "")
                    + "\n\nWould you like to keep these fields for manual editing?\n"
                    "(Select 'No' to remove the unmapped fields from the certificate layout)"
                )
                keep = messagebox.askyesno("CSV Field Mapping Warning", msg)
                if not keep:
                    # Remove missing fields
                    valid_names = set(valid_fields)
                    to_remove = [f.id for f in self.layout_manager.fields if f.name not in valid_names]
                    for fid in to_remove:
                        self.layout_manager.delete_field(fid)

        # Update preview record
        self.canvas_editor.set_record(first_rec)

        self._update_record_switcher_ui()
        self.field_panel.refresh_field_list()
        self.canvas_editor.refresh()
        col_summary = ", ".join(data.columns)
        self.lbl_status.configure(
            text=f"CSV loaded: {data.filename} ({data.row_count} records) | Columns: {col_summary}"
        )

    def _on_template_loaded(self, tpl: TemplateData) -> None:
        """Triggered when user loads a certificate template (image or PDF)."""
        self.template_data = tpl
        self.canvas_editor.set_template(
            tpl.image,
            dims_text=f"{tpl.width} × {tpl.height} px ({tpl.orientation})",
        )
        self.lbl_status.configure(text=f"Template loaded: {tpl.filename} ({tpl.width}x{tpl.height} px).")

    def _on_field_panel_changed(self) -> None:
        """Triggered when attributes are edited in the right sidebar."""
        self.canvas_editor.refresh()

    def _on_canvas_field_selected(self, field_obj: Optional[Any]) -> None:
        """Triggered when a field is clicked or deselected on the visual canvas."""
        self.field_panel.refresh_field_list()

    def _on_layout_manager_updated(self) -> None:
        """Triggered whenever fields are added, removed, reordered, or modified."""
        self.btn_undo.configure(state="normal" if self.layout_manager.can_undo() else "disabled")
        self.btn_redo.configure(state="normal" if self.layout_manager.can_redo() else "disabled")

    def _on_undo(self) -> None:
        if self.layout_manager.undo():
            self.field_panel.refresh_field_list()
            self.canvas_editor.refresh()

    def _on_redo(self) -> None:
        if self.layout_manager.redo():
            self.field_panel.refresh_field_list()
            self.canvas_editor.refresh()

    def _on_duplicate_shortcut(self) -> None:
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.duplicate_field(selected.id)
            self.field_panel.refresh_field_list()
            self.canvas_editor.refresh()

    def _on_reset_layout(self) -> None:
        if messagebox.askyesno("Reset Layout", "Are you sure you want to clear all certificate fields?"):
            self.layout_manager.reset_layout()
            self.field_panel.refresh_field_list()
            self.canvas_editor.refresh()

    def _refresh_all(self) -> None:
        self.field_panel.refresh_field_list()
        self.canvas_editor.refresh()

    # -------------------------------------------------------------------------
    # Record Switcher Navigation
    # -------------------------------------------------------------------------

    def _set_record_index(self, idx: int) -> None:
        if not self.csv_data or self.csv_data.row_count == 0:
            return

        clamped = max(0, min(self.csv_data.row_count - 1, idx))
        self.current_record_index = clamped
        record = self.csv_data.get_record(clamped)
        self.canvas_editor.set_record(record)
        self.placeholder_panel.update_record(record)
        self._update_record_switcher_ui()

    def _jump_to_last_record(self) -> None:
        if self.csv_data:
            self._set_record_index(self.csv_data.row_count - 1)

    def _update_record_switcher_ui(self) -> None:
        if not self.csv_data:
            self.lbl_record_info.configure(text="Preview: Sample Record")
            return

        rec = self.csv_data.get_record(self.current_record_index) or {}
        name = rec.get("Name") or rec.get("RollNumber") or ""
        desc = f"Record {self.current_record_index + 1} of {self.csv_data.row_count}"
        if name:
            desc = f"{desc}: {name}"

        self.lbl_record_info.configure(text=desc)

    # -------------------------------------------------------------------------
    # Validation & Generation Orchestration
    # -------------------------------------------------------------------------

    def _run_preflight_check(self) -> None:
        """Executes pre-flight audit and shows modal."""
        report = PreFlightValidator.validate_all(
            csv_data=self.csv_data,
            template_data=self.template_data,
            fields=self.layout_manager.fields,
            output_dir=self.sidebar.get_output_dir(),
            filename_pattern=self.sidebar.get_filename_pattern(),
        )

        ValidationDialog(
            master=self,
            report=report,
            on_proceed=self._prompt_and_generate if report.is_valid else None,
        )

    def _prompt_and_generate(self) -> None:
        """Validates prerequisites, prompts confirmation summary, and launches batch."""
        # 1. Run Pre-flight validation
        report = PreFlightValidator.validate_all(
            csv_data=self.csv_data,
            template_data=self.template_data,
            fields=self.layout_manager.fields,
            output_dir=self.sidebar.get_output_dir(),
            filename_pattern=self.sidebar.get_filename_pattern(),
        )

        if not report.is_valid:
            ValidationDialog(master=self, report=report, on_proceed=None)
            return

        # 2. Confirmation Summary
        assert self.csv_data is not None
        assert self.template_data is not None

        export_mode = self.sidebar.get_export_mode()
        output_dir = self.sidebar.get_output_dir()
        batch_name = self.sidebar.get_batch_name()
        count = self.csv_data.row_count

        summary_msg = (
            f"Confirm Bulk Certificate Generation:\n\n"
            f"• Total CSV Records: {count}\n"
            f"• Output Mode: {export_mode.upper()}\n"
            f"• Batch Name: {batch_name}\n"
            f"• Destination: {output_dir}\n"
            f"• Multi-page Combined PDF: {'Yes' if self.sidebar.get_include_combined_pdf() else 'No'}\n\n"
            f"Proceed with generation?"
        )

        if not messagebox.askyesno("Confirm Batch Generation", summary_msg):
            return

        # 3. Create Generation Options
        options = GenerationOptions(
            output_dir=output_dir,
            export_mode=export_mode,
            filename_pattern=self.sidebar.get_filename_pattern(),
            collision_policy=self.sidebar.get_collision_policy(),
            create_subfolder=self.sidebar.get_create_subfolder(),
            batch_name=batch_name,
            include_combined_pdf=self.sidebar.get_include_combined_pdf(),
            image_quality=95,
            target_dpi=300,
        )

        # 4. Open Real-Time Progress Modal
        self.current_progress_dialog = GenerationProgressDialog(
            master=self,
            total_records=count,
            on_cancel_requested=self.generation_service.request_cancellation,
        )

        # 5. Thread-safe Progress Callback
        def on_progress(p: GenerationProgress) -> None:
            # Schedule safely on main Tkinter UI thread
            self.after(0, lambda: self._handle_progress_update(p))

        def on_complete(results: list, combined_pdf: Optional[str], report_file: Optional[str]) -> None:
            self.after(0, lambda: self._handle_batch_complete(results, combined_pdf, report_file))

        self.lbl_status.configure(text=f"Generating {count} certificates...")

        # 6. Start Generation Service Worker Thread
        self.generation_service.start_batch_generation(
            template_image=self.template_data.image,
            fields=self.layout_manager.fields,
            records=self.csv_data.records,
            options=options,
            progress_callback=on_progress,
            completion_callback=on_complete,
            lines=self.layout_manager.lines,
        )

    def _handle_progress_update(self, progress: GenerationProgress) -> None:
        """Executes on main UI thread to update modal and status bar."""
        if self.current_progress_dialog and self.current_progress_dialog.winfo_exists():
            self.current_progress_dialog.update_progress(progress)
        self.lbl_status.configure(
            text=f"Batch Progress: {int(progress.percentage)}% ({progress.completed_count} completed, {progress.failed_count} failed)."
        )

    def _handle_batch_complete(
        self,
        results: list,
        combined_pdf: Optional[str],
        report_file: Optional[str],
    ) -> None:
        """Executes on main UI thread when batch processing concludes."""
        success_count = sum(1 for r in results if r.status == "SUCCESS")
        self.lbl_status.configure(
            text=f"Batch complete. {success_count} certificates generated successfully."
        )
