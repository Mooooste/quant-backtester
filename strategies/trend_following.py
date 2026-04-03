"""Trend Following Strategy — 200-day Moving Average Regime Filter.

Inspired by Composer's "Four Corners" approach.
Uses a long-term MA to determine market regime:
  - Price > MA → Bull regime → LONG
  - Price < MA → Bear regime → EXIT or SHORT

This is the most common institutional trend strategy and forms the
backbone of CTAs (Commodity Trading Advisors) managing billions.

Enhancement: Uses ATR-based trailing stop to lock in profits during trends.
"""

from engine.indicators import sma, atr


class TrendFollowingStrategy:
    name = "Trend Following (200d MA)"

    def __init__(self, ma_period: int = 200, use_trailing_stop: bool = True,
                 atr_period: int = 14, atr_multiplier: float = 3.0):
        self.ma_period = ma_period
        self.use_trailing_stop = use_trailing_stop
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    @property
    def params(self) -> dict:
        return {"ma_period": self.ma_period, "atr_multiplier": self.atr_multiplier}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        ma = sma(closes, self.ma_period)
        atr_vals = atr(highs, lows, closes, self.atr_period)

        signals = []
        in_position = False
        trailing_stop = 0
        highest_since_entry = 0

        for i in range(len(klines)):
            if ma[i] is None:
                signals.append({"action": "HOLD"})
                continue

            price = closes[i]
            current_atr = atr_vals[i] if atr_vals[i] is not None else 0

            if not in_position:
                # Enter LONG when price is above MA (bull regime)
                if price > ma[i]:
                    signals.append({"action": "BUY"})
                    in_position = True
                    highest_since_entry = price
                    trailing_stop = price - (current_atr * self.atr_multiplier)
                else:
                    signals.append({"action": "HOLD"})
            else:
                # Update trailing stop
                if price > highest_since_entry:
                    highest_since_entry = price
                    if current_atr > 0:
                        trailing_stop = price - (current_atr * self.atr_multiplier)

                # Exit conditions:
                # 1. Price drops below MA (regime change)
                # 2. Trailing stop hit
                if price < ma[i]:
                    signals.append({"action": "CLOSE"})
                    in_position = False
                elif self.use_trailing_stop and price < trailing_stop:
                    signals.append({"action": "CLOSE"})
                    in_position = False
                else:
                    signals.append({"action": "HOLD"})

        return signals
