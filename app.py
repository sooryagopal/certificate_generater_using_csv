#!/usr/bin/env python3
"""
AURELIA — Bulk Certificate Generator
Main Application Entry Point.
"""

from __future__ import annotations
import sys
import os
import traceback
import tkinter.messagebox as mb

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.main_window import MainWindow


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Logs uncaught exceptions and displays a user-friendly error dialog."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    sys.stderr.write(f"Unhandled Exception:\n{err_msg}\n")

    try:
        mb.showerror(
            "AURELIA — Unexpected Error",
            f"An unexpected error occurred:\n\n{str(exc_value)}\n\nPlease see logs for details.",
        )
    except Exception:
        pass


def main() -> None:
    """Initializes and runs the AURELIA Certificate Studio."""
    # Register global exception hook
    sys.excepthook = handle_uncaught_exception

    # Enforce Python 3.9+ (prompt mentions 3.11+ or newer)
    if sys.version_info < (3, 9):
        print("ERROR: AURELIA requires Python 3.9 or newer.", file=sys.stderr)
        sys.exit(1)

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
