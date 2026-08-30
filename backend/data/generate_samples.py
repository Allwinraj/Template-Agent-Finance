"""
Generate seeded, realistic dummy datasets for the POC use cases.

Run:  python backend/data/generate_samples.py
Output: data/samples/bank_statement.csv, sap_gl_export.csv,
        budget_actuals.csv, budget_plan.csv, budget_commentary.csv
"""
import csv
import random
import sys
from pathlib import Path

random.seed(42)

# Use the same SAMPLES_DIR as the app config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import SAMPLES_DIR  # noqa: E402

SAMPLES = SAMPLES_DIR
SAMPLES.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# POC 1: Bank-to-GL reconciliation
# ---------------------------------------------------------------------------

def gen_bank_to_gl():
    bank_rows = []
    gl_rows = []
    refs = [f"INV-{1000+i}" for i in range(40)]

    for i, ref in enumerate(refs):
        amount = round(random.uniform(500, 5000), 2)
        date = f"2026-08-{random.randint(1, 28):02d}"

        # 85% exact match, 10% within tolerance, 5% unmatched
        roll = random.random()
        if roll < 0.85:
            bank_rows.append({"Value Date": date, "Amount": amount, "Reference": ref, "Description": f"Payment {ref}"})
            gl_rows.append({"Posting Date": date, "Amount in LC": amount, "Assignment": ref, "Document Number": f"DOC-{i+1}"})
        elif roll < 0.95:
            gl_amt = round(amount + random.choice([-0.40, 0.30, -0.25, 0.50]), 2)
            bank_rows.append({"Value Date": date, "Amount": amount, "Reference": ref, "Description": f"Payment {ref}"})
            gl_rows.append({"Posting Date": date, "Amount in LC": gl_amt, "Assignment": ref, "Document Number": f"DOC-{i+1}"})
        else:
            bank_rows.append({"Value Date": date, "Amount": amount, "Reference": ref, "Description": f"Payment {ref}"})

    bank_rows.append(bank_rows[0])  # one duplicate

    _write("bank_statement.csv", bank_rows)
    _write("sap_gl_export.csv", gl_rows)
    print(f"  bank_statement.csv: {len(bank_rows)} rows")
    print(f"  sap_gl_export.csv:  {len(gl_rows)} rows")


# ---------------------------------------------------------------------------
# POC 2: Budget-vs-actual analysis
# ---------------------------------------------------------------------------

ACCOUNTS = [
    ("400000", "Product Revenue"),
    ("410000", "Service Revenue"),
    ("500000", "Office Expenses"),
    ("510000", "Travel Expenses"),
    ("520000", "Software Expenses"),
    ("530000", "Marketing Expenses"),
]
COST_CENTERS = ["CC-10", "CC-20", "CC-30"]
PERIOD = "2026-08"


def gen_budget_vs_actual():
    actuals, budget, commentary = [], [], []

    for acct, acct_name in ACCOUNTS:
        for cc in COST_CENTERS:
            budget_amt = round(random.uniform(20000, 80000), 2)

            # Deterministic variance profile per account type:
            #   revenue accounts: slight over-performance (+2..+12%)
            #   expense accounts: mostly within ±8%, one material, one zero-budget
            if acct.startswith("4"):
                pct = random.uniform(0.02, 0.12)
                actual_amt = round(budget_amt * (1 + pct), 2)
            else:
                roll = random.random()
                if acct == "520000" and cc == "CC-30":
                    budget_amt = 0.0
                    actual_amt = round(random.uniform(3000, 9000), 2)  # zero-budget exception
                elif acct == "530000" and cc == "CC-20":
                    actual_amt = round(budget_amt * 1.35, 2)           # material variance (+35%)
                elif roll < 0.8:
                    actual_amt = round(budget_amt * random.uniform(0.92, 1.08), 2)
                else:
                    actual_amt = round(budget_amt * random.uniform(1.08, 1.18), 2)

            key = {"Company Code": "1000", "GL Account": acct, "Cost Center": cc, "Fiscal Period": PERIOD}
            actuals.append({**key, "Amount": actual_amt})
            budget.append({**key, "Budget Amount": budget_amt})

            variance = round(actual_amt - budget_amt, 2)
            pct = round((variance / budget_amt * 100), 1) if budget_amt else None
            commentary.append({
                **key,
                "GL Account Name": acct_name,
                "Variance": variance,
                "Variance %": pct if pct is not None else "n/a",
                "Commentary": _driver_comment(acct, variance, budget_amt),
            })

    _write("budget_actuals.csv", actuals)
    _write("budget_plan.csv", budget)
    _write("budget_commentary.csv", commentary)
    print(f"  budget_actuals.csv:    {len(actuals)} rows")
    print(f"  budget_plan.csv:       {len(budget)} rows")
    print(f"  budget_commentary.csv: {len(commentary)} rows")


def _driver_comment(acct, variance, budget):
    if budget == 0:
        return "Unbudgeted spend — new initiative approved mid-period; budget amendment pending."
    pct = variance / budget * 100 if budget else 0
    if pct > 25:
        return "Vendor price increase plus unplanned license renewals; procurement reviewing contract terms."
    if pct > 8:
        return "Higher activity volume than planned; partially offset by timing shifts expected next period."
    if pct < -8:
        return "Under-spend due to delayed hiring and postponed projects."
    return "In line with plan; no significant drivers to report."


def _write(name, rows):
    path = SAMPLES / name
    if rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    print("Generating sample datasets...")
    gen_bank_to_gl()
    gen_budget_vs_actual()
    print("Done.")