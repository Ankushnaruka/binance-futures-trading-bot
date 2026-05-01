"""
client.py — Binance Futures Testnet API client wrapper.
Handles authentication, request signing, and raw HTTP communication.
"""

import hashlib
import hmac
import time
import logging
from urllib.parse import urlencode
from typing import Any

import httpx

logger = logging.getLogger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceClientError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class NetworkError(Exception):
    """Raised on network-level failures (timeout, DNS, etc.)."""


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Responsibilities:
      - Sign requests with HMAC-SHA256
      - Attach API key headers
      - Log every outbound request and inbound response
      - Translate HTTP / API errors into typed exceptions
    """

    def __init__(self, api_key: str, api_secret: str, timeout: float = 10.0):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = TESTNET_BASE_URL
        # Underlying HTTP client with API key header pre-attached.
        # Keep the client short-lived where possible to avoid leaking credentials in long-running processes.
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> dict:
        """Add a HMAC-SHA256 signature to a parameter dict.

        This appends `timestamp` and `signature` to the params so private
        endpoints can be authenticated. Do not log `signature` or secrets.
        """
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, path: str, params: dict | None = None, sign: bool = True) -> Any:
        """
        Execute an HTTP request, log it, and return parsed JSON.

        Args:
            method:  HTTP verb ('GET', 'POST', 'DELETE').
            path:    API path, e.g. '/fapi/v1/order'.
            params:  Query / body parameters.
            sign:    Whether to HMAC-sign the request.

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            BinanceClientError: API-level error (bad symbol, etc.).
            NetworkError:        Connection / timeout failure.
        """
        params = params or {}
        if sign:
            params = self._sign(params)

        # Log the outbound request (omit signature for safety).
        logger.info("REQUEST  %s %s | params: %s", method, path, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method == "GET":
                response = self._client.get(path, params=params)
            elif method == "POST":
                response = self._client.post(path, data=params)
            elif method == "DELETE":
                response = self._client.delete(path, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except httpx.TimeoutException as exc:
            # Convert transport-level exceptions into a domain-specific exception
            # so callers can handle network failures uniformly.
            logger.error("Network timeout on %s %s: %s", method, path, exc)
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("Network error on %s %s: %s", method, path, exc)
            raise NetworkError(f"Network failure: {exc}") from exc

        # Log the response (truncated) for troubleshooting.
        logger.info("RESPONSE %s %s | status=%s body=%s", method, path, response.status_code, response.text[:500])

        data = response.json()

        # Binance returns errors as {"code": <negative int>, "msg": "..."}
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            code = data["code"]
            msg = data.get("msg", "Unknown error")
            logger.error("API error — code=%s msg=%s", code, msg)
            raise BinanceClientError(code, msg)

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self) -> dict:
        """Return exchange metadata (symbols, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", sign=False)

    def get_account(self) -> dict:
        """Return futures account information."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(self, **kwargs) -> dict:
        """
        Place a new futures order.

        Keyword args map 1-to-1 with Binance REST params:
          symbol, side, type, quantity, price, timeInForce, stopPrice, etc.
        """
        return self._request("POST", "/fapi/v1/order", params=kwargs)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Fetch a single order by ID."""
        return self._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id})

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order."""
        return self._request("DELETE", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id})

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
