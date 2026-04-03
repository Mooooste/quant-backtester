"""Volatility Breakout Strategy — ATR-based.

Uses Average True Range (ATR) to detect volatility compression,
then trades the breakout when volatility expands.

Logic:
  - When current ATR < rolling average ATR (volatility is compressed)
  - AND price breaks above recent high → BUY (breakout long)
  - AND price breaks below recent low → SELL (breakdown short)
  - Exit when price reverts to the middle of the range or ATR-based stop hit

This is used by many systematic hedge funds. Low-volatility periods
tend to precede large directional moves ("volatility clustering").
"""

from engine.indicators import atr, sma


class VolatilityBreakoutStrategy:
    name = "Volatility Breakout (ATR)"

    def __init__(self, atr_period: int = 14, lookback: int = 20,
                 atr_squeeze_ratio: float = 0.75, atr_stop_mult: float = 2.0):
        self.atr_period = atr_period
        self.lookback = lookback
        self.atr_squeeze_ratio = atr_squeeze_ratio  # ATR < ratio * avg_ATR = squeeze
        self.atr_stop_mult = atr_stop_mult

    @property
    def params(self) -> dict:
        return {
            "atr_period": self.atr_period,
            "lookback": self.lookback,
            "atr_squeeze_ratio": self.atr_squeeze_ratio,
        }

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        atr_vals = atr(highs, lows, closes, self.atr_period)
        avg_atr = sma([v if v is not None else 0 for v in atr_vals], self.lookback)

        signals = []
        in_position = None
        stop_price = 0

        for i in range(len(klines)):
            if i < self.lookback or atr_vals[i] is None or avg_atr[i] is None:
                signals.append({"action": "HOLD"})
                continue

            price = closes[i]
            current_atr = atr_vals[i]

            # Check stop loss
            if in_position == "LONG" and price < stop_price:
                signals.append({"action": "CLOSE"})
                in_position = None
                continue
            elif in_position == "SHORT" and price > stop_price:
                signals.append({"action": "CLOSE"})
                in_position = None
                continue

            if in_position:
                signals.append({"action": "HOLD"})
                continue

            # Detect volatility squeeze
            is_squeeze = current_atr < (avg_atr[i] * self.atr_squeeze_ratio)

            if is_squeeze:
                # Check for breakout
                recent_high = max(highs[i - self.lookback:i])
                recent_low = min(lows[i - self.lookback:i])

                if price > recent_high:
                    signals.append({"action": "BUY"})
                    in_position = "LONG"
                    stop_price = price - (current_atr * self.atr_stop_mult)
                elif price < recent_low:
                    signals.append({"action": "SELL"})
                    in_position = "SHORT"
                    stop_price = price + (current_atr * self.atr_stop_mult)
                else:
                    signals.append({"action": "HOLD"})
            else:
                signals.append({"action": "HOLD"})

        return signals
