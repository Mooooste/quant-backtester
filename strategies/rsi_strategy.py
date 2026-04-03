"""RSI Mean Reversion Strategy.

BUY when RSI drops below oversold level (market is oversold, expect bounce).
SELL when RSI rises above overbought level (market is overbought, expect drop).
"""

from engine.indicators import rsi


class RSIStrategy:
    name = "RSI Mean Reversion"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def params(self) -> dict:
        return {"period": self.period, "oversold": self.oversold, "overbought": self.overbought}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        rsi_values = rsi(closes, self.period)

        signals = []
        in_position = None

        for i in range(len(klines)):
            if rsi_values[i] is None:
                signals.append({"action": "HOLD"})
                continue

            if rsi_values[i] < self.oversold and in_position != "LONG":
                signals.append({"action": "BUY"})
                in_position = "LONG"
            elif rsi_values[i] > self.overbought and in_position != "SHORT":
                signals.append({"action": "SELL"})
                in_position = "SHORT"
            # Exit when RSI returns to neutral
            elif in_position == "LONG" and rsi_values[i] > 50:
                signals.append({"action": "CLOSE"})
                in_position = None
            elif in_position == "SHORT" and rsi_values[i] < 50:
                signals.append({"action": "CLOSE"})
                in_position = None
            else:
                signals.append({"action": "HOLD"})

        return signals
