"""
orders.py — Order placement logic and result formatting.

This module sits between the CLI and the raw API client.
It builds the correct payload for each order type, calls the client,
and returns a normalised OrderResult dataclass.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError

logger = logging.getLogger("trading_bot.orders")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OrderResult:
    """Normalised view of a Binance order response."""
    # Lightweight container used by CLI output and logging.
    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str
    stop_price: str
    time_in_force: str
    raw: dict = field(repr=False)

    @classmethod
    def from_response(cls, data: dict) -> "OrderResult":
        return cls(
            order_id=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            price=data.get("price", "0"),
            stop_price=data.get("stopPrice", "0"),
            time_in_force=data.get("timeInForce", ""),
            raw=data,
        )

    def pretty(self) -> str:
        """Human-readable summary of the order result."""
        lines = [
            "─" * 52,
            f"  Order ID       : {self.order_id}",
            f"  Symbol         : {self.symbol}",
            f"  Side           : {self.side}",
            f"  Type           : {self.order_type}",
            f"  Status         : {self.status}",
            f"  Orig Qty       : {self.orig_qty}",
            f"  Executed Qty   : {self.executed_qty}",
            f"  Avg Price      : {self.avg_price}",
        ]
        if self.price and self.price != "0":
            lines.append(f"  Limit Price    : {self.price}")
        if self.stop_price and self.stop_price != "0":
            lines.append(f"  Stop Price     : {self.stop_price}")
        if self.time_in_force:
            lines.append(f"  Time-in-Force  : {self.time_in_force}")
        lines.append("─" * 52)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Order builder helpers
# ---------------------------------------------------------------------------

def _build_market_payload(symbol: str, side: str, quantity: float) -> dict:
    # Build payload for immediate market execution.
    return {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }


def _build_limit_payload(symbol: str, side: str, quantity: float, price: float) -> dict:
    # Build a LIMIT order payload; defaults to GTC Time-in-Force.
    return {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": "GTC",   # Good-Till-Cancelled — sensible default
    }


def _build_stop_market_payload(symbol: str, side: str, quantity: float, stop_price: float) -> dict:
    # Stop-market triggers a market order when the trigger price is hit.
    return {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "quantity": quantity,
        "stopPrice": stop_price,
    }


def _build_stop_limit_payload(
    symbol: str, side: str, quantity: float, price: float, stop_price: float
) -> dict:
    # Stop (stop-limit) requires both a trigger and a limit price.
    return {
        "symbol": symbol,
        "side": side,
        "type": "STOP",
        "quantity": quantity,
        "price": price,
        "stopPrice": stop_price,
        "timeInForce": "GTC",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def place_order(
    client: BinanceFuturesClient,
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> OrderResult:
    """
    Place an order on Binance Futures Testnet.

    Args:
        client:      Authenticated BinanceFuturesClient instance.
        symbol:      Trading pair, e.g. 'BTCUSDT'.
        side:        'BUY' or 'SELL'.
        order_type:  'MARKET', 'LIMIT', 'STOP_MARKET', or 'STOP'.
        quantity:    Number of contracts / coins.
        price:       Limit price (required for LIMIT / STOP).
        stop_price:  Trigger price (required for STOP_MARKET / STOP).

    Returns:
        OrderResult dataclass.

    Raises:
        BinanceClientError: API rejected the order.
        NetworkError:        Connection failure.
        ValueError:          Unsupported order type (should be caught by validators).
    """
    # Build the correct payload for each order type
    if order_type == "MARKET":
        payload = _build_market_payload(symbol, side, quantity)

    elif order_type == "LIMIT":
        if price is None:
            raise ValueError("price is required for LIMIT orders")
        payload = _build_limit_payload(symbol, side, quantity, price)

    elif order_type == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("stop_price is required for STOP_MARKET orders")
        payload = _build_stop_market_payload(symbol, side, quantity, stop_price)

    elif order_type == "STOP":
        if price is None or stop_price is None:
            raise ValueError("Both price and stop_price are required for STOP orders")
        payload = _build_stop_limit_payload(symbol, side, quantity, price, stop_price)

    else:
        raise ValueError(f"Unsupported order type: {order_type}")

    logger.info(
        "Placing %s %s order | symbol=%s qty=%s price=%s stop=%s",
        side, order_type, symbol, quantity, price, stop_price,
    )

    try:
        response = client.place_order(**payload)
    except BinanceClientError:
        # Exchange returned a business-level error (bad symbol, insufficient balance, etc.)
        logger.error("Order rejected by exchange — see above for details")
        raise
    except NetworkError:
        # Network problems are surfaced to the caller so they can retry or abort.
        logger.error("Network failure while placing order")
        raise

    result = OrderResult.from_response(response)
    logger.info(
        "Order placed successfully | orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id, result.status, result.executed_qty, result.avg_price,
    )
    return result
