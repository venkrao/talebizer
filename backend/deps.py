"""FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from backend.services.snapshot import LoadedSnapshot, SnapshotStore, get_snapshot_store


def require_snapshot(store: SnapshotStore = Depends(get_snapshot_store)) -> LoadedSnapshot:
    snap = store.get_optional()
    if snap is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "no_snapshot",
                "message": "Load portfolio data first via POST /portfolio/refresh.",
            },
        )
    return snap
