import html
import os
import sys
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Kraken uses XBT for Bitcoin
SYMBOL = "XBTUSDT"
INTERVAL = 60
PERIOD = 14
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram(message: str) -> None:
    if not TOKEN or not CHAT_ID:
        print("Telegram token or chat ID not found.", file=sys.stderr)
        sys.exit(1)
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    r = requests.post(url, json=payload, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print(r.text, file=sys.stderr)
        raise
    print(f"Telegram message sent: {message}")


def calculate_rsi():
    # Kraken Public OHLC endpoint - No API Key needed and very GH-friendly
    url = f"https://api.kraken.com/0/public/OHLC?pair={SYMBOL}&interval={INTERVAL}"

    try:
        # We still use a browser-like User-Agent just in case
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data_json = response.json()

        # Kraken returns data in result -> [Pair Name]
        # We take the first pair found in result
        result = data_json.get("result", {})
        pair_key = list(result.keys())[0] if result else None
        data = result.get(pair_key, []) if pair_key else []

    except Exception as e:
        print(f"❌ Error in request to Kraken: {e}", file=sys.stderr)
        return

    # --- SECURITY VALIDATION ---
    if not isinstance(data, list) or len(data) < PERIOD + 1:
        print(f"⚠️ Insufficient data. Candles received: {len(data)}")
        return

    # Kraken returns: [time, open, high, low, close, vwap, volume, count]
    df = pd.DataFrame(
        data,
        columns=["time", "open", "high", "low", "close", "vwap", "vol", "count"],
    )

    # Kraken sends oldest to newest (correct for RSI), but we ensure types
    df["close"] = df["close"].astype(float)

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Initial average calculation
    avg_gain = gain.rolling(window=PERIOD).mean()
    avg_loss = loss.rolling(window=PERIOD).mean()

    # Wilder's Smoothing
    for i in range(PERIOD, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (PERIOD - 1) + gain.iloc[i]) / PERIOD
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (PERIOD - 1) + loss.iloc[i]) / PERIOD

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # Check for NaN in the last value
    if pd.isna(df["rsi"].iloc[-1]):
        print("⚠️ The calculated RSI is NaN. Review input data.")
        return

    last_rsi = round(df["rsi"].iloc[-1], 2)
    last_price = df["close"].iloc[-1]

    if last_rsi <= 35:
        msg = (
            f"🟢 <b>BUY OPPORTUNITY BTC (Kraken)</b>\n"
            f"Price: ${html.escape(str(last_price))}\n"
            f"RSI: {html.escape(str(last_rsi))}\n"
            f"<i>Buy opportunity.</i>"
        )
        send_telegram(msg)
    elif last_rsi >= 70:
        msg = (
            f"🔴 <b>OVERBOUGHT ALERT (Kraken)</b>\n"
            f"Price: ${html.escape(str(last_price))}\n"
            f"RSI: {html.escape(str(last_rsi))}\n"
            f"<i>Wait for correction.</i>"
        )
        send_telegram(msg)
    else:
        send_telegram(
            f"🤖 <b>Live Monitor (Kraken)</b>\n"
            f"BTC: ${last_price}\n"
            f"RSI: {last_rsi}\n"
            f"Status: All quiet."
        )


if __name__ == "__main__":
    calculate_rsi()
