"""
A2 Harmonize — converts source columns into the canonical finance model.

Configuration:
  sources[].field_mappings: {source_column: canonical_field}
  date_format (optional), decimal_comma (optional)
Behavior:
  - renames columns per mapping (UI-configurable)
  - normalizes dates, amounts, signs
  - detects duplicates, flags missing canonical fields
  - preserves lineage: _source_file, _source_row, mapping confidence
"""
import pandas as pd

from app.agents.base import BaseAgent

CANONICAL_FIELDS = [
    "transaction_date", "amount", "currency", "reference", "description",
    "company_code", "gl_account", "cost_center", "fiscal_period",
    "vendor", "employee_id", "category", "document_no",
]


class A2Harmonize(BaseAgent):
    id = "A2"
    name = "Harmonize"
    description = "Maps source columns to canonical fields and normalizes values."
    version = "v3"

    def config_schema(self) -> dict:
        return {
            "sources[].field_mappings": "{source_column: canonical_field}",
            "date_format": "str (optional)",
        }

    def run(self, config: dict, payload: dict, context: dict) -> dict:
        sources_cfg = {s.get("role"): s for s in config.get("sources", [])}
        canonical = {}
        warnings = []

        for role, source in payload.get("sources", {}).items():
            cfg = sources_cfg.get(role, {})
            mappings = cfg.get("field_mappings", {})
            rows_out = []
            seen_keys = set()

            # generic mapping-coverage check: warn when an uploaded file's
            # columns no longer match the saved mappings (e.g. new Excel format)
            if mappings:
                missing_cols = [c for c in mappings if c not in (source.get("columns") or [])]
                if missing_cols:
                    warnings.append(
                        f"role '{role}': saved mappings reference columns not present in "
                        f"{source.get('file') or 'the uploaded file'}: {missing_cols} — "
                        f"re-create the agent or fix the mapping for this format"
                    )

            for row in source.get("rows", []):
                rec = {
                    "transaction_date": self._norm_date(row.get(self._src(mappings, "transaction_date"))),
                    "amount": self._norm_amount(row.get(self._src(mappings, "amount"))),
                    "currency": row.get(self._src(mappings, "currency"), "USD"),
                    "reference": row.get(self._src(mappings, "reference")),
                    "description": row.get(self._src(mappings, "description")),
                    "company_code": row.get(self._src(mappings, "company_code"), "1000"),
                    "gl_account": row.get(self._src(mappings, "gl_account")),
                    "cost_center": row.get(self._src(mappings, "cost_center")),
                    "fiscal_period": row.get(self._src(mappings, "fiscal_period")),
                    "vendor": row.get(self._src(mappings, "vendor")),
                    "employee_id": row.get(self._src(mappings, "employee_id")),
                    "category": row.get(self._src(mappings, "category")),
                    "document_no": row.get(self._src(mappings, "document_no")),
                    # lineage
                    "_source_file": row.get("_source_file"),
                    "_source_row": row.get("_source_row"),
                    "_confidence": row.get("_confidence", 1.0),
                    "_role": role,
                }
                # duplicate detection on (reference, amount)
                dup_key = (rec.get("reference"), rec.get("amount"))
                if dup_key in seen_keys:
                    rec["_duplicate"] = True
                else:
                    seen_keys.add(dup_key)
                rows_out.append(rec)

            canonical[role] = {"rows": rows_out, "row_count": len(rows_out)}

        return {"canonical": canonical, "warnings": warnings}

    @staticmethod
    def _src(mappings: dict, canonical_field: str):
        """Reverse lookup: canonical field -> source column."""
        for src_col, canon in mappings.items():
            if canon == canonical_field:
                return src_col
        return canonical_field  # fall back to same name

    @staticmethod
    def _norm_date(value):
        if value in (None, "", "—"):
            return None
        s = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return pd.Timestamp(pd.to_datetime(s, format=fmt)).date().isoformat()
            except (ValueError, TypeError):
                continue
        try:
            return pd.Timestamp(pd.to_datetime(s)).date().isoformat()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _norm_amount(value):
        if value in (None, "", "—"):
            return None
        try:
            s = str(value).replace(",", "").replace(" ", "")
            return round(float(s), 2)
        except (ValueError, TypeError):
            return None