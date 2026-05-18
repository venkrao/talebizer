"""Thread-safe in-memory portfolio snapshot for the API layer."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from src.ib_service import get_portfolio_frames


@dataclass(frozen=True)
class LoadedSnapshot:
    stocks_df: pd.DataFrame
    options_df: pd.DataFrame
    hedge_df: pd.DataFrame
    crash_df: pd.DataFrame
    summary: dict[str, Any]
    refreshed_at_utc: datetime


class SnapshotStore:
    """Single-user cache; sufficient for local loopback Phase 1."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snap: Optional[LoadedSnapshot] = None
        self._last_error: Optional[str] = None

    def refresh(self) -> LoadedSnapshot:
        with self._lock:
            try:
                stocks_df, options_df, hedge_df, crash_df, summary = get_portfolio_frames()
                snap = LoadedSnapshot(
                    stocks_df=stocks_df,
                    options_df=options_df,
                    hedge_df=hedge_df,
                    crash_df=crash_df,
                    summary=summary,
                    refreshed_at_utc=datetime.now(timezone.utc),
                )
                self._snap = snap
                self._last_error = None
                return snap
            except Exception as exc:
                self._last_error = str(exc)
                raise

    def get_optional(self) -> Optional[LoadedSnapshot]:
        with self._lock:
            return self._snap

    def last_error(self) -> Optional[str]:
        with self._lock:
            return self._last_error


_store = SnapshotStore()


def get_snapshot_store() -> SnapshotStore:
    return _store
