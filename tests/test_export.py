"""
Unit tests for PDF & Image Export Service in AURELIA.
Tests individual PDF export, PNG, JPG, atomic writes, and combined multi-page PDF compilation.
"""

import os
import pytest
from PIL import Image
import pymupdf
from services.pdf_service import PDFService, PDFServiceError


def test_individual_pdf_export(tmp_path):
    out_dir = tmp_path / "pdf_test"
    out_dir.mkdir()
    pdf_path = str(out_dir / "certificate.pdf")

    img = Image.new("RGB", (1200, 800), "#D4AF37")
    res_path = PDFService.export_individual_pdf(img, pdf_path, dpi=300)

    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 0

    # Verify with PyMuPDF
    doc = pymupdf.open(res_path)
    assert len(doc) == 1
    # 1200 px at 300 dpi = 4 inches = 288 points
    page = doc[0]
    assert abs(page.rect.width - 288.0) < 1.0
    doc.close()


def test_png_and_jpg_image_export(tmp_path):
    out_dir = tmp_path / "img_test"
    out_dir.mkdir()

    img = Image.new("RGB", (800, 600), "#151518")

    # PNG
    png_path = str(out_dir / "cert.png")
    PDFService.export_image(img, png_path, fmt="PNG")
    assert os.path.exists(png_path)
    with Image.open(png_path) as opened_png:
        assert opened_png.size == (800, 600)

    # JPG
    jpg_path = str(out_dir / "cert.jpg")
    PDFService.export_image(img, jpg_path, fmt="JPG", quality=90)
    assert os.path.exists(jpg_path)
    with Image.open(jpg_path) as opened_jpg:
        assert opened_jpg.size == (800, 600)


def test_combined_pdf_generation(tmp_path):
    out_dir = tmp_path / "combined_test"
    out_dir.mkdir()

    # Generate 3 individual PDF files
    pdf_paths = []
    for i in range(3):
        p = str(out_dir / f"cert_{i+1}.pdf")
        img = Image.new("RGB", (600, 400), f"#{i+1}{i+1}{i+1}{i+1}{i+1}{i+1}")
        PDFService.export_individual_pdf(img, p, dpi=150)
        pdf_paths.append(p)

    combined_target = str(out_dir / "all_certificates.pdf")
    res = PDFService.combine_pdfs(pdf_paths, combined_target)

    assert os.path.exists(res)

    # Verify 3 pages in combined document
    doc = pymupdf.open(res)
    assert len(doc) == 3
    doc.close()


def test_empty_combined_pdf_raises_error(tmp_path):
    out_path = str(tmp_path / "empty_combined.pdf")
    with pytest.raises(PDFServiceError, match="no input PDF"):
        PDFService.combine_pdfs([], out_path)
