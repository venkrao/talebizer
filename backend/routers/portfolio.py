"""Portfolio snapshot endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps import require_snapshot
from backend.json_util import dataframe_records
from backend.schemas import PortfolioFrameResponse, PortfolioRefreshResponse, PortfolioSummaryResponse
from backend.services.snapshot import LoadedSnapshot, SnapshotStore, get_snapshot_store

router = APIRouter()


@router.post("/refresh", response_model=PortfolioRefreshResponse)
def portfolio_refresh(store: SnapshotStore = Depends(get_snapshot_store)) -> PortfolioRefreshResponse:
    try:
        snap = store.refresh()
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    return PortfolioRefreshResponse(
        refreshed_at_utc=snap.refreshed_at_utc.isoformat(),
        n_stocks=len(snap.stocks_df),
        n_options=len(snap.options_df),
    )


@router.get("/summary", response_model=PortfolioSummaryResponse)
def portfolio_summary(snap: LoadedSnapshot = Depends(require_snapshot)) -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(
        refreshed_at_utc=snap.refreshed_at_utc.isoformat(),
        summary=snap.summary,
    )


@router.get("/stocks", response_model=PortfolioFrameResponse)
def portfolio_stocks(snap: LoadedSnapshot = Depends(require_snapshot)) -> PortfolioFrameResponse:
    return PortfolioFrameResponse(
        refreshed_at_utc=snap.refreshed_at_utc.isoformat(),
        rows=dataframe_records(snap.stocks_df),
    )


@router.get("/options", response_model=PortfolioFrameResponse)
def portfolio_options(snap: LoadedSnapshot = Depends(require_snapshot)) -> PortfolioFrameResponse:
    return PortfolioFrameResponse(
        refreshed_at_utc=snap.refreshed_at_utc.isoformat(),
        rows=dataframe_records(snap.options_df),
    )


@router.get("/hedge", response_model=PortfolioFrameResponse)
def portfolio_hedge(snap: LoadedSnapshot = Depends(require_snapshot)) -> PortfolioFrameResponse:
    return PortfolioFrameResponse(
        refreshed_at_utc=snap.refreshed_at_utc.isoformat(),
        rows=dataframe_records(snap.hedge_df),
    )


@router.get("/crash", response_model=PortfolioFrameResponse)
def portfolio_crash(snap: LoadedSnapshot = Depends(require_snapshot)) -> PortfolioFrameResponse:
    return PortfolioFrameResponse(
        refreshed_at_utc=snap.refreshed_at_utc.isoformat(),
        rows=dataframe_records(snap.crash_df),
    )
