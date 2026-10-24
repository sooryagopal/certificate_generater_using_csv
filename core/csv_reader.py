"""
CSV Reader module for AURELIA — Bulk Certificate Generator.
Robustly reads, parses, validates, and normalizes user-provided CSV files.
Supports UTF-8, UTF-8 with BOM, fallback encodings, delimiter sniffing,
international scripts (including Tamil), and preserves leading zeros.
"""

from __future__ import annotations
import csv
import io
import os
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd


class CSVReaderError(Exception):
    """Custom exception for CSV reading and parsing failures."""
    pass


class CSVData:
    """Container for successfully parsed CSV data and metadata."""
    def __init__(
        self,
        filepath: str,
        columns: List[str],
        records: List[Dict[str, str]],
        encoding: str,
        delimiter: str,
        warnings: List[str]
    ):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.columns = columns
        self.records = records
        self.row_count = len(records)
        self.encoding = encoding
        self.delimiter = delimiter
        self.warnings = warnings

    def get_preview(self, count: int = 10) -> List[Dict[str, str]]:
        """Return the first `count` records for table previews."""
        return self.records[:count]

    def get_record(self, index: int) -> Optional[Dict[str, str]]:
        """Safely fetch record by zero-based row index."""
        if 0 <= index < self.row_count:
            return self.records[index]
        return None


class CSVReader:
    """
    Parser and validator for recipient data files.
    """
    CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin1", "iso-8859-1"]
    COMMON_DELIMITERS = [",", ";", "\t", "|"]

    @classmethod
    def detect_encoding_and_delimiter(
        cls, filepath: str, forced_delimiter: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Detects file encoding and sniffing delimiter.
        Returns: (encoding, delimiter, sample_text)
        """
        if not os.path.exists(filepath):
            raise CSVReaderError(f"CSV file not found: {filepath}")

        if os.path.getsize(filepath) == 0:
            raise CSVReaderError("The selected CSV file is completely empty (0 bytes).")

        raw_bytes = None
        with open(filepath, "rb") as f:
            raw_bytes = f.read(65536)  # Read first 64KB for sniffing

        if not raw_bytes.strip():
            raise CSVReaderError("The selected CSV file contains only whitespace.")

        detected_encoding = None
        sample_text = None

        for enc in cls.CANDIDATE_ENCODINGS:
            try:
                decoded = raw_bytes.decode(enc)
                detected_encoding = enc
                sample_text = decoded
                break
            except UnicodeDecodeError:
                continue

        if not detected_encoding or sample_text is None:
            raise CSVReaderError(
                "Unable to determine CSV text encoding. Please ensure the file is saved in UTF-8 format."
            )

        # Detect delimiter
        if forced_delimiter:
            delimiter = forced_delimiter
        else:
            delimiter = cls._sniff_delimiter(sample_text)

        return detected_encoding, delimiter, sample_text

    @classmethod
    def _sniff_delimiter(cls, text: str) -> str:
        """Sniff delimiter from sample text, falling back to comma."""
        try:
            # Use only first few non-empty lines for sniffer
            lines = [line for line in text.splitlines() if line.strip()][:10]
            sniff_sample = "\n".join(lines)
            dialect = csv.Sniffer().sniff(sniff_sample, delimiters=";,|\t,")
            return dialect.delimiter
        except Exception:
            # Heuristic count fallback on first line
            first_line = text.splitlines()[0] if text.splitlines() else ""
            counts = {d: first_line.count(d) for d in cls.COMMON_DELIMITERS}
            best = max(counts, key=counts.get)
            return best if counts[best] > 0 else ","

    @classmethod
    def load_csv(
        cls, filepath: str, forced_delimiter: Optional[str] = None
    ) -> CSVData:
        """
        Parses the CSV file into a CSVData object.
        Guarantees all cell values are strings (preserving leading zeroes) and handles
        Tamil/international scripts cleanly.
        """
        encoding, delimiter, _ = cls.detect_encoding_and_delimiter(
            filepath, forced_delimiter
        )

        warnings: List[str] = []

        try:
            # Read file lines to find actual header row, skipping blank lines and Excel sep= directives
            header_row: Optional[List[str]] = None
            skip_lines = 0

            with open(filepath, mode="r", encoding=encoding, errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        skip_lines += 1
                        continue
                    # Check for Excel sep= directive
                    if stripped.lower().startswith("sep=") and len(stripped) <= 6:
                        delimiter = stripped[4:].strip()
                        skip_lines += 1
                        continue
                    # Parse candidate header line using current delimiter
                    try:
                        parsed = next(csv.reader([stripped], delimiter=delimiter))
                        if parsed and any(str(p).strip() for p in parsed):
                            header_row = parsed
                            break
                    except Exception:
                        pass
                    skip_lines += 1

            if not header_row or all(not str(h).strip() for h in header_row):
                raise CSVReaderError("The CSV header row is empty or contains only blank columns.")

            cleaned_headers: List[str] = []
            seen_headers = set()

            for i, h in enumerate(header_row):
                # Clean BOM, quotes, and whitespace from column names
                header_name = str(h).replace("\ufeff", "").strip(' \t\r\n"\'')
                if not header_name:
                    header_name = f"Column_{i+1}"
                    warnings.append(f"Header at column index {i+1} was empty; renamed to '{header_name}'.")

                if header_name in seen_headers:
                    # Rename duplicate
                    counter = 2
                    unique_name = f"{header_name}_{counter}"
                    while unique_name in seen_headers:
                        counter += 1
                        unique_name = f"{header_name}_{counter}"
                    warnings.append(
                        f"Duplicate column header '{header_name}' found; renamed to '{unique_name}'."
                    )
                    header_name = unique_name

                seen_headers.add(header_name)
                cleaned_headers.append(header_name)

            # Use pandas with dtype=str to preserve exact string representation (e.g. leading 0s)
            # and keep_default_na=False so 'NA', 'None', etc. aren't converted to float NaN
            df = pd.read_csv(
                filepath,
                encoding=encoding,
                delimiter=delimiter,
                dtype=str,
                keep_default_na=False,
                skiprows=skip_lines + 1,
                names=cleaned_headers,
                header=None,
                skipinitialspace=True,
            )

            # Convert all cells to string cleanly
            records: List[Dict[str, str]] = []
            for _, row in df.iterrows():
                record_dict = {col: str(row[col]) if row[col] is not None else "" for col in cleaned_headers}
                # Check if row is completely empty
                if any(v.strip() for v in record_dict.values()):
                    records.append(record_dict)

            if not records:
                raise CSVReaderError("The CSV file contains a header but no data records.")

            return CSVData(
                filepath=filepath,
                columns=cleaned_headers,
                records=records,
                encoding=encoding,
                delimiter=delimiter,
                warnings=warnings,
            )

        except CSVReaderError:
            raise
        except Exception as e:
            raise CSVReaderError(f"Failed to read CSV file: {str(e)}") from e
