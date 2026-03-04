from __future__ import annotations

from ib_async import IB


class SafeIB(IB):
    """
    Read-only IB client wrapper.

    This subclass hard-blocks any attempt to place, modify, or cancel orders.
    It is intended as a guardrail so this app cannot trade, even if future
    code changes accidentally try to.
    """

    # --- Hard blocks for anything that could submit/modify/cancel orders ---

    def placeOrder(self, contract, order):  # type: ignore[override]
        raise RuntimeError(
            "Trading is disabled in this application. "
            "SafeIB forbids placeOrder calls."
        )

    def whatIfOrder(self, contract, order):  # type: ignore[override]
        raise RuntimeError(
            "Trading is disabled in this application. "
            "SafeIB forbids what-if order calls."
        )

    def cancelOrder(self, trade):  # type: ignore[override]
        raise RuntimeError(
            "Trading is disabled in this application. "
            "SafeIB forbids cancelOrder calls."
        )

    def bracketOrder(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError(
            "Trading is disabled in this application. "
            "SafeIB forbids bracketOrder helpers."
        )

    @staticmethod
    def oneCancelsAll(orders, ocaGroup, ocaType):  # type: ignore[override]
        raise RuntimeError(
            "Trading is disabled in this application. "
            "SafeIB forbids one-cancels-all order helpers."
        )


def create_safe_ib() -> SafeIB:
    """Factory to create a SafeIB instance."""
    return SafeIB()


