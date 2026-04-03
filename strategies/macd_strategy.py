"""MACD Crossover Strategy.

BUY when MACD line crosses above signal line (bullish momentum).
SELL when MACD line crosses below signal line (bearish momentum).
Uses histogram direction for confirmation.
"""

from engine.indicators import macd


class MACDStrategy:
    name = "MACD Crossover"

    def __init__(self, fast: int = 12, slow: int = 26, signal_period: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period

    @property
    def params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "signal_period": self.signal_period}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        macd_line, signal_line, histogram = macd(closes, self.fast, self.slow, self.signal_period)

        signals = []
        for i in range(len(klines)):
            if i < 1 or macd_line[i] is None or signal_line[i] is None \
               or macd_line[i - 1] is None or signal_line[i - 1] is None:
                signals.append({"action": "HOLD"})
                continue

            # MACD crosses above signal -> BUY
            if macd_line[i - 1] <= signal_line[i - 1] and macd_line[i] > signal_line[i]:
                signals.append({"action": "BUY"})
            # MACD crosses below signal -> SELL
            elif macd_line[i - 1] >= signal_line[i - 1] and macd_line[i] < signal_line[i]:
                signals.append({"action": "SELL"})
            else:
                signals.append({"action": "HOLD"})

        return signals
