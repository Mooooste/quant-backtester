"""Fetch historical OHLCV data from Binance public API."""

import json
import time
import requests
import os
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BINANCE_BASE = "https://api.binance.com/api/v3"

# Map friendly interval names to Binance API values
INTERVALS = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
}

# Milliseconds per interval (for pagination)
INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000,
}


def fetch_klines(symbol: str = "BTCUSDT", interval: str = "1d",
                 days: int = 365) -> list[dict]:
    """Fetch historical klines (candlesticks) from Binance.

    Returns list of dicts with: timestamp, open, high, low, close, volume.
    Automatically paginates for large date ranges.
    """
    cache_key = f"{symbol}_{interval}_{days}d"
    cache_file = DATA_DIR / f"{cache_key}.json"

    # Check cache (valid for 1 hour)
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 3600:
            return json.loads(cache_file.read_text())

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (days * 86_400_000)
    limit = 1000  # Binance max per request

    all_klines = []
    current_start = start_ms

    while current_start < end_ms:
        try:
            r = requests.get(
                f"{BINANCE_BASE}/klines",
                params={
                    "symbol": symbol,
                    "interval": INTERVALS.get(interval, interval),
                    "startTime": current_start,
                    "endTime": end_ms,
                    "limit": limit,
                },
                timeout=15,
            )
            r.raise_for_status()
            raw = r.json()

            if not raw:
                break

            for k in raw:
                all_klines.append({
                    "timestamp": k[0],
                    "date": datetime.utcfromtimestamp(k[0] / 1000).strftime("%Y-%m-%d %H:%M"),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })

            # Move start to after the last candle
            current_start = raw[-1][0] + INTERVAL_MS.get(interval, 86_400_000)

            # Rate limit: be polite to Binance
            time.sleep(0.2)

        except Exception as e:
            print(f"Fetch error: {e}")
            break

    # Cache results
    if all_klines:
        cache_file.write_text(json.dumps(all_klines))

    return all_klines


def get_available_symbols() -> list[str]:
    """Get popular trading pairs."""
    return [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
        "MATICUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT",
        "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "TONUSDT",
    ]
