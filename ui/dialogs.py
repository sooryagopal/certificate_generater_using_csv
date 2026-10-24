"""
Modal Dialogs and Windows for AURELIA — Bulk Certificate Generator.
Includes CSV Data Table Preview, Pre-Flight Validation Audit modal,
Real-time Generation Progress modal, and Preset/Settings dialogs.
"""

from __future__ import annotations
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable
import customtkinter as ctk

from ui.theme import AureliaTheme
from core.validators import ValidationReport
from services.generation_service import GenerationProgress


class CSVPreviewDialog(ctk.CTkToplevel):
    """Table viewer for inspected CSV records and columns."""

    def __init__(self, master: Any, columns: List[str], records: List[Dict[str, str]]):
        super().__init__(master)
        self.title("AURELIA — CSV Data Table Preview")
        self.geometry("900x520")
        self.configure(fg_color=AureliaTheme.BG_PANEL)
        self.transient(master)
        self.grab_set()

        # Header Info
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(16, 8))

        lbl_title = ctk.CTkLabel(
            top_bar,
            text=f"CSV RECIPIENT DATA ({len(records)} Records, {len(columns)} Columns)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        lbl_title.pack(side="left")

        # Table Frame using standard themed ttk.Treeview for multi-column scrolling
        table_frame = ctk.CTkFrame(self, fg_color=AureliaTheme.BG_PANEL_ALT, corner_radius=6)
        table_frame.pack(fill="both", expand=True, padx=16, pady=8)

        # Style Treeview for Dark Mode
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=AureliaTheme.BG_INPUT,
            foreground=AureliaTheme.TEXT_MAIN,
            fieldbackground=AureliaTheme.BG_INPUT,
            rowheight=26,
            font=("Helvetica", 11),
        )
        style.configure(
            "Treeview.Heading",
            background=AureliaTheme.BG_PANEL_ALT,
            foreground=AureliaTheme.GOLD_PRIMARY,
            font=("Helvetica", 11, "bold"),
        )
        style.map("Treeview", background=[("selected", AureliaTheme.GOLD_MUTED)])

        scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")

        tree_cols = ["#Row"] + columns
        self.tree = ttk.Treeview(
            table_frame,
            columns=tree_cols,
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # Set Headings and column widths
        self.tree.heading("#Row", text="Row #")
        self.tree.column("#Row", width=60, anchor="center")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=140, anchor="w")

        # Insert up to 500 rows for preview performance
        for i, r in enumerate(records[:500]):
            row_vals = [i + 1] + [r.get(c, "") for c in columns]
            self.tree.insert("", "end", values=row_vals)

        # Bottom Bar
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=16, pady=(6, 16))

        if len(records) > 500:
            ctk.CTkLabel(
                bottom_bar,
                text=f"Showing preview of first 500 of {len(records)} records.",
                text_color=AureliaTheme.TEXT_MUTED,
                font=ctk.CTkFont(size=11),
            ).pack(side="left")

        btn_close = ctk.CTkButton(
            bottom_bar, text="Close Preview", width=120, height=32,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=self.destroy,
        )
        btn_close.pack(side="right")


