from __future__ import annotations

"""
A1 Capture — reads and extracts data from uploaded files.

Configuration (from workflow config):
  sources: [{role, file, required_fields, confidence_threshold}]
Behavior:
  - reads CSV/Excel from the uploads/samples dir
  - computes file hash (duplicate detection / idempotency)
  - extracts rows with per-row confidence
  - quarantines rows missing required fields
"""
import hashlib
from pathlib import Path

import pandas as pd

from app.agents.base import BaseAgent
from app.config import SAMPLES_DIR, UPLOADS_DIR


class A1Capture(BaseAgent):
    id = "A1"
    name = "Capture"
    description = "Reads CSV/Excel files, validates them, and extracts rows with confidence."
    version = "v2"

    def config_schema(self) -> dict:
        return {
            "sources": "list of {role, file, required_fields, confidence_threshold}",
        }

    def run(self, config: dict, payload: dict, context: dict) -> dict:
        sources = config.get("sources", [])
        extracted = {}
        warnings = []

        for source in sources:
            role = source.get("role", f"source_{len(extracted)}")
            file_name = source.get("file")
            path = self._resolve_file(file_name, payload)

            if path is None or not path.exists():
                warnings.append(f"file not found for role '{role}': {file_name}")
                extracted[role] = {"rows": [], "columns": [], "file_hash": None, "row_count": 0}
                continue

            df = self._read(path)
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]

            required = source.get("required_fields", [])
            threshold = float(source.get("confidence_threshold", 0.5))

            rows, quarantined = [], []
            for idx, row in df.iterrows():
                record = {k: (None if pd.isna(v) else v) for k, v in row.items()}
                missing = [f for f in required if record.get(f) in (None, "")]
                confidence = 1.0 - (0.3 * len(missing) / max(len(required), 1))
                record["_source_row"] = int(idx) + 2  # +2: header + 1-based
                record["_source_file"] = path.name
                record["_confidence"] = round(confidence, 2)
                if missing or confidence < threshold:
                    record["_quarantine_reason"] = f"missing {missing}" if missing else "low confidence"
                    quarantined.append(record)
                else:
                    rows.append(record)

            extracted[role] = {
                "rows": rows,
                "quarantined": quarantined,
                "columns": list(df.columns),
                "file_hash": file_hash,
                "file": path.name,
                "row_count": len(rows),
            }
            if quarantined:
                warnings.append(f"{role}: {len(quarantined)} rows quarantined")

        return {
            "sources": extracted,
            "warnings": warnings,
            "source_snapshot": {s.get("role", str(i)): s.get("file") for i, s in enumerate(sources)},
        }

    def _resolve_file(self, file_name: str, payload: dict) -> Path | None:
        if not file_name:
            return None
        for base in (UPLOADS_DIR, SAMPLES_DIR):
            candidate = base / file_name
            if candidate.exists() and candidate.is_file():
                return candidate
        # payload may carry an absolute path from a fresh upload
        raw = payload.get("uploaded_paths", {}).get(file_name, "")
        if raw:
            p = Path(raw)
            if p.is_file():
                return p
        return None

    def _read(self, path: Path) -> pd.DataFrame:
        if path.suffix.lower() in (".xlsx", ".xls"):
            return pd.read_excel(path)
        return pd.read_csv(path)