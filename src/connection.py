from __future__ import annotations

import logging
import time
from typing import Optional

from .config import get_ib_config
from .safe_ib import SafeIB, create_safe_ib


logger = logging.getLogger(__name__)


def connect_ib(retries: int = 3, backoff_seconds: float = 5.0) -> SafeIB:
    """
    Create an IB client and connect to TWS / IB Gateway.

    Minimal implementation: simple retry loop, no background tasks.
    """
    cfg = get_ib_config()

    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        ib = create_safe_ib()
        try:
            logger.info(
                "Connecting to IBKR %s:%s clientId=%s (attempt %s/%s)",
                cfg.host,
                cfg.port,
                cfg.client_id,
                attempt,
                retries,
            )
            # Connect in read-only mode. Passing the primary account causes
            # ib_async to call reqAccountUpdates() during startup (synchronously),
            # which populates PortfolioItem objects with marketPrice / marketValue.
            primary_account = cfg.accounts[0] if cfg.accounts else ""
            ib.connect(
                cfg.host,
                cfg.port,
                clientId=cfg.client_id,
                readonly=True,
                account=primary_account,
            )

            if ib.isConnected():
                logger.info("Connected to IBKR (primary account: %s)", primary_account)

                # Subscribe to portfolio updates for any additional accounts.
                # reqAccountUpdates() is called within the same sync context here,
                # so it runs cleanly. Failure is non-fatal; the primary account
                # data will still be available.
                for extra_account in cfg.accounts[1:]:
                    try:
                        ib.reqAccountUpdates(extra_account)
                        logger.info("Subscribed to account updates for %s", extra_account)
                    except Exception as exc:
                        logger.warning(
                            "Could not subscribe to account updates for %s: %s",
                            extra_account,
                            exc,
                        )

                return ib

            last_error = RuntimeError("IB connection did not report as connected")
        except Exception as exc:  # pragma: no cover - minimal error path
            logger.exception("Error connecting to IBKR: %s", exc)
            last_error = exc
            # Ensure we close any half-open connection before retrying
            try:
                ib.disconnect()
            except Exception:
                pass

        if attempt < retries:
            time.sleep(backoff_seconds)

    raise RuntimeError(f"Failed to connect to IBKR after {retries} attempts") from last_error


