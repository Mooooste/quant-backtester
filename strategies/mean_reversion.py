"""Mean Reversion Strategy — Z-Score based.

When price deviates too far from its rolling mean (measured by Z-score),
bet on it reverting. This is the core principle behind many quant strategies.

BUY when Z-score < -threshold (price is abnormally low).
SELL when Z-score > +threshold (price is abnormally high).
CLOSE when Z-score returns near 0.
"""

from engine.indicators import sma


class MeanReversionStrategy:
    name = "Mean Reversion (Z-Score)"

    def __init__(self, lookback: int = 30, entry_z: float = 2.0, exit_z: float = 0.5):
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

    @property
    def params(self) -> dict:
        return {"lookback": self.lookback, "entry_z": self.entry_z, "exit_z": self.exit_z}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        signals = []
        in_position = None

        for i in range(len(klines)):
            if i < self.lookback:
                signals.append({"action": "HOLD"})
                continue

            window = closes[i - self.lookback + 1: i + 1]
            mean = sum(window) / len(window)
            std = (sum((x - mean) ** 2 for x in window) / len(window)) ** 0.5

            if std == 0:
                signals.append({"action": "HOLD"})
                continue

            z_score = (closes[i] - mean) / std

            # Price far below mean -> BUY (expect reversion up)
            if z_score < -self.entry_z and in_position != "LONG":
                signals.append({"action": "BUY"})
                in_position = "LONG"
            # Price far above mean -> SELL (expect reversion down)
            elif z_score > self.entry_z and in_position != "SHORT":
                signals.append({"action": "SELL"})
                in_position = "SHORT"
            # Price back to normal -> close
            elif in_position and abs(z_score) < self.exit_z:
                signals.append({"action": "CLOSE"})
                in_position = None
            else:
                signals.append({"action": "HOLD"})

        return signals