class ValidationDialog(ctk.CTkToplevel):
    """Pre-flight check summary dialog highlighting blocking errors and warnings."""

    def __init__(
        self,
        master: Any,
        report: ValidationReport,
        on_proceed: Optional[Callable[[], None]] = None,
    ):
        super().__init__(master)
        self.title("AURELIA — Pre-Flight Validation Audit")
        self.geometry("640x500")
        self.configure(fg_color=AureliaTheme.BG_PANEL)
        self.transient(master)
        self.grab_set()

        self.report = report
        self.on_proceed = on_proceed

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 10))

        status_text = "READY FOR GENERATION" if self.report.is_valid else "VALIDATION ISSUES DETECTED"
        status_color = AureliaTheme.SUCCESS if self.report.is_valid else AureliaTheme.ERROR

        lbl_badge = ctk.CTkLabel(
            header,
            text=f"● {status_text}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=status_color,
        )
        lbl_badge.pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, fg_color=AureliaTheme.BG_PANEL_ALT, corner_radius=6)
        scroll.pack(fill="both", expand=True, padx=20, pady=6)

        # 1. Blocking Errors
        if self.report.errors:
            lbl_err_title = ctk.CTkLabel(
                scroll, text=f"BLOCKING ERRORS ({len(self.report.errors)})",
                text_color=AureliaTheme.ERROR, font=ctk.CTkFont(size=12, weight="bold"),
            )
            lbl_err_title.pack(anchor="w", pady=(6, 2))

            for err in self.report.errors:
                msg_box = ctk.CTkLabel(
                    scroll, text=f"✕  {err}",
                    text_color=AureliaTheme.ERROR, font=ctk.CTkFont(size=11),
                    justify="left", anchor="w", wraplength=560,
                )
                msg_box.pack(anchor="w", padx=12, pady=2)

        # 2. Warnings
        if self.report.warnings:
            lbl_warn_title = ctk.CTkLabel(
                scroll, text=f"ADVISORIES & WARNINGS ({len(self.report.warnings)})",
                text_color=AureliaTheme.WARNING, font=ctk.CTkFont(size=12, weight="bold"),
            )
            lbl_warn_title.pack(anchor="w", pady=(12, 2))

            for w in self.report.warnings:
                msg_box = ctk.CTkLabel(
                    scroll, text=f"▲  {w}",
                    text_color=AureliaTheme.WARNING, font=ctk.CTkFont(size=11),
                    justify="left", anchor="w", wraplength=560,
                )
                msg_box.pack(anchor="w", padx=12, pady=2)

        # 3. Problematic Rows
        if self.report.problematic_rows:
            lbl_rows_title = ctk.CTkLabel(
                scroll, text=f"AFFECTED ROWS ({len(self.report.problematic_rows)} Rows with empty mapped values)",
                text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=12, weight="bold"),
            )
            lbl_rows_title.pack(anchor="w", pady=(12, 2))

            # Display first 20 rows
            sample_rows = list(self.report.problematic_rows.items())[:20]
            for row_num, issues in sample_rows:
                lbl_row = ctk.CTkLabel(
                    scroll, text=f"Row {row_num}: {'; '.join(issues)}",
                    text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=10),
                    anchor="w",
                )
                lbl_row.pack(anchor="w", padx=14, pady=1)

            if len(self.report.problematic_rows) > 20:
                ctk.CTkLabel(
                    scroll,
                    text=f"...and {len(self.report.problematic_rows) - 20} more rows.",
                    text_color=AureliaTheme.TEXT_DISABLED, font=ctk.CTkFont(size=10),
                ).pack(anchor="w", padx=14, pady=2)

        if not self.report.errors and not self.report.warnings:
            ctk.CTkLabel(
                scroll,
                text="✓ All pre-flight checks passed successfully! CSV, template, field mappings, and destination directory are validated.",
                text_color=AureliaTheme.SUCCESS,
                font=ctk.CTkFont(size=12),
                wraplength=560,
            ).pack(anchor="w", padx=10, pady=16)

        # Bottom Buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(10, 16))

        btn_cancel = ctk.CTkButton(
            bottom, text="Close", width=100, height=32,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=self.destroy,
        )
        btn_cancel.pack(side="left")

        if self.report.is_valid and self.on_proceed:
            btn_proceed = ctk.CTkButton(
                bottom, text="Proceed to Generate", width=160, height=32,
                fg_color=AureliaTheme.GOLD_PRIMARY, hover_color=AureliaTheme.GOLD_HOVER,
                text_color="#000000", font=ctk.CTkFont(size=12, weight="bold"),
                command=self._proceed,
            )
            btn_proceed.pack(side="right")

    def _proceed(self) -> None:
        self.destroy()
        if self.on_proceed:
            self.on_proceed()


