"""Bollinger Band Breakout / Mean Reversion Strategy.

BUY when price touches lower band (oversold bounce).
SELL when price touches upper band (overbought reversal).
CLOSE when price returns to middle band.
"""

from engine.indicators import bollinger_bands


class BollingerStrategy:
    name = "Bollinger Bands"

    def __init__(self, period: int = 20, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std

    @property
    def params(self) -> dict:
        return {"period": self.period, "num_std": self.num_std}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        upper, middle, lower = bollinger_bands(closes, self.period, self.num_std)

        signals = []
        in_position = None

        for i in range(len(klines)):
            if upper[i] is None or lower[i] is None:
                signals.append({"action": "HOLD"})
                continue

            price = closes[i]

            # Price touches lower band -> BUY (mean reversion upward)
            if price <= lower[i] and in_position != "LONG":
                signals.append({"action": "BUY"})
                in_position = "LONG"
            # Price touches upper band -> SELL (mean reversion downward)
            elif price >= upper[i] and in_position != "SHORT":
                signals.append({"action": "SELL"})
                in_position = "SHORT"
            # Price returns to middle -> close position
            elif in_position and abs(price - middle[i]) / middle[i] < 0.005:
                signals.append({"action": "CLOSE"})
                in_position = None
            else:
                signals.append({"action": "HOLD"})

        return signals
