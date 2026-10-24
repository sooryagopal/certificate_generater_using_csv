"""
Report Service module for AURELIA — Bulk Certificate Generator.
Generates structured CSV audit logs and summary metrics for completed certificate batches.
"""

from __future__ import annotations
import os
import csv
from typing import List, Dict, Any
from models.generation_result import GenerationResult


class ReportService:
    """Manages creation of batch audit reports and summary statistics."""

    @classmethod
    def generate_csv_report(
        cls,
        results: List[GenerationResult],
        report_path: str,
    ) -> str:
        """
        Writes generation outcome for every record into a structured CSV file.
        """
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        tmp_path = f"{report_path}.tmp"

        fieldnames = [
            "Row",
            "Participant_Identifier",
            "Status",
            "Generated_Files",
            "Formats",
            "Error_Details",
            "Timestamp",
        ]

        try:
            with open(tmp_path, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in results:
                    writer.writerow(r.to_csv_dict())

            os.replace(tmp_path, report_path)
            return report_path
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise IOError(f"Could not write generation report: {str(e)}") from e

    @classmethod
    def compute_summary(cls, results: List[GenerationResult]) -> Dict[str, Any]:
        """Calculates aggregate counts from batch results."""
        total = len(results)
        success = sum(1 for r in results if r.status == "SUCCESS")
        skipped = sum(1 for r in results if r.status == "SKIPPED")
        failed = sum(1 for r in results if r.status == "FAILED")
        total_files = sum(len(r.generated_files) for r in results)

        return {
            "total": total,
            "success": success,
            "skipped": skipped,
            "failed": failed,
            "total_files": total_files,
        }
