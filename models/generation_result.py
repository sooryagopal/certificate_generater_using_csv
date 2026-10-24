"""
GenerationResult model for AURELIA — Bulk Certificate Generator.
Tracks per-record generation outcomes for auditing and summary reports.
"""

from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class GenerationResult:
    """
    Represents the output status of an individual certificate generation row.
    """
    row_index: int
    record_id: str
    status: str  # 'SUCCESS', 'SKIPPED', 'FAILED'
    generated_files: List[str] = field(default_factory=list)
    formats: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_csv_dict(self) -> Dict[str, Any]:
        """Convert result into a flat dictionary suitable for CSV report export."""
        return {
            "Row": self.row_index,
            "Participant_Identifier": self.record_id,
            "Status": self.status,
            "Generated_Files": "; ".join(self.generated_files),
            "Formats": "; ".join(self.formats),
            "Error_Details": self.error_message or "",
            "Timestamp": self.timestamp,
        }
