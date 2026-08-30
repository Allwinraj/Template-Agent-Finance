from __future__ import annotations

"""Routes: review queue + human decisions (README §3B)."""
from fastapi import APIRouter, HTTPException

from app.services import exception_service

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


@router.get("/")
def list_exceptions(queue: str | None = None):
    return exception_service.list_open(queue)


@router.get("/{exception_id}")
def get_exception(exception_id: str):
    exc = exception_service.find_one("exceptions", lambda e: e.get("exception_id") == exception_id)
    if not exc:
        raise HTTPException(status_code=404, detail="exception not found")
    return exc


@router.post("/{exception_id}/decision")
def decide(exception_id: str, decision: str, comment: str = "", decided_by: str = "reviewer-17"):
    result = exception_service.decide(exception_id, decision, comment, decided_by)
    if not result:
        raise HTTPException(status_code=404, detail="exception not found")
    return result
