import html
import os
import sys
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

SYMBOL = "BTCUSDT"
INTERVAL = "4h"
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=100"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error in request to Binance: {e}", file=sys.stderr)
        return

    # --- SECURITY VALIDATION ---
    if not isinstance(data, list) or len(data) < PERIOD + 1:
        print(
            f"⚠️ Insufficient data or format error. Candles received: {len(data) if isinstance(data, list) else 'N/A'}"
        )
        print(f"Response Body: {data}")
        return

    df = pd.DataFrame(
        data,
        columns=[
            "time",
            "open",
            "high",
            "low",
            "close",
            "vol",
            "close_time",
            "q_vol",
            "trades",
            "takers_buy_base",
            "takers_buy_quote",
            "ignore",
        ],
    )

    df["close"] = df["close"].astype(float)

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculo de promedio inicial
    avg_gain = gain.rolling(window=PERIOD).mean()
    avg_loss = loss.rolling(window=PERIOD).mean()

    # Suavizado de Wilder (el "Senior way" de calcular RSI)
    for i in range(PERIOD, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (PERIOD - 1) + gain.iloc[i]) / PERIOD
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (PERIOD - 1) + loss.iloc[i]) / PERIOD

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # Verificamos que no haya NaN en el último valor
    if pd.isna(df["rsi"].iloc[-1]):
        print("⚠️ The calculated RSI is NaN. Review input data.")
        return

    last_rsi = round(df["rsi"].iloc[-1], 2)
    last_price = df["close"].iloc[-1]

    if last_rsi <= 35:
        msg = (
            f"🟢 <b>BUY OPPORTUNITY BTC</b>\n"
            f"Price: ${html.escape(str(last_price))}\n"
            f"RSI: {html.escape(str(last_rsi))}\n"
            f"<i>Buy opportunity.</i>"
        )
        send_telegram(msg)
    elif last_rsi >= 70:
        msg = (
            f"🔴 <b>OVERBOUGHT ALERT</b>\n"
            f"Price: ${html.escape(str(last_price))}\n"
            f"RSI: {html.escape(str(last_rsi))}\n"
            f"<i>Do not enter now, wait for correction.</i>"
        )
        send_telegram(msg)
    else:
        # Esto te sirve como Heartbeat en Telegram
        send_telegram(
            f"🤖 <b>Live Monitor</b>\nBTC: ${last_price}\nRSI: {last_rsi}\nStatus: All quiet."
        )


if __name__ == "__main__":
    calculate_rsi()
