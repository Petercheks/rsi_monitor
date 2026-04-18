# RSI Monitor

A small Python utility that pulls **BTCUSDT** candle data from the public Binance API, computes the **RSI (14)** on **4-hour** closes using Wilder smoothing, and sends the result to a **Telegram** chat.

## What it does

- Fetches the last 100 **4h** klines for `BTCUSDT`.
- Calculates RSI with period **14** (Wilder-style smoothing after the initial simple average).
- Sends a Telegram message:
  - **RSI ≤ 35**: “opportunity” style alert (oversold zone).
  - **RSI ≥ 70**: overbought alert.
  - **Otherwise**: a short status message including the current RSI.

HTTP calls use timeouts; Telegram errors surface as non-zero exits with the API response body on stderr.

## Requirements

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (recommended for installs and runs)

Dependencies are listed in `pyproject.toml` (`pandas`, `requests`, `python-dotenv`).

## Configuration

| Variable           | Description                                                   |
| ------------------ | ------------------------------------------------------------- |
| `TELEGRAM_TOKEN`   | Bot token from [@BotFather](https://t.me/BotFather).          |
| `TELEGRAM_CHAT_ID` | Target chat ID (user, group, or channel the bot can message). |

For local runs, create a `.env` file in the project root (it is gitignored):

```env
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

`python-dotenv` loads `.env` automatically when you run the script.

## Local usage

Install dependencies and run:

```bash
uv sync
uv run main.py
```

Or with `python` after installing into a venv:

```bash
pip install -e .
python main.py
```

## GitHub Actions

The workflow `.github/workflows/rsi_alert.yml`:

- Runs on a **schedule**: every **4 hours** at minute 0 (UTC), aligned with the 4h candle interval.
- Supports **manual runs** via `workflow_dispatch`.
- Expects repository secrets **`TELEGRAM_TOKEN`** and **`TELEGRAM_CHAT_ID`** (Settings → Secrets and variables → Actions).

The job checks out the repo, installs **uv**, and runs `uv run main.py` with those secrets as environment variables (no `.env` file required on the runner).

## Customizing behavior

Edit the constants at the top of `main.py`:

- `SYMBOL` — trading pair (default `BTCUSDT`).
- `INTERVAL` — Binance kline interval (default `4h`).
- `PERIOD` — RSI length (default `14`).
- Alert thresholds are **35** and **70** in the `if` / `elif` branches; adjust as needed.

## Disclaimer

This tool is for **informational purposes only**. It is not financial advice. Market data comes from Binance’s public API; availability and limits are subject to Binance’s terms.
