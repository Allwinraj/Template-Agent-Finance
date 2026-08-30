"""
A3 Match — matches records between two canonical datasets.

Configuration:
  matching: {keys: [canonical fields], date_tolerance_days, amount_tolerance}
Behavior:
  - exact match first (all keys equal)
  - tolerant match (amount within tolerance, date within window)
  - calls Calculation Engine (amount_difference, date_difference, match_score)
  - produces matches with evidence + unmatched lists
"""
from app.agents.base import BaseAgent
from app.engines import calculation_engine as ce


class A3Match(BaseAgent):
    id = "A3"
    name = "Match"
    description = "Matches records across datasets: exact first, then tolerant."
    version = "v3"

    def config_schema(self) -> dict:
        return {
            "matching.keys": "list of canonical fields",
            "matching.amount_tolerance": "float",
            "matching.date_tolerance_days": "int",
        }

    def run(self, config: dict, payload: dict, context: dict) -> dict:
        matching = config.get("matching", {})
        keys = matching.get("keys", ["amount", "reference"])
        amount_tol = float(matching.get("amount_tolerance", 1.0))
        date_tol = int(matching.get("date_tolerance_days", 3))

        canonical = payload.get("canonical", {})
        roles = list(canonical.keys())
        if len(roles) < 2:
            return {"matches": [], "unmatched": list(canonical.get(roles[0], {}).get("rows", [])) if roles else [], "note": "need 2 sources"}

        left_role, right_role = roles[0], roles[1]
        left_rows = canonical.get(left_role, {}).get("rows", [])
        right_rows = canonical.get(right_role, {}).get("rows", [])

        matches, matched_right = [], set()

        # Pass 1: exact match on all keys
        right_by_key = {}
        for j, r in enumerate(right_rows):
            k = tuple(str(r.get(f)) for f in keys)
            right_by_key.setdefault(k, []).append(j)

        for i, l in enumerate(left_rows):
            k = tuple(str(l.get(f)) for f in keys)
            if k in right_by_key:
                j = right_by_key[k].pop(0)
                if not right_by_key[k]:
                    del right_by_key[k]
                matched_right.add(j)
                matches.append(self._build_match(l, right_rows[j], left_role, right_role, 0.0, 0, True, 100.0))

        # Pass 2: tolerant match on remaining
        remaining_left = [l for l in left_rows if not any(m["left"] is l for m in matches)]
        for l in remaining_left:
            best = None
            for j, r in enumerate(right_rows):
                if j in matched_right:
                    continue
                amount_diff = ce.amount_difference(a=l.get("amount") or 0, b=r.get("amount") or 0)
                date_diff = ce.date_difference(date_1=l.get("transaction_date"), date_2=r.get("transaction_date"))
                if amount_diff is None or date_diff is None:
                    continue
                if amount_diff <= amount_tol and date_diff <= date_tol:
                    ref_match = (l.get("reference") or "").strip().lower() == (r.get("reference") or "").strip().lower()
                    score = ce.match_score(amount_diff=amount_diff, date_diff=date_diff, ref_match=ref_match)
                    if best is None or score > best["score"]:
                        best = {"j": j, "amount_diff": amount_diff, "date_diff": date_diff, "ref_match": ref_match, "score": score}
            if best:
                matched_right.add(best["j"])
                matches.append(self._build_match(l, right_rows[best["j"]], left_role, right_role, best["amount_diff"], best["date_diff"], best["ref_match"], best["score"]))

        unmatched_left = [l for l in left_rows if not any(m["left"] is l for m in matches)]
        unmatched_right = [r for j, r in enumerate(right_rows) if j not in matched_right]

        return {
            "matches": matches,
            "unmatched": {left_role: unmatched_left, right_role: unmatched_right},
            "stats": {
                "left": len(left_rows), "right": len(right_rows),
                "matched": len(matches),
                "unmatched_left": len(unmatched_left),
                "unmatched_right": len(unmatched_right),
            },
        }

    @staticmethod
    def _build_match(l, r, left_role, right_role, amount_diff, date_diff, ref_match, score) -> dict:
        return {
            "left": l,
            "right": r,
            "left_role": left_role,
            "right_role": right_role,
            "amount_diff": amount_diff,
            "date_diff": date_diff,
            "ref_match": ref_match,
            "score": score,
            "status": "matched" if score >= 95 else "requires_review",
            "evidence": {
                "left_ref": f"{l.get('_source_file')}:{l.get('_source_row')}",
                "right_ref": f"{r.get('_source_file')}:{r.get('_source_row')}",
            },
        }