"""
CSV Placeholders Panel for AURELIA — Bulk Certificate Generator.
Dedicated collapsible panel displaying every detected CSV column header as an available
dynamic certificate placeholder with search/filtering, live sample previews,
click-to-insert, drag-and-drop positioning, and copy-to-clipboard functionality.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from typing import Optional, List, Dict, Any, Callable
import customtkinter as ctk

from ui.theme import AureliaTheme
from core.layout_manager import LayoutManager
from core.placeholder_engine import PlaceholderEngine


class PlaceholderCard(ctk.CTkFrame):
    """Card widget representing an individual detected CSV column placeholder."""

    def __init__(
        self,
        master: Any,
        column_name: str,
        sample_value: str,
        on_insert: Callable[[str], None],
        on_copy: Callable[[str], None],
        on_start_drag: Callable[[str, Any], None],
        **kwargs: Any,
    ):
        super().__init__(
            master,
            fg_color=AureliaTheme.BG_PANEL_ALT,
            corner_radius=6,
            border_width=1,
            border_color=AureliaTheme.BORDER,
            **kwargs,
        )

        self.column_name = column_name
        self.placeholder = PlaceholderEngine.generate_placeholder(column_name)
        self.sample_value = sample_value
        self.on_insert = on_insert
        self.on_copy = on_copy
        self.on_start_drag = on_start_drag

        self._build_ui()

    def _build_ui(self) -> None:
        # Top row: Column Name + Placeholder Badge
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", padx=8, pady=(6, 2))

        # Drag handle / icon
        lbl_drag = ctk.CTkLabel(
            header_row,
            text="⠿",
            font=ctk.CTkFont(size=14),
            text_color=AureliaTheme.TEXT_MUTED,
            cursor="fleur",
            width=16,
        )
        lbl_drag.pack(side="left", padx=(0, 4))
        lbl_drag.bind("<ButtonPress-1>", lambda e: self.on_start_drag(self.column_name, e))

        lbl_col = ctk.CTkLabel(
            header_row,
            text=self.column_name,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=AureliaTheme.TEXT_MAIN,
            anchor="w",
        )
        lbl_col.pack(side="left", fill="x", expand=True)

        badge_ph = ctk.CTkLabel(
            header_row,
            text=self.placeholder,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
            fg_color=AureliaTheme.BG_INPUT,
            corner_radius=4,
            padx=6,
            pady=2,
            cursor="hand2",
        )
        badge_ph.pack(side="right")
        badge_ph.bind("<Button-1>", lambda e: self.on_copy(self.placeholder))

        # Middle row: Sample value from active record
        sample_row = ctk.CTkFrame(self, fg_color="transparent")
        sample_row.pack(fill="x", padx=8, pady=(2, 4))

        sample_display = self.sample_value if self.sample_value else "(empty)"
        self.lbl_sample = ctk.CTkLabel(
            sample_row,
            text=f"Sample: {sample_display}",
            font=ctk.CTkFont(size=10),
            text_color=AureliaTheme.TEXT_MUTED if self.sample_value else AureliaTheme.TEXT_DISABLED,
            anchor="w",
        )
        self.lbl_sample.pack(anchor="w")

        # Bottom row: Action Buttons
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=8, pady=(2, 6))

        btn_insert = ctk.CTkButton(
            action_row,
            text="+ Insert",
            height=24,
            width=65,
            fg_color=AureliaTheme.GOLD_PRIMARY,
            hover_color=AureliaTheme.GOLD_HOVER,
            text_color="#000000",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=lambda: self.on_insert(self.column_name),
        )
        btn_insert.pack(side="left", padx=(0, 4))

        btn_copy = ctk.CTkButton(
            action_row,
            text="📋 Copy",
            height=24,
            width=60,
            fg_color=AureliaTheme.BG_INPUT,
            hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN,
            font=ctk.CTkFont(size=10),
            command=lambda: self.on_copy(self.placeholder),
        )
        btn_copy.pack(side="left", padx=2)

        # Allow dragging from the card body as well
        self.bind("<ButtonPress-1>", lambda e: self.on_start_drag(self.column_name, e))

    def update_sample_value(self, new_val: str) -> None:
        """Refreshes the displayed preview sample value."""
        self.sample_value = new_val
        sample_display = new_val if new_val else "(empty)"
        self.lbl_sample.configure(
            text=f"Sample: {sample_display}",
            text_color=AureliaTheme.TEXT_MUTED if new_val else AureliaTheme.TEXT_DISABLED,
        )


class PlaceholderPanel(ctk.CTkFrame):
    """
    Dedicated collapsible side panel presenting all detected CSV columns as
    dynamic placeholders with search filtering and live sample values.
    """

    def __init__(
        self,
        master: Any,
        layout_manager: LayoutManager,
        on_field_created: Optional[Callable[[], None]] = None,
        get_canvas_drop_coords: Optional[Callable[[int, int], Optional[tuple[float, float]]]] = None,
        **kwargs: Any,
    ):
        super().__init__(master, fg_color=AureliaTheme.BG_PANEL, corner_radius=0, width=280, **kwargs)

        self.layout_manager = layout_manager
        self.on_field_created = on_field_created
        self.get_canvas_drop_coords = get_canvas_drop_coords

        self.columns: List[str] = []
        self.current_record: Dict[str, Any] = {}
        self.card_widgets: Dict[str, PlaceholderCard] = {}
        self.is_collapsed: bool = False

        # Drag & drop state
        self._dragging_column: Optional[str] = None
        self._drag_indicator: Optional[tk.Toplevel] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Builds header, search filter, action buttons, and scrollable placeholder cards."""
        # Main Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=(12, 6))

        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text="CSV PLACEHOLDERS",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=AureliaTheme.GOLD_PRIMARY,
        )
        self.lbl_title.pack(side="left")

        self.lbl_count = ctk.CTkLabel(
            self.header_frame,
            text="(0)",
            font=ctk.CTkFont(size=11),
            text_color=AureliaTheme.TEXT_MUTED,
        )
        self.lbl_count.pack(side="left", padx=(4, 0))

        # Collapse toggle button
        self.btn_toggle_collapse = ctk.CTkButton(
            self.header_frame,
            text="◀",
            width=24,
            height=24,
            fg_color=AureliaTheme.BG_PANEL_ALT,
            hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            command=self.toggle_collapse,
        )
        self.btn_toggle_collapse.pack(side="right")

        # Container for content when not collapsed
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True)

        # Search Bar
        search_box = ctk.CTkFrame(self.content_container, fg_color="transparent")
        search_box.pack(fill="x", padx=10, pady=(2, 6))

        self.entry_search = ctk.CTkEntry(
            search_box,
            placeholder_text="Search columns or {{placeholder}}...",
            height=28,
            fg_color=AureliaTheme.BG_INPUT,
            font=ctk.CTkFont(size=11),
        )
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.entry_search.bind("<KeyRelease>", lambda e: self._on_search_changed())

        self.btn_clear_search = ctk.CTkButton(
            search_box,
            text="✕",
            width=24,
            height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT,
            hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            command=self._clear_search,
        )
        self.btn_clear_search.pack(side="right")

        # Global Action Bar: Insert All Columns
        action_bar = ctk.CTkFrame(self.content_container, fg_color="transparent")
        action_bar.pack(fill="x", padx=10, pady=(0, 6))

        self.btn_insert_all = ctk.CTkButton(
            action_bar,
            text="⚡ Insert All Columns",
            height=26,
            fg_color=AureliaTheme.BG_PANEL_ALT,
            hover_color=AureliaTheme.BORDER_LIGHT,
            text_color=AureliaTheme.GOLD_PRIMARY,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_insert_all_columns,
        )
        self.btn_insert_all.pack(fill="x")

        # Feedback Toast Label (temporary notice when placeholder copied)
        self.lbl_toast = ctk.CTkLabel(
            self.content_container,
            text="",
            height=20,
            font=ctk.CTkFont(size=10),
            text_color=AureliaTheme.SUCCESS,
        )
        self.lbl_toast.pack(fill="x", padx=10, pady=(0, 2))

        # Scrollable Cards List
        self.cards_scroll = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        self.cards_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Empty State Notice
        self.lbl_empty_msg = ctk.CTkLabel(
            self.cards_scroll,
            text="Upload a CSV file to automatically detect columns and generate certificate placeholders.",
            font=ctk.CTkFont(size=11),
            text_color=AureliaTheme.TEXT_MUTED,
            wraplength=230,
            justify="center",
        )
        self.lbl_empty_msg.pack(fill="x", padx=10, pady=40)

        # Collapsed state vertical bar (hidden initially)
        self.collapsed_bar = ctk.CTkFrame(self, fg_color="transparent", width=36)
        self.btn_expand = ctk.CTkButton(
            self.collapsed_bar,
            text="▶\n\nP\nL\nA\nC\nE\nH\nO\nL\nD\nE\nR\nS",
            width=32,
            fg_color=AureliaTheme.BG_PANEL_ALT,
            hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.GOLD_PRIMARY,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self.toggle_collapse,
        )
        self.btn_expand.pack(fill="both", expand=True, padx=2, pady=8)

    # -------------------------------------------------------------------------
    # Public Update Interface
    # -------------------------------------------------------------------------

    def set_columns(self, columns: List[str], current_record: Optional[Dict[str, Any]] = None) -> None:
        """
        Receives newly detected columns from CSV and reconstructs placeholder cards.
        Supports 5, 20, 50, or 100+ columns without arbitrary truncation.
        """
        self.columns = list(columns)
        self.current_record = current_record or {}
        self.lbl_count.configure(text=f"({len(self.columns)})")

        # Auto-expand if collapsed and columns are loaded
        if self.is_collapsed and self.columns:
            self.toggle_collapse()

        self._render_cards()

    def update_record(self, record: Optional[Dict[str, Any]]) -> None:
        """
        Refreshes live preview sample values across all cards when the active CSV record changes.
        """
        self.current_record = record or {}
        for col, card in self.card_widgets.items():
            val = self.current_record.get(col, "")
            card.update_sample_value("" if val is None else str(val))

    def toggle_collapse(self) -> None:
        """Toggles between expanded panel and compact vertical tab."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content_container.pack_forget()
            self.header_frame.pack_forget()
            self.configure(width=38)
            self.collapsed_bar.pack(fill="both", expand=True)
        else:
            self.collapsed_bar.pack_forget()
            self.configure(width=280)
            self.header_frame.pack(fill="x", padx=10, pady=(12, 6))
            self.content_container.pack(fill="both", expand=True)

    # -------------------------------------------------------------------------
    # Rendering & Filtering
    # -------------------------------------------------------------------------

    def _render_cards(self, query: str = "") -> None:
        """Renders filtered cards for all detected columns."""
        # Clear existing card widgets
        for card in self.card_widgets.values():
            card.destroy()
        self.card_widgets.clear()

        if not self.columns:
            self.lbl_empty_msg.configure(
                text="Upload a CSV file to automatically detect columns and generate certificate placeholders."
            )
            self.lbl_empty_msg.pack(fill="x", padx=10, pady=40)
            self.btn_insert_all.configure(state="disabled")
            return

        self.btn_insert_all.configure(state="normal")
        query_clean = query.strip().lower()

        filtered_cols = []
        for col in self.columns:
            ph = PlaceholderEngine.generate_placeholder(col).lower()
            if not query_clean or query_clean in col.lower() or query_clean in ph:
                filtered_cols.append(col)

        if not filtered_cols:
            self.lbl_empty_msg.configure(text=f"No placeholders matching '{query}'.")
            self.lbl_empty_msg.pack(fill="x", padx=10, pady=30)
            return

        self.lbl_empty_msg.pack_forget()

        for col in filtered_cols:
            val = self.current_record.get(col, "")
            val_str = "" if val is None else str(val)
            card = PlaceholderCard(
                self.cards_scroll,
                column_name=col,
                sample_value=val_str,
                on_insert=self._on_insert_clicked,
                on_copy=self._on_copy_clicked,
                on_start_drag=self._on_start_drag,
            )
            card.pack(fill="x", padx=2, pady=3)
            self.card_widgets[col] = card

    def _on_search_changed(self) -> None:
        query = self.entry_search.get()
        self._render_cards(query=query)

    def _clear_search(self) -> None:
        self.entry_search.delete(0, "end")
        self._render_cards(query="")

    # -------------------------------------------------------------------------
    # Actions: Insert, Copy, Drag-and-Drop, Insert All
    # -------------------------------------------------------------------------

    def _on_insert_clicked(self, column_name: str) -> None:
        """
        Method A: Click to insert.
        Creates a new dynamic text field on the certificate canvas near center or offset.
        """
        self.layout_manager.add_placeholder_field(column_name=column_name)
        self._show_toast(f"Inserted {{{{{column_name}}}}} on certificate.")
        if self.on_field_created:
            self.on_field_created()

    def _on_copy_clicked(self, placeholder: str) -> None:
        """
        Method C: Copy placeholder to clipboard.
        """
        try:
            self.clipboard_clear()
            self.clipboard_append(placeholder)
            self.update()  # Required for clipboard on some X11/mac platforms
            self._show_toast(f"Copied {placeholder} to clipboard!")
        except Exception:
            self._show_toast(f"Copied {placeholder}")

    def _show_toast(self, message: str) -> None:
        """Displays temporary user feedback text."""
        self.lbl_toast.configure(text=message)
        # Schedule auto-clearing after 3.5 seconds
        self.after(3500, lambda: self._clear_toast(message))

    def _clear_toast(self, expected_msg: str) -> None:
        if self.lbl_toast.cget("text") == expected_msg:
            self.lbl_toast.configure(text="")

    def _on_insert_all_columns(self) -> None:
        """
        Inserts all detected columns with confirmation prompt to avoid accidental overcrowding.
        """
        if not self.columns:
            return

        count = len(self.columns)
        confirm = messagebox.askyesno(
            "Insert All Columns",
            f"Are you sure you want to insert all {count} detected CSV columns as text fields on the certificate?\n\n"
            "This will clear the current layout and arrange each column in a structured vertical template.",
        )
        if not confirm:
            return

        self.layout_manager.insert_all_columns(self.columns)
        self._show_toast(f"Created {count} certificate fields.")
        if self.on_field_created:
            self.on_field_created()

    # -------------------------------------------------------------------------
    # Method B: Drag and Drop Implementation
    # -------------------------------------------------------------------------

    def _on_start_drag(self, column_name: str, event: Any) -> None:
        """Initiates drag gesture for a placeholder."""
        self._dragging_column = column_name

        # Create lightweight floating tooltip indicator
        if self._drag_indicator:
            try:
                self._drag_indicator.destroy()
            except Exception:
                pass

        self._drag_indicator = tk.Toplevel(self)
        self._drag_indicator.overrideredirect(True)
        self._drag_indicator.attributes("-topmost", True)
        self._drag_indicator.configure(bg="#D4AF37")

        ph_text = PlaceholderEngine.generate_placeholder(column_name)
        lbl = tk.Label(
            self._drag_indicator,
            text=f" ⠿ {ph_text} ",
            bg="#D4AF37",
            fg="#000000",
            font=("Arial", 10, "bold"),
            padx=6,
            pady=3,
        )
        lbl.pack()

        # Position at pointer
        x = self.winfo_pointerx() + 12
        y = self.winfo_pointery() + 12
        self._drag_indicator.geometry(f"+{x}+{y}")

        # Bind motion and release globally to root window
        root = self.winfo_toplevel()
        root.bind("<B1-Motion>", self._on_drag_motion, add="+")
        root.bind("<ButtonRelease-1>", self._on_drag_release, add="+")

    def _on_drag_motion(self, event: Any) -> None:
        """Moves drag indicator with the mouse pointer."""
        if self._drag_indicator and self._drag_indicator.winfo_exists():
            x = self.winfo_pointerx() + 12
            y = self.winfo_pointery() + 12
            self._drag_indicator.geometry(f"+{x}+{y}")

    def _on_drag_release(self, event: Any) -> None:
        """Completes drop onto canvas if coordinates fall within canvas area."""
        root = self.winfo_toplevel()
        root.unbind("<B1-Motion>")
        root.unbind("<ButtonRelease-1>")

        col = self._dragging_column
        self._dragging_column = None

        if self._drag_indicator:
            try:
                self._drag_indicator.destroy()
            except Exception:
                pass
            self._drag_indicator = None

        if not col:
            return

        # Check if dropped onto certificate canvas
        if self.get_canvas_drop_coords:
            drop_coords = self.get_canvas_drop_coords(event.x_root, event.y_root)
            if drop_coords:
                norm_x, norm_y = drop_coords
                self.layout_manager.add_placeholder_field(column_name=col, x=norm_x, y=norm_y)
                self._show_toast(f"Dropped {{{{{col}}}}} at ({norm_x:.2f}, {norm_y:.2f}).")
                if self.on_field_created:
                    self.on_field_created()
                return

        # If dropped outside canvas, add at standard default position
        self.layout_manager.add_placeholder_field(column_name=col)
        self._show_toast(f"Inserted {{{{{col}}}}}")
        if self.on_field_created:
            self.on_field_created()
