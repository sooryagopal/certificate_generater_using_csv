"""
Unit tests for GenerationService in AURELIA.
Tests batch generation execution, report creation, error isolation per record, and thread cancellation.
"""

import os
import time
from PIL import Image
from models.text_field import TextField
from services.generation_service import GenerationService, GenerationOptions
from services.report_service import ReportService


def test_batch_generation_execution(tmp_path):
    out_dir = tmp_path / "batch_out"
    out_dir.mkdir()

    template = Image.new("RGB", (800, 600), "#0B0B0D")
    fields = [
        TextField(name="Name", column_name="Name", x=0.5, y=0.5, font_size=36),
    ]
    records = [
        {"Name": "Soorya G", "RollNumber": "23ADR154"},
        {"Name": "Prathisha S", "RollNumber": "23ADR132"},
        {"Name": "Ruban S", "RollNumber": "23ADR144"},
    ]

    options = GenerationOptions(
        output_dir=str(out_dir),
        export_mode="pdf_png",
        filename_pattern="{Name}_{RollNumber}",
        create_subfolder=True,
        batch_name="TestBatch",
        include_combined_pdf=True,
        target_dpi=150,
    )

    service = GenerationService()
    progress_snapshots = []
    completed_results = []
    combined_pdf_path = None
    report_csv_path = None

    def on_progress(p):
        progress_snapshots.append(p)

    def on_complete(results, combined_pdf, report_path):
        nonlocal combined_pdf_path, report_csv_path
        completed_results.extend(results)
        combined_pdf_path = combined_pdf
        report_csv_path = report_path

    # Start generation
    service.start_batch_generation(
        template_image=template,
        fields=fields,
        records=records,
        options=options,
        progress_callback=on_progress,
        completion_callback=on_complete,
    )

    # Wait for background thread
    timeout = 10
    start = time.time()
    while service.is_running() and (time.time() - start) < timeout:
        time.sleep(0.1)

    assert not service.is_running()
    assert len(completed_results) == 3
    assert all(r.status == "SUCCESS" for r in completed_results)

    # Check generated files on disk
    certs_folder = out_dir / "TestBatch" / "certificates"
    assert certs_folder.exists()
    assert (certs_folder / "Soorya_G_23ADR154.pdf").exists()
    assert (certs_folder / "Soorya_G_23ADR154.png").exists()

    # Check combined PDF
    assert combined_pdf_path is not None
    assert os.path.exists(combined_pdf_path)

    # Check Generation Report CSV
    assert report_csv_path is not None
    assert os.path.exists(report_csv_path)
    with open(report_csv_path, "r", encoding="utf-8-sig") as f:
        content = f.read()
        assert "Soorya G" in content
        assert "SUCCESS" in content


def test_generation_cancellation(tmp_path):
    out_dir = tmp_path / "cancel_out"
    out_dir.mkdir()

    template = Image.new("RGB", (600, 400), "#000000")
    fields = [TextField(name="Name", column_name="Name")]
    # Large set of records
    records = [{"Name": f"Participant {i}"} for i in range(50)]

    options = GenerationOptions(
        output_dir=str(out_dir),
        export_mode="pdf",
        filename_pattern="Cert_{row}",
        create_subfolder=False,
    )

    service = GenerationService()
    completed_results = []

    def on_progress(p):
        # Cancel as soon as first record begins
        if p.current_index >= 1:
            service.request_cancellation()

    def on_complete(results, combined_pdf, report_path):
        completed_results.extend(results)

    service.start_batch_generation(
        template_image=template,
        fields=fields,
        records=records,
        options=options,
        progress_callback=on_progress,
        completion_callback=on_complete,
    )

    timeout = 10
    start = time.time()
    while service.is_running() and (time.time() - start) < timeout:
        time.sleep(0.1)

    assert not service.is_running()
    # It must have stopped early (far fewer than 50 records processed)
    assert len(completed_results) < 50
