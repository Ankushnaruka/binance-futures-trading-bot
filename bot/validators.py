"""
validators.py — Input validation for order parameters.

All validation is pure (no side effects) and raises ValueError with
a human-readable message on failure.
"""

from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP"}

# Pure validation helpers — do not perform I/O or API calls here.


def validate_symbol(symbol: str) -> str:
    """Return uppercased symbol or raise ValueError."""
    s = symbol.strip().upper()
    if not s:
        raise ValueError("Symbol cannot be empty.")
    if not s.isalnum():
        raise ValueError(f"Symbol '{s}' contains invalid characters. Use only letters and digits (e.g. BTCUSDT).")
    return s


def validate_side(side: str) -> str:
    """Return uppercased side or raise ValueError."""
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")
    return s


def validate_order_type(order_type: str) -> str:
    """Return uppercased order type or raise ValueError."""
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValueError(f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'.")
    return t


def validate_quantity(quantity: str | float) -> float:
    """Return positive float quantity or raise ValueError."""
    # Ensure quantity is a numeric type and greater than zero.
    try:
        q = float(quantity)
    except (ValueError, TypeError):
        raise ValueError(f"Quantity must be a number, got '{quantity}'.")
    if q <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {q}.")
    return q


def validate_price(price: str | float | None, order_type: str) -> float | None:
    """
    Validate price field.
    - LIMIT orders require a positive price.
    - MARKET orders must NOT supply a price.
    Returns float or None.
    """
    if order_type == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders.")
        try:
            p = float(price)
        except (ValueError, TypeError):
            raise ValueError(f"Price must be a number, got '{price}'.")
        if p <= 0:
            raise ValueError(f"Price must be greater than zero, got {p}.")
        return p

    if order_type == "MARKET" and price is not None:
        raise ValueError("Price should not be specified for MARKET orders.")

    return None


def validate_stop_price(stop_price: str | float | None, order_type: str) -> float | None:
    """Validate stop price for STOP / STOP_MARKET orders."""
    # Stop prices are required for stop-type orders and must be positive.
    stop_types = {"STOP", "STOP_MARKET"}
    if order_type in stop_types:
        if stop_price is None:
            raise ValueError(f"--stop-price is required for {order_type} orders.")
        try:
            sp = float(stop_price)
        except (ValueError, TypeError):
            raise ValueError(f"Stop price must be a number, got '{stop_price}'.")
        if sp <= 0:
            raise ValueError(f"Stop price must be greater than zero, got {sp}.")
        return sp
    return None


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """
    Run all validations and return a clean dict of validated values.

    Raises ValueError on the first validation failure.
    """
    # Run lightweight validators sequentially; raise the first encountered error.
    v_symbol = validate_symbol(symbol)
    v_side = validate_side(side)
    v_type = validate_order_type(order_type)
    v_qty = validate_quantity(quantity)
    v_price = validate_price(price, v_type)
    v_stop = validate_stop_price(stop_price, v_type)

    return {
        "symbol": v_symbol,
        "side": v_side,
        "order_type": v_type,
        "quantity": v_qty,
        "price": v_price,
        "stop_price": v_stop,
    }
