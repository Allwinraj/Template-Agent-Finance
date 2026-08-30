"""Engine library API — exposes available calculators and rules."""
from fastapi import APIRouter

from app.engines.calculation_engine import list_calculators
from app.engines.rule_engine import list_rules

router = APIRouter()


@router.get("/calculators")
def list_calculators_endpoint():
    """Return the full calculator library with metadata."""
    return {"calculators": list_calculators()}


@router.get("/rules")
def list_rules_endpoint():
    """Return the full rule library with metadata."""
    return {"rules": list_rules()}

