#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet trading bot.

Usage examples:
  # Market BUY
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit SELL
  python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500

  # Stop-Market (bonus order type)
  python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 58000

  # Stop-Limit (bonus order type)
  python cli.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.001 --price 57800 --stop-price 58000

Environment variables (or .env file):
  BINANCE_API_KEY     — your Testnet API key
  BINANCE_API_SECRET  — your Testnet API secret
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.logging_config import setup_logging
from bot.orders import place_order
from bot.validators import validate_all

import logging

# Boot logging before anything else so every import is covered
load_dotenv()
setup_logging()
logger = logging.getLogger("trading_bot.cli")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_banner():
    print("\n" + "═" * 52)
    print("  🤖  Binance Futures Testnet — Trading Bot")
    print("═" * 52)
    # Small ASCII banner shown at CLI startup.


def _print_request_summary(params: dict):
    print("\n📋  Order Request Summary")
    print("─" * 52)
    for key, value in params.items():
        if value is not None:
            label = key.replace("_", " ").title()
            print(f"  {label:<18}: {value}")
    print("─" * 52)


def _get_credentials() -> tuple[str, str]:
    """Read API credentials from environment variables."""
    # Loads credentials from environment or .env and exits with code 1 if missing.
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        print(
            "\n❌  Missing API credentials.\n"
            "    Set BINANCE_API_KEY and BINANCE_API_SECRET in your environment\n"
            "    or in a .env file in the project root.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    return api_key, api_secret


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place orders on Binance Futures Testnet (USDT-M)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        metavar="SIDE",
        help="Order side: BUY or SELL",
    )
    parser.add_argument(
        "--type", "-t",
        required=True,
        dest="order_type",
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP",
                 "market", "limit", "stop_market", "stop"],
        metavar="TYPE",
        help="Order type: MARKET | LIMIT | STOP_MARKET | STOP",
    )
    parser.add_argument(
        "--quantity", "-q",
        required=True,
        metavar="QTY",
        help="Order quantity (number of contracts or coins)",
    )
    parser.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT and STOP orders)",
    )
    parser.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP_MARKET and STOP orders)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the request summary without placing an order",
    )

    return parser

# Build an argparse parser that maps CLI flags to internal parameters.


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    _print_banner()

    parser = build_parser()
    args = parser.parse_args()

    # 1. Validate all user inputs
    logger.info(
        "CLI invoked | symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        args.symbol, args.side, args.order_type, args.quantity, args.price, args.stop_price,
    )

    try:
        validated = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        # Validation errors are surfaced to the user with exit code 2.
        logger.error("Validation failed: %s", exc)
        print(f"\n❌  Validation Error: {exc}\n", file=sys.stderr)
        sys.exit(2)

    _print_request_summary(validated)

    if args.dry_run:
        print("\n🔍  Dry-run mode — no order placed.\n")
        logger.info("Dry-run mode — exiting without placing order")
        sys.exit(0)

    # 2. Load credentials and build client
    api_key, api_secret = _get_credentials()

    # 3. Place the order
    try:
        with BinanceFuturesClient(api_key=api_key, api_secret=api_secret) as client:
            result = place_order(
                client,
                symbol=validated["symbol"],
                side=validated["side"],
                order_type=validated["order_type"],
                quantity=validated["quantity"],
                price=validated["price"],
                stop_price=validated["stop_price"],
            )

    except BinanceClientError as exc:
        # API-returned failures are logged and returned with exit code 3.
        logger.error("Order failed — BinanceClientError %s: %s", exc.code, exc.message)
        print(f"\n❌  Order failed (API error {exc.code}): {exc.message}\n", file=sys.stderr)
        sys.exit(3)

    except NetworkError as exc:
        logger.error("Order failed — NetworkError: %s", exc)
        print(f"\n❌  Network error: {exc}\n", file=sys.stderr)
        sys.exit(4)

    except Exception as exc:
        # Catch-all for unexpected exceptions; exit code 5 indicates this case.
        logger.exception("Unexpected error: %s", exc)
        print(f"\n❌  Unexpected error: {exc}\n", file=sys.stderr)
        sys.exit(5)

    # 4. Print result
    print("\n✅  Order placed successfully!\n")
    print(result.pretty())
    print()


if __name__ == "__main__":
    main()
