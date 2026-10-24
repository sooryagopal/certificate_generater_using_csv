"""
PDF & Image Export Service for AURELIA — Bulk Certificate Generator.
Generates print-ready individual PDF, PNG, and JPG certificates, and stitches
multiple certificates into a single consolidated multi-page PDF document.
Uses atomic writes to prevent corrupt or partial output files.
"""

from __future__ import annotations
import os
import io
from typing import List, Tuple
from PIL import Image
import pymupdf


class PDFServiceError(Exception):
    """Exception raised for export or PDF generation failures."""
    pass


class PDFService:
    """Handles raster and vector export conversions and multi-page compilation."""

    @classmethod
    def export_individual_pdf(
        cls,
        image: Image.Image,
        dest_path: str,
        dpi: int = 300,
    ) -> str:
        """
        Converts a rendered PIL Image into a high-fidelity PDF certificate.
        Uses atomic file replacement (.tmp -> final).
        """
        tmp_path = f"{dest_path}.tmp"
        try:
            # Calculate physical page dimensions in points (72 points = 1 inch)
            width_pts = (image.width / dpi) * 72.0
            height_pts = (image.height / dpi) * 72.0

            # Encode image to high-quality PNG bytes stream
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG", optimize=True)
            img_bytes = img_byte_arr.getvalue()

            # Create PDF using PyMuPDF
            doc = pymupdf.open()
            page = doc.new_page(width=width_pts, height=height_pts)
            page_rect = pymupdf.Rect(0, 0, width_pts, height_pts)
            page.insert_image(page_rect, stream=img_bytes)

            doc.save(tmp_path, deflate=True, garbage=3)
            doc.close()

            # Atomic rename
            os.replace(tmp_path, dest_path)
            return dest_path

        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise PDFServiceError(f"Failed to export PDF '{dest_path}': {str(e)}") from e

    @classmethod
    def export_image(
        cls,
        image: Image.Image,
        dest_path: str,
        fmt: str = "PNG",
        quality: int = 95,
    ) -> str:
        """
        Exports rendered certificate as PNG or JPG with atomic write.
        """
        tmp_path = f"{dest_path}.tmp"
        fmt_upper = fmt.upper()
        if fmt_upper not in ("PNG", "JPG", "JPEG"):
            fmt_upper = "PNG"

        try:
            target_image = image
            save_kwargs = {}

            if fmt_upper in ("JPG", "JPEG"):
                if target_image.mode != "RGB":
                    target_image = target_image.convert("RGB")
                save_kwargs = {"format": "JPEG", "quality": quality, "optimize": True}
            else:
                save_kwargs = {"format": "PNG", "optimize": True}

            target_image.save(tmp_path, **save_kwargs)
            os.replace(tmp_path, dest_path)
            return dest_path

        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise PDFServiceError(f"Failed to export {fmt} '{dest_path}': {str(e)}") from e

    @classmethod
    def combine_pdfs(
        cls,
        pdf_paths: List[str],
        combined_output_path: str,
    ) -> str:
        """
        Combines a list of individual PDF certificate paths into a single document.
        Does not create an empty combined PDF if pdf_paths is empty.
        """
        if not pdf_paths:
            raise PDFServiceError("Cannot create combined PDF: no input PDF files were provided.")

        valid_paths = [p for p in pdf_paths if os.path.exists(p) and os.path.getsize(p) > 0]
        if not valid_paths:
            raise PDFServiceError("Cannot create combined PDF: none of the generated PDF files exist on disk.")

        tmp_path = f"{combined_output_path}.tmp"
        try:
            combined_doc = pymupdf.open()
            for p in valid_paths:
                source_doc = pymupdf.open(p)
                combined_doc.insert_pdf(source_doc)
                source_doc.close()

            combined_doc.save(tmp_path, deflate=True, garbage=3)
            combined_doc.close()

            os.replace(tmp_path, combined_output_path)
            return combined_output_path

        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise PDFServiceError(f"Failed to build combined PDF: {str(e)}") from e
