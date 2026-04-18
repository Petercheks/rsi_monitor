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
        print(
            "Telegram token or chat ID not found.",
            file=sys.stderr,
        )
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
    print(f"Mensaje enviado: {message}")


def calculate_rsi():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=100"
    data = requests.get(url, timeout=30).json()

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

    avg_gain = gain.rolling(window=PERIOD).mean()
    avg_loss = loss.rolling(window=PERIOD).mean()

    for i in range(PERIOD, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (PERIOD - 1) + gain.iloc[i]) / PERIOD
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (PERIOD - 1) + loss.iloc[i]) / PERIOD

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    last_rsi = round(df["rsi"].iloc[-1], 2)
    last_price = df["close"].iloc[-1]

    if last_rsi <= 35:
        msg = (
            f"🟢 <b>OPORTUNIDAD BTC</b>\n"
            f"Precio: ${html.escape(str(last_price))}\n"
            f"RSI: {html.escape(str(last_rsi))}\n"
            f"<i>Zona de compra.</i>"
        )
        send_telegram(msg)
    elif last_rsi >= 70:
        msg = (
            f"🔴 <b>ALERTA SOBRECOMPRA</b>\n"
            f"Precio: ${html.escape(str(last_price))}\n"
            f"RSI: {html.escape(str(last_rsi))}\n"
            f"<i>No entres ahora, espera corrección.</i>"
        )
        send_telegram(msg)
    else:
        send_telegram(f"RSI actual: {last_rsi}. en {SYMBOL} Todo tranquilo.")


if __name__ == "__main__":
    calculate_rsi()
