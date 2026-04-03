"""SMA Crossover Strategy — The classic trend-following approach.

BUY when fast SMA crosses above slow SMA (golden cross).
SELL when fast SMA crosses below slow SMA (death cross).
"""

from engine.indicators import sma


class SMACrossover:
    name = "SMA Crossover"

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period

    @property
    def params(self) -> dict:
        return {"fast_period": self.fast_period, "slow_period": self.slow_period}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        fast_sma = sma(closes, self.fast_period)
        slow_sma = sma(closes, self.slow_period)

        signals = []
        for i in range(len(klines)):
            if i < 1 or fast_sma[i] is None or slow_sma[i] is None \
               or fast_sma[i - 1] is None or slow_sma[i - 1] is None:
                signals.append({"action": "HOLD"})
                continue

            # Golden cross: fast crosses above slow
            if fast_sma[i - 1] <= slow_sma[i - 1] and fast_sma[i] > slow_sma[i]:
                signals.append({"action": "BUY"})
            # Death cross: fast crosses below slow
            elif fast_sma[i - 1] >= slow_sma[i - 1] and fast_sma[i] < slow_sma[i]:
                signals.append({"action": "SELL"})
            else:
                signals.append({"action": "HOLD"})

        return signals
