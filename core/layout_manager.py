"""
Layout Manager module for AURELIA — Bulk Certificate Generator.
Manages active certificate text fields, layer ordering, selection state,
and robust undo/redo history stacks.
"""

from __future__ import annotations
import copy
from typing import List, Optional, Dict, Any, Callable, Tuple, Union
from models.text_field import TextField
from models.strike_line import StrikeLine
from models.layout_preset import LayoutPreset


class LayoutManager:
    """State manager for active certificate fields and strike-through lines with undo/redo capabilities."""

    def __init__(self, max_history: int = 50) -> None:
        self.fields: List[TextField] = []
        self.lines: List[StrikeLine] = []
        self.selected_field_id: Optional[str] = None
        self.selected_line_id: Optional[str] = None
        self.selected_type: str = "field"  # "field" or "line"
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []
        self.max_history = max_history
        self._on_change_callbacks: List[Callable[[], None]] = []

    def register_callback(self, cb: Callable[[], None]) -> None:
        """Register listener invoked when layout changes."""
        self._on_change_callbacks.append(cb)

    def _notify_change(self) -> None:
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception:
                pass

    def _save_snapshot(self) -> None:
        """Saves current fields and lines state onto undo stack and clears redo stack."""
        snapshot = {
            "fields": [f.to_dict() for f in self.fields],
            "lines": [l.to_dict() for l in self.lines],
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        """Reverts the last layout action."""
        if not self.can_undo():
            return False

        # Current state goes to redo stack
        current_state = {
            "fields": [f.to_dict() for f in self.fields],
            "lines": [l.to_dict() for l in self.lines],
        }
        self._redo_stack.append(current_state)

        # Restore from undo stack
        prev_state = self._undo_stack.pop()
        if isinstance(prev_state, dict):
            self.fields = [TextField.from_dict(d) for d in prev_state.get("fields", [])]
            self.lines = [StrikeLine.from_dict(d) for d in prev_state.get("lines", [])]
        else:
            self.fields = [TextField.from_dict(d) for d in prev_state]
            self.lines = []

        # Ensure selected_field_id is still valid
        if self.selected_field_id and not self.get_field(self.selected_field_id):
            self.selected_field_id = self.fields[0].id if self.fields else None
        if self.selected_line_id and not self.get_line(self.selected_line_id):
            self.selected_line_id = self.lines[0].id if self.lines else None

        self._notify_change()
        return True

    def redo(self) -> bool:
        """Re-applies a previously undone layout action."""
        if not self.can_redo():
            return False

        current_state = {
            "fields": [f.to_dict() for f in self.fields],
            "lines": [l.to_dict() for l in self.lines],
        }
        self._undo_stack.append(current_state)

        next_state = self._redo_stack.pop()
        if isinstance(next_state, dict):
            self.fields = [TextField.from_dict(d) for d in next_state.get("fields", [])]
            self.lines = [StrikeLine.from_dict(d) for d in next_state.get("lines", [])]
        else:
            self.fields = [TextField.from_dict(d) for d in next_state]
            self.lines = []

        if self.selected_field_id and not self.get_field(self.selected_field_id):
            self.selected_field_id = self.fields[0].id if self.fields else None
        if self.selected_line_id and not self.get_line(self.selected_line_id):
            self.selected_line_id = self.lines[0].id if self.lines else None

        self._notify_change()
        return True

    def get_field(self, field_id: str) -> Optional[TextField]:
        """Lookup field by ID."""
        for f in self.fields:
            if f.id == field_id:
                return f
        return None

    def get_selected_field(self) -> Optional[TextField]:
        """Returns the currently selected field or None."""
        if not self.selected_field_id:
            return None
        return self.get_field(self.selected_field_id)

    def select_field(self, field_id: Optional[str]) -> None:
        """Sets the selected field ID and clears line selection."""
        self.selected_field_id = field_id
        if field_id is not None:
            self.selected_line_id = None
            self.selected_type = "field"
        elif self.selected_type == "field":
            self.selected_type = "none"
        self._notify_change()

    def clear_selection(self) -> None:
        """Deselects any active field or line."""
        self.selected_field_id = None
        self.selected_line_id = None
        self.selected_type = "none"
        self._notify_change()


    def add_field(
        self,
        name: str = "New Field",
        column_name: str = "",
        is_static: bool = False,
        static_text: str = "",
        x: float = 0.50,
        y: float = 0.50,
        font_size: int = 40,
        text_color: str = "#D4AF37",
    ) -> TextField:
        """Creates and appends a new text field."""
        self._save_snapshot()

        # Stagger slightly if fields already exist at 0.5, 0.5
        new_y = y
        if any(abs(f.y - y) < 0.03 for f in self.fields):
            new_y = min(0.9, y + 0.05 * len(self.fields))

        new_field = TextField(
            name=name,
            column_name=column_name,
            is_static=is_static,
            static_text=static_text,
            x=x,
            y=new_y,
            font_size=font_size,
            text_color=text_color,
            order=len(self.fields),
        )
        self.fields.append(new_field)
        self.selected_field_id = new_field.id
        self._notify_change()
        return new_field

    def delete_field(self, field_id: str) -> bool:
        """Removes the field with given ID."""
        target = self.get_field(field_id)
        if not target:
            return False

        self._save_snapshot()
        self.fields = [f for f in self.fields if f.id != field_id]

        if self.selected_field_id == field_id:
            self.selected_field_id = self.fields[0].id if self.fields else None

        self._reindex_order()
        self._notify_change()
        return True

    def duplicate_field(self, field_id: str) -> Optional[TextField]:
        """Duplicates a field with slightly offset coordinates."""
        source = self.get_field(field_id)
        if not source:
            return None

        self._save_snapshot()
        dup = source.copy()
        dup.order = len(self.fields)
        self.fields.append(dup)
        self.selected_field_id = dup.id
        self._notify_change()
        return dup

    def move_field_order(self, field_id: str, direction: int) -> bool:
        """
        Reorders field layer.
        direction: -1 for move up (higher index), +1 for move down (lower index)
        """
        for i, f in enumerate(self.fields):
            if f.id == field_id:
                new_idx = i + direction
                if 0 <= new_idx < len(self.fields):
                    self._save_snapshot()
                    self.fields[i], self.fields[new_idx] = self.fields[new_idx], self.fields[i]
                    self._reindex_order()
                    self._notify_change()
                    return True
                break
        return False

    def _reindex_order(self) -> None:
        """Re-assigns sequential order numbers to all fields."""
        for i, f in enumerate(self.fields):
            f.order = i

    def update_field_property(self, field_id: str, **kwargs: Any) -> bool:
        """Updates specific attributes of a field, recording undo snapshot."""
        target = self.get_field(field_id)
        if not target:
            return False

        self._save_snapshot()
        for k, v in kwargs.items():
            if hasattr(target, k):
                setattr(target, k, v)

        self._notify_change()
        return True

    def reset_field_position(self, field_id: str) -> bool:
        """Centers field back to (0.50, 0.50)."""
        return self.update_field_property(field_id, x=0.50, y=0.50)

    def reset_layout(self) -> None:
        """Clears all fields and lines."""
        if self.fields or self.lines:
            self._save_snapshot()
            self.fields.clear()
            self.lines.clear()
            self.selected_field_id = None
            self.selected_line_id = None
            self.selected_type = "none"
            self._notify_change()

    def load_preset(self, preset: LayoutPreset) -> None:
        """Replaces current layout with preset fields and lines."""
        self._save_snapshot()
        self.fields = [f.copy() for f in preset.fields]
        self.lines = [l.copy() for l in getattr(preset, "lines", [])]
        self._reindex_order()
        self._reindex_line_order()
        self.selected_field_id = self.fields[0].id if self.fields else None
        self.selected_line_id = None
        self.selected_type = "field" if self.fields else ("line" if self.lines else "none")
        self._notify_change()

    def export_to_preset(
        self,
        name: str,
        template_w: int = 1920,
        template_h: int = 1080,
        template_name: Optional[str] = None,
        description: str = "",
    ) -> LayoutPreset:
        """Generates a LayoutPreset from current fields and lines."""
        return LayoutPreset(
            name=name,
            version="2.0",
            description=description,
            template_width=template_w,
            template_height=template_h,
            template_name=template_name,
            fields=[f.copy() for f in self.fields],
            lines=[l.copy() for l in self.lines],
        )

    # -------------------------------------------------------------------------
    # STRIKE-THROUGH LINE OPERATIONS
    # -------------------------------------------------------------------------

    def get_line(self, line_id: str) -> Optional[StrikeLine]:
        """Lookup strike-through line by ID."""
        for line in self.lines:
            if line.id == line_id:
                return line
        return None

    def get_selected_line(self) -> Optional[StrikeLine]:
        """Returns the currently selected strike-through line or None."""
        if not self.selected_line_id:
            return None
        return self.get_line(self.selected_line_id)

    def select_line(self, line_id: Optional[str]) -> None:
        """Sets the selected line ID and clears field selection."""
        self.selected_line_id = line_id
        if line_id is not None:
            self.selected_field_id = None
            self.selected_type = "line"
        elif self.selected_type == "line":
            self.selected_type = "none"
        self._notify_change()

    def add_strike_line(
        self,
        name: str = "Strike Line",
        x: float = 0.50,
        y: float = 0.50,
        length: float = 0.15,
        thickness: int = 3,
        color: str = "#000000",
    ) -> StrikeLine:
        """Creates and appends a new manual strike-through line."""
        self._save_snapshot()

        # Generate a friendly incremental name if default
        line_idx = len(self.lines) + 1
        line_name = f"{name} {line_idx}" if name == "Strike Line" else name

        new_line = StrikeLine(
            name=line_name,
            x=x,
            y=y,
            length=length,
            thickness=thickness,
            color=color,
            order=len(self.lines),
        )
        self.lines.append(new_line)
        self.selected_line_id = new_line.id
        self.selected_field_id = None
        self.selected_type = "line"
        self._notify_change()
        return new_line

    def delete_line(self, line_id: str) -> bool:
        """Removes the strike line with given ID."""
        target = self.get_line(line_id)
        if not target:
            return False

        self._save_snapshot()
        self.lines = [l for l in self.lines if l.id != line_id]

        if self.selected_line_id == line_id:
            self.selected_line_id = self.lines[0].id if self.lines else None
            if not self.selected_line_id:
                self.selected_type = "field" if self.fields else "none"

        self._reindex_line_order()
        self._notify_change()
        return True

    def duplicate_line(self, line_id: str) -> Optional[StrikeLine]:
        """Duplicates a line with slightly offset coordinates."""
        source = self.get_line(line_id)
        if not source:
            return None

        self._save_snapshot()
        dup = source.copy()
        dup.y = min(0.95, dup.y + 0.02)
        dup.order = len(self.lines)
        self.lines.append(dup)
        self.selected_line_id = dup.id
        self.selected_field_id = None
        self.selected_type = "line"
        self._notify_change()
        return dup

    def update_line_property(self, line_id: str, **kwargs: Any) -> bool:
        """Updates specific attributes of a strike line, recording undo snapshot."""
        target = self.get_line(line_id)
        if not target:
            return False

        self._save_snapshot()
        for k, v in kwargs.items():
            if hasattr(target, k):
                setattr(target, k, v)

        self._notify_change()
        return True

    def _reindex_line_order(self) -> None:
        """Re-assigns sequential order numbers to all lines."""
        for i, l in enumerate(self.lines):
            l.order = i


    def add_placeholder_field(
        self,
        column_name: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        font_size: Optional[int] = None,
        text_color: Optional[str] = None,
        bold: Optional[bool] = None,
    ) -> TextField:
        """Creates and appends a dynamic text field tied to a CSV column placeholder."""
        self._save_snapshot()

        if x is None:
            x = 0.50
        if y is None:
            # Stagger vertically from previously selected or last field
            selected = self.get_selected_field()
            if selected:
                y = min(0.92, selected.y + 0.06)
            elif self.fields:
                y = min(0.92, self.fields[-1].y + 0.06)
            else:
                y = 0.45

        # Format initial style based on column semantics
        col_lower = column_name.lower()
        if font_size is None:
            if any(k in col_lower for k in ("name", "student", "recipient")):
                font_size = 52
            elif any(k in col_lower for k in ("event", "title", "course", "award", "prize")):
                font_size = 38
            elif any(k in col_lower for k in ("roll", "id", "reg", "code", "cert")):
                font_size = 26
            else:
                font_size = 36

        if bold is None:
            bold = any(k in col_lower for k in ("name", "student", "recipient", "event", "title", "course", "award", "prize"))

        if text_color is None:
            if any(k in col_lower for k in ("name", "student", "recipient", "roll", "id", "reg", "code", "cert")):
                text_color = "#D4AF37"
            else:
                text_color = "#F5F1E5"

        new_field = TextField(
            name=column_name,
            column_name=column_name,
            placeholder=f"{{{{{column_name}}}}}",
            is_static=False,
            x=x,
            y=y,
            font_size=font_size,
            text_color=text_color,
            bold=bold,
            order=len(self.fields),
        )
        self.fields.append(new_field)
        self.selected_field_id = new_field.id
        self._notify_change()
        return new_field

    def insert_all_columns(self, columns: List[str]) -> List[TextField]:
        """Arranges dynamic placeholders for all detected columns in a sensible vertical layout."""
        if not columns:
            return []

        self._save_snapshot()
        self.fields.clear()

        total = len(columns)
        start_y = 0.30
        end_y = 0.78
        step_y = (end_y - start_y) / max(1, total - 1) if total > 1 else 0.0

        created_fields = []
        for idx, col in enumerate(columns):
            col_lower = col.lower()
            y_pos = start_y + idx * step_y if total > 1 else 0.45

            if any(k in col_lower for k in ("name", "student", "participant", "recipient")):
                font_sz = 52
                color = "#D4AF37"
                bold = True
                casing = "none"
            elif any(k in col_lower for k in ("event", "title", "course", "award", "prize")):
                font_sz = 36
                color = "#F5F1E5"
                bold = True
                casing = "uppercase"
            elif any(k in col_lower for k in ("roll", "id", "reg", "code", "cert")):
                font_sz = 26
                color = "#D4AF37"
                bold = False
                casing = "none"
            elif any(k in col_lower for k in ("dept", "department", "class", "branch", "college")):
                font_sz = 26
                color = "#A6A29A"
                bold = False
                casing = "none"
            else:
                font_sz = 26
                color = "#F5F1E5"
                bold = False
                casing = "none"

            f = TextField(
                name=col,
                column_name=col,
                placeholder=f"{{{{{col}}}}}",
                is_static=False,
                x=0.50,
                y=y_pos,
                font_size=font_sz,
                text_color=color,
                bold=bold,
                transform_case=casing,
                order=idx,
            )
            self.fields.append(f)
            created_fields.append(f)

        self.selected_field_id = self.fields[0].id if self.fields else None
        self._notify_change()
        return created_fields

    def synchronize_with_csv(self, new_columns: List[str]) -> Tuple[List[str], List[str]]:
        """
        Synchronizes existing fields against new CSV columns.
        Returns:
            (valid_mapped_fields, missing_column_fields)
        """
        avail_lower = {c.strip().lower(): c for c in new_columns}
        valid = []
        missing = []

        from core.placeholder_engine import PlaceholderEngine

        for f in self.fields:
            if f.is_static:
                unresolved = PlaceholderEngine.find_unresolved(f.static_text, set(new_columns))
                if unresolved:
                    missing.append(f"{f.name} (unresolved {', '.join(unresolved)})")
                else:
                    valid.append(f.name)
            else:
                if f.template_text and "{{" in f.template_text:
                    unresolved = PlaceholderEngine.find_unresolved(f.template_text, set(new_columns))
                    if unresolved:
                        missing.append(f"{f.name} (unresolved {', '.join(unresolved)})")
                    else:
                        valid.append(f.name)
                elif f.column_name:
                    col_key = f.column_name.strip().lower()
                    if col_key in avail_lower:
                        f.column_name = avail_lower[col_key]
                        f.placeholder = f"{{{{{f.column_name}}}}}"
                        valid.append(f.name)
                    else:
                        missing.append(f"{f.name} (missing '{f.column_name}')")
                else:
                    missing.append(f"{f.name} (unmapped)")

        self._notify_change()
        return valid, missing
