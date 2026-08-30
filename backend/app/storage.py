from __future__ import annotations

"""Simple JSON-file persistence — swap for a real DB later."""
import json
from pathlib import Path

from app.config import STORE_DIR


def _path(collection: str) -> Path:
    return STORE_DIR / f"{collection}.json"


def load(collection: str) -> list:
    p = _path(collection)
    if not p.exists():
        return []
    try:
        items = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    # Guard against cloud-sync corruption (e.g. OneDrive can merge/race file
    # writes and produce duplicate records). Dedupe on 'id', keeping the last
    # occurrence, so find_one/update stay deterministic.
    if isinstance(items, list):
        seen_ids = {}
        has_ids = all(isinstance(x, dict) and x.get("id") for x in items)
        if has_ids and len(items) > 1:
            for x in items:
                seen_ids[x["id"]] = x
            deduped = list(seen_ids.values())
            if len(deduped) != len(items):
                print(f"[storage] WARNING: {collection}.json contained "
                      f"{len(items) - len(deduped)} duplicate record(s) (cloud-sync race?) — deduped on read")
                items = deduped
    return items


def _write(collection: str, items: list) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STORE_DIR / f"{collection}.json.tmp"
    tmp.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
    tmp.replace(STORE_DIR / f"{collection}.json")


def insert(collection: str, item: dict) -> dict:
    """Add a record with an auto id."""
    items = load(collection)
    item = {**item, "id": _next_id(items)}
    items.append(item)
    _write(collection, items)
    return item


def append(collection: str, item: dict) -> dict:
    """Append-only insert (used by audit service)."""
    items = load(collection)
    item = {**item, "seq": len(items) + 1}
    items.append(item)
    _write(collection, items)
    return item


def find(collection: str, predicate) -> list:
    return [x for x in load(collection) if predicate(x)]


def find_one(collection: str, predicate):
    for item in load(collection):
        if predicate(item):
            return item
    return None


def update(collection: str, item_id: str, patch: dict) -> dict | None:
    items = load(collection)
    for i, item in enumerate(items):
        if item.get("id") == item_id:
            items[i] = {**item, **patch}
            _write(collection, items)
            return items[i]
    return None


def delete(collection: str, item_id: str) -> bool:
    items = load(collection)
    remaining = [x for x in items if x.get("id") != item_id]
    if len(remaining) != len(items):
        _write(collection, remaining)
        return True
    return False


def _next_id(items: list) -> str:
    """Gap-safe: max numeric id + 1 (dedup/sync races can create gaps)."""
    max_id = 0
    for x in items:
        try:
            max_id = max(max_id, int(str(x.get("id", "0"))) )
        except (ValueError, TypeError):
            continue
    return f"{max_id + 1:06d}"