class GenerationProgressDialog(ctk.CTkToplevel):
    """Live progress modal displaying batch execution status, cancel button, and summary."""

    def __init__(
        self,
        master: Any,
        total_records: int,
        on_cancel_requested: Callable[[], None],
    ):
        super().__init__(master)
        self.title("AURELIA — Generating Certificates")
        self.geometry("560x360")
        self.configure(fg_color=AureliaTheme.BG_PANEL)
        self.transient(master)
        self.grab_set()

        self.total_records = total_records
        self.on_cancel_requested = on_cancel_requested
        self._is_cancelled = False
        self._combined_pdf_path: Optional[str] = None
        self._output_folder_path: Optional[str] = None

        self._build_ui()

    def _build_ui(self) -> None:
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=24, pady=20)

        # Header Title
        self.lbl_headline = ctk.CTkLabel(
            self.content_frame,
            text="PROCESSING BATCH...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        self.lbl_headline.pack(anchor="w", pady=(0, 4))

        # Current Participant indicator
        self.lbl_current = ctk.CTkLabel(
            self.content_frame,
            text="Initializing generation engine...",
            font=ctk.CTkFont(size=12),
            text_color=AureliaTheme.TEXT_MAIN,
            anchor="w",
        )
        self.lbl_current.pack(anchor="w", pady=(0, 10))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.content_frame,
            height=14,
            progress_color=AureliaTheme.GOLD_PRIMARY,
            fg_color=AureliaTheme.BG_INPUT,
        )
        self.progress_bar.pack(fill="x", pady=6)
        self.progress_bar.set(0.0)

        # Percentage & Count label
        self.lbl_stats = ctk.CTkLabel(
            self.content_frame,
            text=f"0 / {self.total_records} (0%)",
            font=ctk.CTkFont(size=11),
            text_color=AureliaTheme.TEXT_MUTED,
        )
        self.lbl_stats.pack(anchor="e", pady=(0, 14))

        # Counts Cards Frame
        cards_frame = ctk.CTkFrame(self.content_frame, fg_color=AureliaTheme.BG_PANEL_ALT, corner_radius=6)
        cards_frame.pack(fill="x", pady=4)

        for col_idx, (title, color) in enumerate([("Completed", AureliaTheme.SUCCESS), ("Skipped", AureliaTheme.WARNING), ("Failed", AureliaTheme.ERROR)]):
            card = ctk.CTkFrame(cards_frame, fg_color="transparent")
            card.grid(row=0, column=col_idx, padx=16, pady=12, sticky="nsew")
            cards_frame.grid_columnconfigure(col_idx, weight=1)

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10), text_color=AureliaTheme.TEXT_MUTED).pack()
            val_lbl = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=18, weight="bold"), text_color=color)
            val_lbl.pack()
            if title == "Completed":
                self.lbl_completed = val_lbl
            elif title == "Skipped":
                self.lbl_skipped = val_lbl
            else:
                self.lbl_failed = val_lbl

        # Action Buttons Area
        self.action_box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.action_box.pack(fill="x", pady=(18, 0))

        self.btn_cancel = ctk.CTkButton(
            self.action_box, text="Cancel Batch", width=120, height=32,
            fg_color=AureliaTheme.ERROR_MUTED, hover_color=AureliaTheme.ERROR,
            text_color=AureliaTheme.ERROR, font=ctk.CTkFont(size=11, weight="bold"),
            command=self._cancel,
        )
        self.btn_cancel.pack(side="right")

    def update_progress(self, progress: GenerationProgress) -> None:
        """Called thread-safely via root.after() to update widgets."""
        fraction = progress.percentage / 100.0
        self.progress_bar.set(fraction)

        self.lbl_current.configure(text=f"Generating: {progress.current_name}")
        self.lbl_stats.configure(
            text=f"{progress.completed_count + progress.skipped_count + progress.failed_count} / {progress.total_records} ({int(progress.percentage)}%)"
        )
        self.lbl_completed.configure(text=str(progress.completed_count))
        self.lbl_skipped.configure(text=str(progress.skipped_count))
        self.lbl_failed.configure(text=str(progress.failed_count))

        if progress.combined_pdf_path:
            self._combined_pdf_path = progress.combined_pdf_path
        if progress.report_path:
            self._output_folder_path = os.path.dirname(progress.report_path)

        if progress.is_finished:
            self._show_completion_state(progress)

    def _show_completion_state(self, progress: GenerationProgress) -> None:
        """Transitions modal into completion state with open folder actions."""
        self.progress_bar.set(1.0)
        status_text = "BATCH GENERATION COMPLETE" if not self._is_cancelled else "BATCH CANCELLED"
        self.lbl_headline.configure(
            text=status_text,
            text_color=AureliaTheme.GOLD_PRIMARY if not self._is_cancelled else AureliaTheme.WARNING,
        )
        elapsed_str = f"in {progress.elapsed_seconds:.1f}s" if progress.elapsed_seconds > 0 else ""
        self.lbl_current.configure(
            text=f"Successfully processed {progress.completed_count} certificates {elapsed_str}."
        )

        self.btn_cancel.pack_forget()

        # Action Buttons
        btn_close = ctk.CTkButton(
            self.action_box, text="Close", width=90, height=32,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, command=self.destroy,
        )
        btn_close.pack(side="left")

        if self._combined_pdf_path and os.path.exists(self._combined_pdf_path):
            btn_pdf = ctk.CTkButton(
                self.action_box, text="Open Combined PDF", width=150, height=32,
                fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
                text_color=AureliaTheme.TEXT_MAIN, command=self._open_combined_pdf,
            )
            btn_pdf.pack(side="right", padx=(6, 0))

        if self._output_folder_path and os.path.exists(self._output_folder_path):
            btn_folder = ctk.CTkButton(
                self.action_box, text="Open Output Folder", width=150, height=32,
                fg_color=AureliaTheme.GOLD_PRIMARY, hover_color=AureliaTheme.GOLD_HOVER,
                text_color="#000000", font=ctk.CTkFont(weight="bold"),
                command=self._open_output_folder,
            )
            btn_folder.pack(side="right")

    def _cancel(self) -> None:
        self._is_cancelled = True
        self.btn_cancel.configure(text="Cancelling...", state="disabled")
        self.on_cancel_requested()

    def _open_output_folder(self) -> None:
        if self._output_folder_path and os.path.exists(self._output_folder_path):
            open_path_in_os(self._output_folder_path)

    def _open_combined_pdf(self) -> None:
        if self._combined_pdf_path and os.path.exists(self._combined_pdf_path):
            open_path_in_os(self._combined_pdf_path)


def open_path_in_os(target_path: str) -> None:
    """Safely launches folder or file in the native operating system file manager."""
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", target_path], check=False)
        elif sys.platform == "win32":  # Windows
            os.startfile(target_path)  # type: ignore
        else:  # Linux / BSD
            subprocess.run(["xdg-open", target_path], check=False)
    except Exception:
        pass
