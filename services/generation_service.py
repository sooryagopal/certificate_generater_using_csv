"""
Generation Service module for AURELIA — Bulk Certificate Generator.
Coordinates background multi-threaded batch rendering, file export,
thread-safe progress reporting, cancellation, error recovery, and report creation.
"""

from __future__ import annotations
import os
import time
import threading
from typing import List, Dict, Any, Optional, Callable, Set
from PIL import Image

from models.text_field import TextField
from models.strike_line import StrikeLine
from models.generation_result import GenerationResult
from core.renderer import Renderer
from core.filename_utils import FilenameUtils, CollisionPolicy
from services.pdf_service import PDFService
from services.report_service import ReportService


class GenerationOptions:
    """Configuration parameter set for bulk generation execution."""
    def __init__(
        self,
        output_dir: str,
        export_mode: str = "pdf",  # 'pdf', 'png', 'jpg', 'pdf_png', 'pdf_jpg', 'combined_pdf'
        filename_pattern: str = "{Name}_{RollNumber}",
        collision_policy: str = CollisionPolicy.APPEND_ROW,
        create_subfolder: bool = True,
        batch_name: str = "Batch",
        include_combined_pdf: bool = False,
        image_quality: int = 95,
        target_dpi: int = 300,
    ):
        self.output_dir = output_dir
        self.export_mode = export_mode
        self.filename_pattern = filename_pattern
        self.collision_policy = collision_policy
        self.create_subfolder = create_subfolder
        self.batch_name = filename_pattern and FilenameUtils.sanitize_filename(batch_name) or "Certificates"
        self.include_combined_pdf = include_combined_pdf or (export_mode == "combined_pdf")
        self.image_quality = image_quality
        self.target_dpi = target_dpi


class GenerationProgress:
    """Snapshot of real-time batch generation progress."""
    def __init__(
        self,
        current_index: int,
        total_records: int,
        current_name: str,
        completed_count: int,
        skipped_count: int,
        failed_count: int,
        is_finished: bool = False,
        error_message: Optional[str] = None,
        combined_pdf_path: Optional[str] = None,
        report_path: Optional[str] = None,
        elapsed_seconds: float = 0.0,
    ):
        self.current_index = current_index
        self.total_records = total_records
        self.current_name = current_name
        self.completed_count = completed_count
        self.skipped_count = skipped_count
        self.failed_count = failed_count
        self.is_finished = is_finished
        self.error_message = error_message
        self.combined_pdf_path = combined_pdf_path
        self.report_path = report_path
        self.elapsed_seconds = elapsed_seconds

    @property
    def percentage(self) -> float:
        if self.total_records <= 0:
            return 100.0 if self.is_finished else 0.0
        return min(100.0, (self.current_index / self.total_records) * 100.0)


