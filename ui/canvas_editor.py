"""
Interactive Certificate Canvas Editor for AURELIA.
Provides mouse drag-and-drop field positioning, coordinate normalization,
interactive selection handles, alignment guidelines, zoom, pan, and keyboard shortcuts.
"""

from __future__ import annotations
import math
import tkinter as tk
from typing import Optional, Dict, Any, Callable, Tuple
import customtkinter as ctk
from PIL import Image, ImageTk

from ui.theme import AureliaTheme
from models.text_field import TextField
from core.layout_manager import LayoutManager
from core.renderer import Renderer


class CanvasEditor(ctk.CTkFrame):
    """Visual drag-and-drop workspace for positioning certificate fields."""

    def __init__(
        self,
        master: Any,
        layout_manager: LayoutManager,
        on_field_selected: Optional[Callable[[Optional[TextField]], None]] = None,
        **kwargs: Any,
    ):
        super().__init__(master, fg_color=AureliaTheme.BG_MAIN, corner_radius=0, **kwargs)

        self.layout_manager = layout_manager
        self.on_field_selected = on_field_selected
        self.renderer = Renderer()

        # Canvas State
        self.template_image: Optional[Image.Image] = None
        self.current_record: Optional[Dict[str, Any]] = None
        self.zoom_level: float = 1.0
        self.fit_to_screen: bool = True
        self.show_grid: bool = False
        self.snap_enabled: bool = True

        # Rendered Cache
        self._rendered_tk_img: Optional[ImageTk.PhotoImage] = None
        self._rendered_pil_img: Optional[Image.Image] = None
        self._canvas_img_id: Optional[int] = None

        # Coordinate transform parameters
        self._scale: float = 1.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._displayed_w: int = 0
        self._displayed_h: int = 0

        # Dragging state
        self._drag_field_id: Optional[str] = None
        self._drag_start_norm_x: float = 0.0
        self._drag_start_norm_y: float = 0.0
        self._mouse_down_canvas_x: float = 0.0
        self._mouse_down_canvas_y: float = 0.0
        self._is_dragging: bool = False

        # Snapping indicators
        self._active_guidelines: list = []

        self._build_ui()
        self._bind_events()

    def _build_ui(self) -> None:
        """Constructs canvas toolbar and underlying Tkinter drawing canvas."""
        # Top Canvas Toolbar (Zoom, Fit, Grid, Snap)
        self.toolbar = ctk.CTkFrame(self, fg_color=AureliaTheme.BG_PANEL, height=42, corner_radius=6)
        self.toolbar.pack(fill="x", padx=12, pady=(10, 6))

        # Zoom Controls
        self.btn_zoom_out = ctk.CTkButton(
            self.toolbar, text="−", width=32, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=14, weight="bold"),
            command=self.zoom_out,
        )
        self.btn_zoom_out.pack(side="left", padx=(8, 2), pady=6)

        self.lbl_zoom = ctk.CTkLabel(
            self.toolbar, text="100%", width=50,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=12),
        )
        self.lbl_zoom.pack(side="left", padx=2, pady=6)

        self.btn_zoom_in = ctk.CTkButton(
            self.toolbar, text="+", width=32, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=14, weight="bold"),
            command=self.zoom_in,
        )
        self.btn_zoom_in.pack(side="left", padx=(2, 8), pady=6)

        self.btn_fit = ctk.CTkButton(
            self.toolbar, text="Fit View", width=74, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=12),
            command=self.fit_view,
        )
        self.btn_fit.pack(side="left", padx=4, pady=6)

        self.btn_actual_size = ctk.CTkButton(
            self.toolbar, text="100%", width=54, height=28,
            fg_color=AureliaTheme.BG_PANEL_ALT, hover_color=AureliaTheme.BORDER,
            text_color=AureliaTheme.TEXT_MAIN, font=ctk.CTkFont(size=12),
            command=self.reset_zoom,
        )
        self.btn_actual_size.pack(side="left", padx=4, pady=6)

        # Separator
        sep = ctk.CTkFrame(self.toolbar, width=2, height=20, fg_color=AureliaTheme.BORDER)
        sep.pack(side="left", padx=10, pady=10)

        # Snapping Switch
        self.chk_snap = ctk.CTkCheckBox(
            self.toolbar, text="Snap to Center", width=120, height=24,
            checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, hover_color=AureliaTheme.GOLD_HOVER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=12),
            command=self._on_snap_toggled,
        )
        self.chk_snap.select()
        self.chk_snap.pack(side="left", padx=6, pady=6)

        # Grid Switch
        self.chk_grid = ctk.CTkCheckBox(
            self.toolbar, text="Alignment Grid", width=120, height=24,
            checkbox_width=18, checkbox_height=18,
            fg_color=AureliaTheme.GOLD_PRIMARY, hover_color=AureliaTheme.GOLD_HOVER,
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=12),
            command=self._on_grid_toggled,
        )
        self.chk_grid.pack(side="left", padx=6, pady=6)

        # Dimensions info badge on right
        self.lbl_dims = ctk.CTkLabel(
            self.toolbar, text="No Template Loaded",
            text_color=AureliaTheme.TEXT_MUTED, font=ctk.CTkFont(size=12),
        )
        self.lbl_dims.pack(side="right", padx=14, pady=6)

        # Main Canvas Area
        self.canvas_container = ctk.CTkFrame(self, fg_color=AureliaTheme.BG_MAIN, corner_radius=0)
        self.canvas_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.canvas = tk.Canvas(
            self.canvas_container,
            bg=AureliaTheme.BG_MAIN,
            bd=0,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)

    def _bind_events(self) -> None:
        """Attaches interactive mouse and keyboard handlers."""
        self.canvas.bind("<Configure>", self._on_canvas_resized)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)  # macOS / Win
        self.canvas.bind("<Button-4>", lambda e: self.zoom_in())   # Linux scroll up
        self.canvas.bind("<Button-5>", lambda e: self.zoom_out())  # Linux scroll down

        # Canvas Keyboard Focus & Navigation
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<Key-Left>", lambda e: self._nudge_selected(-0.002, 0.0))
        self.canvas.bind("<Key-Right>", lambda e: self._nudge_selected(0.002, 0.0))
        self.canvas.bind("<Key-Up>", lambda e: self._nudge_selected(0.0, -0.002))
        self.canvas.bind("<Key-Down>", lambda e: self._nudge_selected(0.0, 0.002))
        self.canvas.bind("<Shift-Key-Left>", lambda e: self._nudge_selected(-0.01, 0.0))
        self.canvas.bind("<Shift-Key-Right>", lambda e: self._nudge_selected(0.01, 0.0))
        self.canvas.bind("<Shift-Key-Up>", lambda e: self._nudge_selected(0.0, -0.01))
        self.canvas.bind("<Shift-Key-Down>", lambda e: self._nudge_selected(0.0, 0.01))
        self.canvas.bind("<Delete>", lambda e: self._delete_selected())
        self.canvas.bind("<BackSpace>", lambda e: self._delete_selected())

    # -------------------------------------------------------------------------
    # Public Update Interface
    # -------------------------------------------------------------------------

    def set_template(self, image: Optional[Image.Image], dims_text: str = "") -> None:
        """Sets the active template image and updates layout."""
        self.template_image = image
        if dims_text:
            self.lbl_dims.configure(text=dims_text)
        elif image:
            self.lbl_dims.configure(text=f"{image.width} × {image.height} px")
        else:
            self.lbl_dims.configure(text="No Template Loaded")

        self.fit_to_screen = True
        self.refresh()

    def set_record(self, record: Optional[Dict[str, Any]]) -> None:
        """Sets the active CSV participant record for live preview rendering."""
        self.current_record = record
        self.refresh()

    def refresh(self) -> None:
        """Re-renders canvas elements."""
        self._calculate_transforms()
        self._draw_canvas_content()

    # -------------------------------------------------------------------------
    # Coordinate Transforms & Layout Math
    # -------------------------------------------------------------------------

    def _calculate_transforms(self) -> None:
        """Computes scale factor, letterbox offsets, and dimensions."""
        if not self.template_image:
            return

        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())
        tw = self.template_image.width
        th = self.template_image.height

        if self.fit_to_screen:
            # Scale to fit window while preserving aspect ratio
            pad_w = cw - 40
            pad_h = ch - 40
            fit_scale = min(pad_w / tw, pad_h / th)
            self._scale = max(0.05, fit_scale)
            self.zoom_level = self._scale / (min(cw / tw, ch / th))
        else:
            base_fit = min(cw / tw, ch / th)
            self._scale = max(0.05, base_fit * self.zoom_level)

        self._displayed_w = int(tw * self._scale)
        self._displayed_h = int(th * self._scale)
        self._offset_x = (cw - self._displayed_w) / 2.0
        self._offset_y = (ch - self._displayed_h) / 2.0

        percent = int(self._scale / (min(cw / tw, ch / th) or 1.0) * 100)
        self.lbl_zoom.configure(text=f"{percent}%")

    def norm_to_canvas(self, norm_x: float, norm_y: float) -> Tuple[float, float]:
        """Converts normalized (0.0 to 1.0) template coordinates to canvas pixels."""
        cx = self._offset_x + norm_x * self._displayed_w
        cy = self._offset_y + norm_y * self._displayed_h
        return cx, cy

    def canvas_to_norm(self, cx: float, cy: float) -> Tuple[float, float]:
        """Converts canvas pixel coordinates to normalized (0.0 to 1.0) template values."""
        if self._displayed_w <= 0 or self._displayed_h <= 0:
            return 0.5, 0.5
        norm_x = (cx - self._offset_x) / self._displayed_w
        norm_y = (cy - self._offset_y) / self._displayed_h
        return max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y))

    def get_norm_from_screen(self, screen_x: int, screen_y: int) -> Optional[Tuple[float, float]]:
        """
        Tests if screen coordinates fall within the certificate canvas area.
        If yes, returns normalized (x, y) coordinates (0.0 to 1.0).
        Otherwise returns None.
        """
        try:
            cx_canvas = self.canvas.winfo_rootx()
            cy_canvas = self.canvas.winfo_rooty()
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()

            if not (cx_canvas <= screen_x <= cx_canvas + cw and cy_canvas <= screen_y <= cy_canvas + ch):
                return None

            cx = screen_x - cx_canvas
            cy = screen_y - cy_canvas
            return self.canvas_to_norm(cx, cy)
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Canvas Drawing
    # -------------------------------------------------------------------------

    def _draw_canvas_content(self) -> None:
        """Renders template, text overlays, grid, guidelines, and selection box."""
        self.canvas.delete("all")
        self._active_guidelines.clear()

        if not self.template_image:
            self._draw_empty_state()
            return

        # 1. Render certificate graphic with text overlays using core Renderer
        rendered = self.renderer.render_certificate(
            template_image=self.template_image,
            fields=self.layout_manager.fields,
            record=self.current_record,
            scale=self._scale,
        )
        self._rendered_pil_img = rendered
        self._rendered_tk_img = ImageTk.PhotoImage(rendered)

        # 2. Draw certificate image onto canvas
        self._canvas_img_id = self.canvas.create_image(
            self._offset_x, self._offset_y,
            anchor="nw",
            image=self._rendered_tk_img,
        )

        # Draw subtle template border shadow
        self.canvas.create_rectangle(
            self._offset_x, self._offset_y,
            self._offset_x + self._displayed_w,
            self._offset_y + self._displayed_h,
            outline=AureliaTheme.BORDER,
            width=1,
        )

        # 3. Draw grid if enabled
        if self.show_grid:
            self._draw_grid_overlay()

        # 4. Draw active guidelines (e.g. during dragging)
        for g in self._active_guidelines:
            self.canvas.create_line(g["coords"], fill=AureliaTheme.GOLD_PRIMARY, dash=(4, 4), width=1)

        # 5. Draw selection box for currently selected field
        selected = self.layout_manager.get_selected_field()
        if selected and selected.is_visible:
            self._draw_selection_box(selected)

    def _draw_empty_state(self) -> None:
        """Draws a clean, elegant placeholder message when no template is loaded."""
        cw = max(200, self.canvas.winfo_width())
        ch = max(200, self.canvas.winfo_height())
        cx, cy = cw / 2.0, ch / 2.0

        # Elegant dotted border placeholder
        card_w, card_h = min(cw - 80, 560), min(ch - 80, 280)
        self.canvas.create_rectangle(
            cx - card_w / 2, cy - card_h / 2,
            cx + card_w / 2, cy + card_h / 2,
            outline=AureliaTheme.BORDER,
            dash=(6, 6),
            width=1,
        )

        self.canvas.create_text(
            cx, cy - 25,
            text="AURELIA STUDIO WORKSPACE",
            fill=AureliaTheme.GOLD_PRIMARY,
            font=("Helvetica", 16, "bold"),
        )
        self.canvas.create_text(
            cx, cy + 12,
            text="Upload a CSV recipient file and Certificate Template on the left to begin.",
            fill=AureliaTheme.TEXT_MUTED,
            font=("Helvetica", 12),
        )

    def _draw_grid_overlay(self) -> None:
        """Draws subtle alignment grid lines across template area."""
        step_x = self._displayed_w / 10.0
        step_y = self._displayed_h / 10.0

        for i in range(1, 10):
            gx = self._offset_x + i * step_x
            self.canvas.create_line(gx, self._offset_y, gx, self._offset_y + self._displayed_h, fill="#1F1F24", width=1)

        for j in range(1, 10):
            gy = self._offset_y + j * step_y
            self.canvas.create_line(self._offset_x, gy, self._offset_x + self._displayed_w, gy, fill="#1F1F24", width=1)

    def _draw_selection_box(self, field_obj: TextField) -> None:
        """Draws crisp gold bounding box with 8 corner/edge handles around selected field."""
        if not self.template_image:
            return

        # Calculate bounding box in template pixels scaled to canvas
        bbox = self.renderer.calculate_field_bbox(
            field_obj=field_obj,
            template_width=self.template_image.width,
            template_height=self.template_image.height,
            record=self.current_record,
            scale=self._scale,
        )

        x0 = self._offset_x + bbox[0]
        y0 = self._offset_y + bbox[1]
        x1 = self._offset_x + bbox[2]
        y1 = self._offset_y + bbox[3]

        # Draw main gold bounding rectangle
        self.canvas.create_rectangle(
            x0 - 4, y0 - 4, x1 + 4, y1 + 4,
            outline=AureliaTheme.SELECTION_BOX,
            width=2,
            dash=(4, 2),
        )

        # Draw handles at 4 corners
        h_size = 3
        handle_coords = [
            (x0 - 4, y0 - 4),  # NW
            (x1 + 4, y0 - 4),  # NE
            (x0 - 4, y1 + 4),  # SW
            (x1 + 4, y1 + 4),  # SE
        ]
        for hx, hy in handle_coords:
            self.canvas.create_rectangle(
                hx - h_size, hy - h_size, hx + h_size, hy + h_size,
                fill=AureliaTheme.GOLD_PRIMARY,
                outline=AureliaTheme.BG_MAIN,
                width=1,
            )

        # Field tag badge above selection box
        badge_text = f" {field_obj.name} "
        self.canvas.create_text(
            (x0 + x1) / 2.0, y0 - 16,
            text=badge_text,
            fill=AureliaTheme.GOLD_PRIMARY,
            font=("Helvetica", 10, "bold"),
        )

    # -------------------------------------------------------------------------
    # Mouse Interaction & Dragging
    # -------------------------------------------------------------------------

    def _on_mouse_down(self, event: tk.Event) -> None:
        """Hit-test fields on click to initiate dragging or selection."""
        if not self.template_image:
            return

        cx, cy = event.x, event.y
        self._mouse_down_canvas_x = cx
        self._mouse_down_canvas_y = cy
        self._is_dragging = False

        # Hit test in reverse order (top layer first)
        hit_field = None
        for f in reversed(self.layout_manager.fields):
            if not f.is_visible:
                continue
            bbox = self.renderer.calculate_field_bbox(
                field_obj=f,
                template_width=self.template_image.width,
                template_height=self.template_image.height,
                record=self.current_record,
                scale=self._scale,
            )
            x0 = self._offset_x + bbox[0] - 6
            y0 = self._offset_y + bbox[1] - 6
            x1 = self._offset_x + bbox[2] + 6
            y1 = self._offset_y + bbox[3] + 6

            if x0 <= cx <= x1 and y0 <= cy <= y1:
                hit_field = f
                break

        if hit_field:
            self.layout_manager.select_field(hit_field.id)
            self._drag_field_id = hit_field.id
            self._drag_start_norm_x = hit_field.x
            self._drag_start_norm_y = hit_field.y
            if self.on_field_selected:
                self.on_field_selected(hit_field)
            self.canvas.config(cursor="fleur")
        else:
            self.layout_manager.select_field(None)
            self._drag_field_id = None
            if self.on_field_selected:
                self.on_field_selected(None)
            self.canvas.config(cursor="crosshair")

        self.refresh()

    def _on_mouse_drag(self, event: tk.Event) -> None:
        """Updates field position during drag with real-time snapping."""
        if not self._drag_field_id or not self.template_image:
            return

        field_obj = self.layout_manager.get_field(self._drag_field_id)
        if not field_obj:
            return

        self._is_dragging = True

        dx_canvas = event.x - self._mouse_down_canvas_x
        dy_canvas = event.y - self._mouse_down_canvas_y

        dx_norm = dx_canvas / max(1, self._displayed_w)
        dy_norm = dy_canvas / max(1, self._displayed_h)

        new_x = max(0.0, min(1.0, self._drag_start_norm_x + dx_norm))
        new_y = max(0.0, min(1.0, self._drag_start_norm_y + dy_norm))

        self._active_guidelines.clear()

        # Snapping to Center (0.50) and Margins
        if self.snap_enabled:
            snap_dist = 0.012  # Threshold in normalized space
            # Center X
            if abs(new_x - 0.50) < snap_dist:
                new_x = 0.50
                mid_x = self._offset_x + 0.50 * self._displayed_w
                self._active_guidelines.append({
                    "coords": (mid_x, self._offset_y, mid_x, self._offset_y + self._displayed_h)
                })
            # Center Y
            if abs(new_y - 0.50) < snap_dist:
                new_y = 0.50
                mid_y = self._offset_y + 0.50 * self._displayed_h
                self._active_guidelines.append({
                    "coords": (self._offset_x, mid_y, self._offset_x + self._displayed_w, mid_y)
                })

        # Apply position directly to object without snapshot on every pixel move
        field_obj.x = new_x
        field_obj.y = new_y

        self._draw_canvas_content()

    def _on_mouse_up(self, event: tk.Event) -> None:
        """Finalizes drag operation and commits undo history snapshot."""
        if self._is_dragging and self._drag_field_id:
            # Register change in layout manager for undo/redo
            field_obj = self.layout_manager.get_field(self._drag_field_id)
            if field_obj:
                self.layout_manager.update_field_property(
                    self._drag_field_id,
                    x=field_obj.x,
                    y=field_obj.y,
                )

        self._drag_field_id = None
        self._is_dragging = False
        self._active_guidelines.clear()
        self.canvas.config(cursor="crosshair")
        self.refresh()

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """Handles mouse wheel zoom if Ctrl or Cmd key is pressed."""
        if event.state & 0x4 or event.state & 0x8:  # Ctrl or Cmd
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def _on_canvas_resized(self, event: tk.Event) -> None:
        """Auto-recalculates canvas scale when window resizes."""
        if self.template_image:
            self.refresh()

    # -------------------------------------------------------------------------
    # Keyboard Nudge & Deletion
    # -------------------------------------------------------------------------

    def _nudge_selected(self, dx: float, dy: float) -> None:
        """Moves selected field incrementally via arrow keys."""
        selected = self.layout_manager.get_selected_field()
        if not selected:
            return
        new_x = max(0.0, min(1.0, selected.x + dx))
        new_y = max(0.0, min(1.0, selected.y + dy))
        self.layout_manager.update_field_property(selected.id, x=new_x, y=new_y)
        self.refresh()

    def _delete_selected(self) -> None:
        """Deletes selected field via Delete/Backspace key."""
        selected = self.layout_manager.get_selected_field()
        if selected:
            self.layout_manager.delete_field(selected.id)
            if self.on_field_selected:
                self.on_field_selected(None)
            self.refresh()

    # -------------------------------------------------------------------------
    # Toolbar Actions
    # -------------------------------------------------------------------------

    def zoom_in(self) -> None:
        self.fit_to_screen = False
        self.zoom_level = min(4.0, self.zoom_level * 1.15)
        self.refresh()

    def zoom_out(self) -> None:
        self.fit_to_screen = False
        self.zoom_level = max(0.15, self.zoom_level / 1.15)
        self.refresh()

    def fit_view(self) -> None:
        self.fit_to_screen = True
        self.zoom_level = 1.0
        self.refresh()

    def reset_zoom(self) -> None:
        self.fit_to_screen = False
        self.zoom_level = 1.0
        self.refresh()

    def _on_snap_toggled(self) -> None:
        self.snap_enabled = bool(self.chk_snap.get())

    def _on_grid_toggled(self) -> None:
        self.show_grid = bool(self.chk_grid.get())
        self.refresh()
