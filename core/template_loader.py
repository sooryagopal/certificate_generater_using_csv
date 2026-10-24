"""
Template Loader module for AURELIA — Bulk Certificate Generator.
Loads and analyzes certificate templates in PNG, JPG, JPEG, WEBP, and PDF formats.
Converts PDF pages to high-resolution raster images at 300 DPI, preserving
original aspect ratios and never modifying the source file.
"""

from __future__ import annotations
import os
from typing import Optional, List, Tuple
from PIL import Image
import pymupdf


class TemplateError(Exception):
    """Custom exception for template loading failures."""
    pass


class TemplateData:
    """Encapsulates a loaded certificate template and its physical metadata."""
    def __init__(
        self,
        filepath: str,
        image: Image.Image,
        page_index: int = 0,
        total_pages: int = 1,
        is_pdf: bool = False,
        warnings: Optional[List[str]] = None,
    ):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.image = image
        self.width, self.height = image.size
        self.aspect_ratio = self.width / max(1, self.height)
        self.orientation = "Landscape" if self.width >= self.height else "Portrait"
        self.page_index = page_index
        self.total_pages = total_pages
        self.is_pdf = is_pdf
        self.warnings = warnings or []

        # Resolution quality assessment
        # Recommended print resolution is at least 1800 x 1200 (~150 DPI for A4)
        # Optimal print resolution is 3508 x 2480 (300 DPI for A4)
        self.is_low_resolution = self.width < 1500 or self.height < 1000
        if self.is_low_resolution:
            self.warnings.append(
                f"Low resolution template detected ({self.width}x{self.height}). "
                "For high-quality printing, at least 1920x1080 or 300 DPI is recommended."
            )

    def get_thumbnail(self, max_size: Tuple[int, int] = (1200, 800)) -> Image.Image:
        """Generate a high-quality resized thumbnail for display on canvas."""
        thumb = self.image.copy()
        thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
        return thumb


class TemplateLoader:
    """Factory and loader for certificate graphic templates."""
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}

    @classmethod
    def load_template(cls, filepath: str, page_index: int = 0, dpi: int = 300) -> TemplateData:
        """
        Loads a template from the given filepath.
        For PDFs, renders the specified page at target DPI (default 300).
        """
        if not os.path.exists(filepath):
            raise TemplateError(f"Template file not found: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise TemplateError(
                f"Unsupported template format '{ext}'. Supported formats: {', '.join(sorted(cls.SUPPORTED_EXTENSIONS))}"
            )

        warnings: List[str] = []

        try:
            if ext == ".pdf":
                return cls._load_pdf(filepath, page_index=page_index, dpi=dpi, warnings=warnings)
            else:
                return cls._load_image(filepath, warnings=warnings)
        except TemplateError:
            raise
        except Exception as e:
            raise TemplateError(f"Failed to load certificate template: {str(e)}") from e

    @classmethod
    def _load_image(cls, filepath: str, warnings: List[str]) -> TemplateData:
        """Loads raster image template using Pillow."""
        try:
            with Image.open(filepath) as img:
                # Load pixel data completely into memory so original file handle is released
                img.load()
                # Convert palette/transparency to RGB with white background
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    converted = Image.new("RGB", img.size, (255, 255, 255))
                    alpha_img = img.convert("RGBA")
                    converted.paste(alpha_img, mask=alpha_img.split()[3])
                    final_img = converted
                else:
                    final_img = img.convert("RGB")

            return TemplateData(
                filepath=filepath,
                image=final_img,
                page_index=0,
                total_pages=1,
                is_pdf=False,
                warnings=warnings,
            )
        except Exception as e:
            raise TemplateError(f"Error opening image file: {str(e)}")

    @classmethod
    def _load_pdf(cls, filepath: str, page_index: int, dpi: int, warnings: List[str]) -> TemplateData:
        """Loads and renders a single page of a PDF document at high resolution."""
        try:
            doc = pymupdf.open(filepath)
            total_pages = len(doc)
            if total_pages == 0:
                doc.close()
                raise TemplateError("The PDF template file contains no pages.")

            if page_index < 0 or page_index >= total_pages:
                warnings.append(
                    f"Requested page {page_index + 1} exceeds total pages ({total_pages}). Falling back to page 1."
                )
                page_index = 0

            page = doc.load_page(page_index)
            # 72 points per inch in PDF coordinates -> scale factor for target DPI
            zoom = dpi / 72.0
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)

            # Convert PyMuPDF Pixmap to PIL Image
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            doc.close()

            return TemplateData(
                filepath=filepath,
                image=img,
                page_index=page_index,
                total_pages=total_pages,
                is_pdf=True,
                warnings=warnings,
            )
        except Exception as e:
            raise TemplateError(f"Error reading PDF template: {str(e)}")
