#!/usr/bin/env python3
"""
TradingView Webhook → Telegram Bot Bridge.

Receives webhook alerts from TradingView and forwards them to Telegram.

Setup:
    1. Create Telegram bot via @BotFather → get TOKEN
    2. Get your Chat ID via @userinfobot → get CHAT_ID
    3. Set environment variables or edit .env file
    4. Deploy this script (Railway / Render / VPS)
    5. Set TradingView alert webhook URL to: https://your-server.com/webhook

Usage (local testing):
    pip install -r requirements.txt
    export TELEGRAM_TOKEN="your_bot_token"
    export TELEGRAM_CHAT_ID="your_chat_id"
    python bot.py

Usage (production):
    See TELEGRAM_SETUP.md for full deployment guide
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "trade1000_secret_key")
PORT = int(os.environ.get("PORT", 5000))

# Rate limiting: max 1 message per N seconds (avoid spam)
MIN_MESSAGE_INTERVAL = 10
last_message_time = 0

# ============================================================================
# APP SETUP
# ============================================================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ============================================================================
# TELEGRAM FUNCTIONS
# ============================================================================

def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to Telegram."""
    global last_message_time

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set!")
        return False

    # Rate limiting
    now = time.time()
    if now - last_message_time < MIN_MESSAGE_INTERVAL:
        log.warning("Rate limited — skipping message")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            last_message_time = now
            log.info("Telegram message sent successfully")
            return True
        else:
            log.error(f"Telegram API error: {resp.status_code} — {resp.text}")
            return False
    except requests.RequestException as e:
        log.error(f"Failed to send Telegram message: {e}")
        return False


def format_signal_message(data: dict) -> str:
    """Format the webhook payload into a readable Telegram message."""

    signal = data.get("signal", "UNKNOWN").upper()
    ticker = data.get("ticker", "N/A")
    price = data.get("price", "N/A")
    timeframe = data.get("timeframe", "5M")
    timestamp = data.get("time", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    # Signal emoji and direction
    if "LONG" in signal:
        emoji = "\U0001F7E2"  # green circle
        direction = "LONG"
        action = "BUY"
    elif "SHORT" in signal:
        emoji = "\U0001F534"  # red circle
        direction = "SHORT"
        action = "SELL"
    elif "VOLUME" in signal:
        emoji = "\U0001F4CA"  # chart
        direction = "VOLUME SPIKE"
        action = "WATCH"
    else:
        emoji = "\U0001F514"  # bell
        direction = signal
        action = "CHECK"

    # Build message
    sl = data.get("sl", "—")
    tp1 = data.get("tp1", "—")
    tp2 = data.get("tp2", "—")
    tp3 = data.get("tp3", "—")
    rsi = data.get("rsi", "—")
    atr = data.get("atr", "—")
    trend_1h = data.get("trend_1h", "—")
    momentum_15m = data.get("momentum_15m", "—")

    msg = f"""{emoji} <b>{direction} SIGNAL — {ticker}</b>

<b>Action:</b> {action}
<b>Price:</b> ${price}
<b>Time:</b> {timestamp}
<b>Timeframe:</b> {timeframe}

<b>Conditions:</b>
  1H Trend: {trend_1h}
  15M Momentum: {momentum_15m}
  RSI: {rsi}

<b>Levels:</b>
  Stop Loss: ${sl}
  TP1 (50%): ${tp1}
  TP2 (30%): ${tp2}
  TP3 (20%): ${tp3}

<b>ATR:</b> {atr}

\U000026A0 <i>Проверь чеклист перед входом!</i>"""

    return msg


def format_simple_message(data: dict) -> str:
    """Format a simple alert message (from TradingView default format)."""

    text = data.get("message", data.get("text", ""))
    ticker = data.get("ticker", "")
    price = data.get("price", "")

    if text:
        return f"\U0001F514 <b>Alert: {ticker}</b>\n\n{text}\n\nPrice: ${price}"

    return f"\U0001F514 <b>Alert</b>\n\n{json.dumps(data, indent=2)}"


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.route("/", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "TradingView → Telegram Bridge",
        "telegram_configured": bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID),
    })


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive TradingView webhook and forward to Telegram.

    TradingView sends POST with JSON or plain text body.
    """
    log.info(f"Webhook received from {request.remote_addr}")

    # Parse payload
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        # TradingView sometimes sends plain text
        raw = request.get_data(as_text=True)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            data = {"message": raw}

    log.info(f"Payload: {json.dumps(data, default=str)[:500]}")

    # Optional: verify webhook secret
    secret = data.get("secret", "")
    if WEBHOOK_SECRET and secret and secret != WEBHOOK_SECRET:
        log.warning("Invalid webhook secret!")
        return jsonify({"error": "unauthorized"}), 401

    # Format and send message
    if data.get("signal"):
        message = format_signal_message(data)
    else:
        message = format_simple_message(data)

    success = send_telegram(message)

    if success:
        return jsonify({"status": "sent"}), 200
    else:
        return jsonify({"status": "failed"}), 500


@app.route("/test", methods=["GET"])
def test():
    """Send a test message to verify the setup works."""
    msg = """\U00002705 <b>Test Message</b>

TradingView → Telegram bridge is working!
Bot is ready to receive trading signals.

Time: """ + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    success = send_telegram(msg)
    if success:
        return jsonify({"status": "test message sent"}), 200
    else:
        return jsonify({"status": "failed", "check": "TELEGRAM_TOKEN and TELEGRAM_CHAT_ID"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("TradingView → Telegram Bridge")
    log.info("=" * 50)

    if not TELEGRAM_TOKEN:
        log.warning("TELEGRAM_TOKEN not set! Messages won't be sent.")
    if not TELEGRAM_CHAT_ID:
        log.warning("TELEGRAM_CHAT_ID not set! Messages won't be sent.")

    log.info(f"Starting server on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
