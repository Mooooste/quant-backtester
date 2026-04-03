"""Daily Return Mean Reversion — from Composer's single-asset approach.

Core idea: When a coin pumps too much in a single day (>threshold%),
it's likely to revert. Go short. When it dumps too much, go long.

This exploits the well-documented "overnight reversal" effect in crypto
where large daily moves tend to partially reverse.

Parameters calibrated for crypto's higher volatility vs equities.
"""


class DailyReturnReversion:
    name = "Daily Return Reversion"

    def __init__(self, long_threshold: float = -3.0, short_threshold: float = 3.0,
                 hold_bars: int = 3):
        self.long_threshold = long_threshold    # Buy when daily return < this
        self.short_threshold = short_threshold  # Sell when daily return > this
        self.hold_bars = hold_bars              # Hold for N bars then close

    @property
    def params(self) -> dict:
        return {
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "hold_bars": self.hold_bars,
        }

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        signals = []
        in_position = None
        bars_in_trade = 0

        for i in range(len(klines)):
            if i < 1:
                signals.append({"action": "HOLD"})
                continue

            daily_return = ((closes[i] - closes[i - 1]) / closes[i - 1]) * 100

            if in_position:
                bars_in_trade += 1
                # Time-based exit
                if bars_in_trade >= self.hold_bars:
                    signals.append({"action": "CLOSE"})
                    in_position = None
                    bars_in_trade = 0
                else:
                    signals.append({"action": "HOLD"})
            else:
                # Big drop -> buy (expect bounce)
                if daily_return < self.long_threshold:
                    signals.append({"action": "BUY"})
                    in_position = "LONG"
                    bars_in_trade = 0
                # Big pump -> sell (expect reversion)
                elif daily_return > self.short_threshold:
                    signals.append({"action": "SELL"})
                    in_position = "SHORT"
                    bars_in_trade = 0
                else:
                    signals.append({"action": "HOLD"})

        return signals
