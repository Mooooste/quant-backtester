"""Market Regime Detection Strategy — Inspired by Composer's "Four Corners".

Classifies market into 4 regimes using dual moving averages and momentum:
  1. STRONG BULL  — Price > fast MA > slow MA, momentum positive
  2. MILD BULL    — Price > slow MA but below fast MA (weakening trend)
  3. MILD BEAR    — Price < slow MA but above fast MA (recovery possible)
  4. STRONG BEAR  — Price < fast MA < slow MA, momentum negative

Position sizing varies by regime:
  - Strong Bull:  100% long
  - Mild Bull:    50% long (reduced exposure)
  - Mild Bear:    No position (cash)
  - Strong Bear:  Short position

Uses RSI as momentum filter for confirmation.
"""

from engine.indicators import sma, ema, rsi


class RegimeDetectionStrategy:
    name = "Regime Detection (4-State)"

    def __init__(self, fast_ma: int = 50, slow_ma: int = 200,
                 rsi_period: int = 14, rsi_bull: float = 50, rsi_bear: float = 50):
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.rsi_period = rsi_period
        self.rsi_bull = rsi_bull
        self.rsi_bear = rsi_bear

    @property
    def params(self) -> dict:
        return {"fast_ma": self.fast_ma, "slow_ma": self.slow_ma}

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        closes = [k["close"] for k in klines]
        fast = ema(closes, self.fast_ma)
        slow = sma(closes, self.slow_ma)
        rsi_vals = rsi(closes, self.rsi_period)

        signals = []
        current_regime = None
        in_position = None

        for i in range(len(klines)):
            if fast[i] is None or slow[i] is None or rsi_vals[i] is None:
                signals.append({"action": "HOLD"})
                continue

            price = closes[i]
            r = rsi_vals[i]

            # Classify regime
            if price > fast[i] and fast[i] > slow[i] and r > self.rsi_bull:
                regime = "STRONG_BULL"
            elif price > slow[i]:
                regime = "MILD_BULL"
            elif price < fast[i] and fast[i] < slow[i] and r < self.rsi_bear:
                regime = "STRONG_BEAR"
            else:
                regime = "MILD_BEAR"

            # Generate signal based on regime transition
            if regime != current_regime:
                current_regime = regime

                if regime == "STRONG_BULL" and in_position != "LONG":
                    signals.append({"action": "BUY"})
                    in_position = "LONG"
                elif regime == "STRONG_BEAR" and in_position != "SHORT":
                    signals.append({"action": "SELL"})
                    in_position = "SHORT"
                elif regime in ("MILD_BEAR", "MILD_BULL") and in_position is not None:
                    signals.append({"action": "CLOSE"})
                    in_position = None
                else:
                    signals.append({"action": "HOLD"})
            else:
                signals.append({"action": "HOLD"})

        return signals
