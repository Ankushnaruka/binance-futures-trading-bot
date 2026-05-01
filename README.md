 # Binance Futures Testnet — Trading Bot

 A small, well-structured Python CLI for placing orders on the Binance
 Futures Testnet (USDT-M). It’s written for local, single‑user use: run the
 script on your machine, provide your Testnet API key + secret in a local
 `.env` file, and send orders from the terminal. There is no web login or
 multi-user account management here.

 ---

 ## 📁 Project Structure

 ```
 trading_bot/
 ├── bot/
 │   ├── __init__.py          # Package marker
 │   ├── client.py            # Binance API client (auth, signing, HTTP)
 │   ├── orders.py            # Order-building logic + OrderResult dataclass
 │   ├── validators.py        # Pure input validation (no side effects)
 │   └── logging_config.py    # Rotating file + coloured console logging
 ├── logs/
 │   ├── market_order.log     # Sample MARKET order log
 │   └── limit_order.log      # Sample LIMIT order log
 ├── cli.py                   # CLI entry point (argparse)
 ├── .env.example             # Credential template
 ├── requirements.txt
 └── README.md
 ```

 ---

 ## ⚙️ Setup

 ### 1. Get Testnet credentials

 1. Visit <https://testnet.binancefuture.com>
 2. Log in (or register with a GitHub account — quick and free)
 3. Go to **API Management** and generate a new key pair
 4. Copy your **API Key** and **Secret Key**

 ### 2. Install dependencies

 ```bash
 # Python 3.10+ recommended
 python -m venv .venv
 source .venv/bin/activate      # Windows: .venv\Scripts\activate

 pip install -r requirements.txt
 ```

 ### 3. Configure credentials

 ```bash
 cp .env.example .env
 # Open .env and paste your API key and secret
 ```

 `.env` is ignored by git so your keys stay local.

 ---

 ## 🚀 How to Run

 ### Basic syntax

 ```
 python cli.py --symbol SYMBOL --side SIDE --type TYPE --quantity QTY [--price PRICE] [--stop-price STOP]
 ```

 ### Examples

 #### Market BUY
 ```bash
 python cli.py \
   --symbol BTCUSDT \
   --side BUY \
   --type MARKET \
   --quantity 0.001
 ```

 #### Limit SELL
 ```bash
 python cli.py \
   --symbol ETHUSDT \
   --side SELL \
   --type LIMIT \
   --quantity 0.01 \
   --price 3500
 ```

 #### Stop-Market SELL *(bonus order type)*
 ```bash
 python cli.py \
   --symbol BTCUSDT \
   --side SELL \
   --type STOP_MARKET \
   --quantity 0.001 \
   --stop-price 58000
 ```

 #### Stop-Limit SELL *(bonus order type)*
 ```bash
 python cli.py \
   --symbol BTCUSDT \
   --side SELL \
   --type STOP \
   --quantity 0.001 \
   --price 57800 \
   --stop-price 58000
 ```

 #### Dry-run (validate only, no order placed)
 ```bash
 python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run
 ```

 ---

 ## 📋 CLI Arguments

 | Argument | Required | Description |
 |----------|----------|-------------|
 | `--symbol` / `-s` | ✅ | Trading pair (e.g. `BTCUSDT`, `ETHUSDT`) |
 | `--side` | ✅ | `BUY` or `SELL` |
 | `--type` / `-t` | ✅ | `MARKET`, `LIMIT`, `STOP_MARKET`, or `STOP` |
 | `--quantity` / `-q` | ✅ | Contract quantity (positive number) |
 | `--price` / `-p` | LIMIT/STOP | Limit price |
 | `--stop-price` | STOP/STOP_MARKET | Trigger price |
 | `--dry-run` | ❌ | Validate and print summary without placing order |

 ---

 ## 📤 Sample Output

 The CLI prints a compact, human-readable summary and then a detailed
 order block. Below are representative outputs captured from Testnet runs.

 ### Market order
 ```
 ════════════════════════════════════════════════════
   🤖  Binance Futures Testnet — Trading Bot
 ════════════════════════════════════════════════════

 📋  Order Request Summary
 ────────────────────────────────────────────────────
   Symbol            : BTCUSDT
   Side              : BUY
   Order Type        : MARKET
   Quantity          : 0.001
 ────────────────────────────────────────────────────

 ✅  Order placed successfully!

 ────────────────────────────────────────────────────
   Order ID       : 4751923847
   Symbol         : BTCUSDT
   Side           : BUY
   Type           : MARKET
   Status         : FILLED
   Orig Qty       : 0.001
   Executed Qty   : 0.001
   Avg Price      : 61234.50000
 ────────────────────────────────────────────────────
 ```

 ### Limit order
 ```
 ✅  Order placed successfully!

 ────────────────────────────────────────────────────
   Order ID       : 1928374650
   Symbol         : ETHUSDT
   Side           : SELL
   Type           : LIMIT
   Status         : NEW
   Orig Qty       : 0.01
   Executed Qty   : 0.00000000
   Avg Price      : 0.00000000
   Limit Price    : 3500.00000000
   Time-in-Force  : GTC
 ────────────────────────────────────────────────────
 ```

 ---

 ## 📝 Logging

 Logs are written to `logs/trading_bot.log` (rotating, max 5 MB × 3 files).

 Every log line includes:
 - Timestamp (ISO 8601)
 - Log level
 - Logger name (module path)
 - Message with structured key=value fields

 The console shows INFO+ with colour; the file captures DEBUG+ for full
 API request/response tracing.

 Sample log lines (also see `logs/market_order.log` and `logs/limit_order.log`):
 ```
 2025-05-01T10:14:01 | INFO     | trading_bot.cli    | CLI invoked | symbol=BTCUSDT side=BUY type=MARKET qty=0.001
 2025-05-01T10:14:01 | INFO     | trading_bot.client | REQUEST  POST /fapi/v1/order | params: {...}
 2025-05-01T10:14:02 | INFO     | trading_bot.client | RESPONSE POST /fapi/v1/order | status=200 body={...}
 2025-05-01T10:14:02 | INFO     | trading_bot.orders | Order placed successfully | orderId=4751923847 status=FILLED
 ```

 ---

 ## 🛡️ Error Handling

 | Scenario | Exit Code | Behaviour |
 |----------|-----------|-----------|
 | Bad CLI input (wrong type/value) | `2` | Validation error message + no API call |
 | Missing API credentials | `1` | Clear instruction to set env vars |
 | API error (bad symbol, insufficient balance) | `3` | Binance error code + message |
 | Network timeout / DNS failure | `4` | Network error message |
 | Unexpected exception | `5` | Full traceback to log file, brief message to stderr |

 ---

 ## 🧪 Assumptions

 1. **Testnet only** — the base URL is hardcoded to `https://testnet.binancefuture.com`.
    Never send real credentials to this bot.
 2. **Quantity precision** — Binance enforces symbol-specific tick/lot size filters.
    If an order is rejected with code `-1111` (precision), reduce decimal places.
 3. **Margin** — Testnet accounts come with a pre-funded balance; no deposit needed.
 4. **LIMIT time-in-force** — defaults to `GTC` (Good-Till-Cancelled).
 5. **STOP order** (bonus) uses Binance's `STOP` type which requires both a
    `stopPrice` (trigger) and a `price` (limit fill price).

 ---

 ## 📦 Dependencies

 | Package | Purpose |
 |---------|---------|
 | `httpx` | Async-capable HTTP client; cleaner than `requests` |
 | `python-dotenv` | Load `.env` credentials without shell export |

 Both are pure Python with no C extensions — install is fast on any platform.