class GenerationService:
    """Manages multithreaded certificate generation batches."""

    def __init__(self) -> None:
        self.renderer = Renderer()
        self._cancel_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running

    def request_cancellation(self) -> None:
        """Signals the background generation loop to abort gracefully."""
        self._cancel_event.set()

    def start_batch_generation(
        self,
        template_image: Image.Image,
        fields: List[TextField],
        records: List[Dict[str, Any]],
        options: GenerationOptions,
        progress_callback: Callable[[GenerationProgress], None],
        completion_callback: Callable[[List[GenerationResult], Optional[str], Optional[str]], None],
        lines: Optional[List[StrikeLine]] = None,
    ) -> None:
        """
        Launches background thread for non-blocking batch generation.
        """
        if self._is_running:
            raise RuntimeError("A certificate generation batch is already in progress.")

        self._cancel_event.clear()
        self._is_running = True

        def run() -> None:
            results: List[GenerationResult] = []
            combined_pdf_path: Optional[str] = None
            report_path: Optional[str] = None

            try:
                results, combined_pdf_path, report_path = self._process_batch(
                    template_image=template_image,
                    fields=fields,
                    records=records,
                    options=options,
                    progress_callback=progress_callback,
                    lines=lines,
                )
            except Exception as e:
                # Fatal worker exception
                progress_callback(
                    GenerationProgress(
                        current_index=0,
                        total_records=len(records),
                        current_name="Fatal Error",
                        completed_count=0,
                        skipped_count=0,
                        failed_count=len(records),
                        is_finished=True,
                        error_message=str(e),
                    )
                )
            finally:
                self._is_running = False
                completion_callback(results, combined_pdf_path, report_path)

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()

    def _process_batch(
        self,
        template_image: Image.Image,
        fields: List[TextField],
        records: List[Dict[str, Any]],
        options: GenerationOptions,
        progress_callback: Callable[[GenerationProgress], None],
        lines: Optional[List[StrikeLine]] = None,
    ) -> Tuple[List[GenerationResult], Optional[str], Optional[str]]:
        """Core batch processing loop executed in worker thread."""
        total_records = len(records)
        completed = 0
        skipped = 0
        failed = 0
        results: List[GenerationResult] = []
        generated_pdf_files: List[str] = []
        used_filenames: Set[str] = set()

        start_time = time.time()

        # Resolve directory structure
        base_dir = options.output_dir
        if options.create_subfolder:
            batch_folder = os.path.join(base_dir, options.batch_name)
            certs_folder = os.path.join(batch_folder, "certificates")
            report_dir = batch_folder
        else:
            batch_folder = base_dir
            certs_folder = os.path.join(base_dir, "certificates")
            report_dir = base_dir

        os.makedirs(certs_folder, exist_ok=True)

        # Determine export formats needed
        export_pdf = options.export_mode in ("pdf", "pdf_png", "pdf_jpg", "combined_pdf") or options.include_combined_pdf
        export_png = options.export_mode in ("png", "pdf_png")
        export_jpg = options.export_mode in ("jpg", "pdf_jpg")

        for idx, record in enumerate(records):
            row_num = idx + 1
            if self._cancel_event.is_set():
                break

            # Identify participant for status display
            participant_id = record.get("Name") or record.get("RollNumber") or record.get("id") or f"Record {row_num}"

            # Notify progress start of record
            progress_callback(
                GenerationProgress(
                    current_index=idx,
                    total_records=total_records,
                    current_name=str(participant_id),
                    completed_count=completed,
                    skipped_count=skipped,
                    failed_count=failed,
                    elapsed_seconds=time.time() - start_time,
                )
            )

            record_files: List[str] = []
            record_formats: List[str] = []

            try:
                # 1. Format output filename base
                base_name = FilenameUtils.format_filename(
                    pattern=options.filename_pattern,
                    record=record,
                    row_number=row_num,
                )

                # Check if we should skip
                skip_this_record = False

                # 2. Render certificate in memory
                rendered_img = self.renderer.render_certificate(
                    template_image=template_image,
                    fields=fields,
                    record=record,
                    scale=1.0,
                    lines=lines,
                )

                # 3. Export PDF if needed
                if export_pdf:
                    pdf_path, should_skip = FilenameUtils.resolve_destination(
                        output_dir=certs_folder,
                        base_name=base_name,
                        extension=".pdf",
                        policy=options.collision_policy,
                        row_number=row_num,
                        existing_names=used_filenames,
                    )
                    if should_skip:
                        skip_this_record = True
                    elif pdf_path:
                        PDFService.export_individual_pdf(
                            image=rendered_img,
                            dest_path=pdf_path,
                            dpi=options.target_dpi,
                        )
                        record_files.append(os.path.basename(pdf_path))
                        record_formats.append("PDF")
                        generated_pdf_files.append(pdf_path)

                # 4. Export PNG if needed
                if export_png and not skip_this_record:
                    png_path, should_skip = FilenameUtils.resolve_destination(
                        output_dir=certs_folder,
                        base_name=base_name,
                        extension=".png",
                        policy=options.collision_policy,
                        row_number=row_num,
                        existing_names=used_filenames,
                    )
                    if not should_skip and png_path:
                        PDFService.export_image(
                            image=rendered_img,
                            dest_path=png_path,
                            fmt="PNG",
                        )
                        record_files.append(os.path.basename(png_path))
                        record_formats.append("PNG")

                # 5. Export JPG if needed
                if export_jpg and not skip_this_record:
                    jpg_path, should_skip = FilenameUtils.resolve_destination(
                        output_dir=certs_folder,
                        base_name=base_name,
                        extension=".jpg",
                        policy=options.collision_policy,
                        row_number=row_num,
                        existing_names=used_filenames,
                    )
                    if not should_skip and jpg_path:
                        PDFService.export_image(
                            image=rendered_img,
                            dest_path=jpg_path,
                            fmt="JPG",
                            quality=options.image_quality,
                        )
                        record_files.append(os.path.basename(jpg_path))
                        record_formats.append("JPG")

                # Record outcome
                if skip_this_record:
                    skipped += 1
                    results.append(
                        GenerationResult(
                            row_index=row_num,
                            record_id=str(participant_id),
                            status="SKIPPED",
                            generated_files=[],
                            formats=[],
                            error_message="Skipped due to existing file collision policy.",
                        )
                    )
                else:
                    completed += 1
                    results.append(
                        GenerationResult(
                            row_index=row_num,
                            record_id=str(participant_id),
                            status="SUCCESS",
                            generated_files=record_files,
                            formats=record_formats,
                        )
                    )

            except Exception as e:
                failed += 1
                results.append(
                    GenerationResult(
                        row_index=row_num,
                        record_id=str(participant_id),
                        status="FAILED",
                        generated_files=[],
                        formats=[],
                        error_message=str(e),
                    )
                )

        # Build combined PDF if requested and PDFs were generated
        combined_pdf_path = None
        if options.include_combined_pdf and generated_pdf_files and not self._cancel_event.is_set():
            try:
                target_combined = os.path.join(batch_folder, "combined_certificates.pdf")
                combined_pdf_path = PDFService.combine_pdfs(
                    pdf_paths=generated_pdf_files,
                    combined_output_path=target_combined,
                )
            except Exception as e:
                # Log combined PDF build warning
                pass

        # Write audit report CSV
        report_path = None
        if results:
            try:
                report_file = os.path.join(report_dir, "generation_report.csv")
                report_path = ReportService.generate_csv_report(results, report_file)
            except Exception:
                pass

        # Final progress dispatch
        progress_callback(
            GenerationProgress(
                current_index=total_records,
                total_records=total_records,
                current_name="Done",
                completed_count=completed,
                skipped_count=skipped,
                failed_count=failed,
                is_finished=True,
                combined_pdf_path=combined_pdf_path,
                report_path=report_path,
                elapsed_seconds=time.time() - start_time,
            )
        )

        return results, combined_pdf_path, report_path
