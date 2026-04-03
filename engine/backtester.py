"""Core backtesting engine — runs strategies against historical data."""

from dataclasses import dataclass, field
from datetime import datetime
import math


@dataclass
class TradeRecord:
    """A single completed trade (entry + exit)."""
    entry_date: str
    exit_date: str
    side: str           # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    bars_held: int


@dataclass
class Position:
    """Currently open position."""
    side: str
    entry_price: float
    entry_date: str
    quantity: float
    entry_bar: int


@dataclass
class BacktestResult:
    """Complete backtest output."""
    strategy_name: str
    symbol: str
    interval: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    buy_hold_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    max_drawdown_pct: float
    max_drawdown_duration: int  # bars
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    avg_bars_held: float
    equity_curve: list = field(default_factory=list)
    drawdown_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    signals: list = field(default_factory=list)  # for charting

    @staticmethod
    def _safe(v, decimals=2):
        """Convert inf/nan to JSON-safe values."""
        if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
            return 9999.99 if v > 0 else -9999.99
        return round(v, decimals)

    def to_dict(self) -> dict:
        s = self._safe
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "interval": self.interval,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_capital": s(self.final_capital),
            "total_return_pct": s(self.total_return_pct),
            "buy_hold_return_pct": s(self.buy_hold_return_pct),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": s(self.win_rate),
            "avg_win_pct": s(self.avg_win_pct),
            "avg_loss_pct": s(self.avg_loss_pct),
            "profit_factor": s(self.profit_factor),
            "max_drawdown_pct": s(self.max_drawdown_pct),
            "max_drawdown_duration": self.max_drawdown_duration,
            "sharpe_ratio": s(self.sharpe_ratio, 3),
            "sortino_ratio": s(self.sortino_ratio, 3),
            "calmar_ratio": s(self.calmar_ratio, 3),
            "avg_bars_held": s(self.avg_bars_held, 1),
            "equity_curve": self.equity_curve,
            "drawdown_curve": self.drawdown_curve,
            "trades": [
                {
                    "entry_date": t.entry_date, "exit_date": t.exit_date,
                    "side": t.side, "entry_price": round(t.entry_price, 2),
                    "exit_price": round(t.exit_price, 2),
                    "pnl": round(t.pnl, 2), "pnl_pct": round(t.pnl_pct, 2),
                    "bars_held": t.bars_held,
                }
                for t in self.trades
            ],
            "signals": self.signals,
        }


class Backtester:
    """Run a strategy against historical kline data."""

    def __init__(self, initial_capital: float = 100_000,
                 commission_pct: float = 0.1,
                 slippage_pct: float = 0.05):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct / 100  # e.g. 0.1% -> 0.001
        self.slippage_pct = slippage_pct / 100

    def run(self, strategy, klines: list[dict], symbol: str = "",
            interval: str = "") -> BacktestResult:
        """Execute the backtest.

        strategy must implement:
            - name: str
            - generate_signals(klines) -> list of {"action": "BUY"/"SELL"/"HOLD", ...}
        """
        if len(klines) < 2:
            raise ValueError("Need at least 2 data points")

        signals = strategy.generate_signals(klines)
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = []
        signal_markers = []

        closes = [k["close"] for k in klines]

        for i, (kline, signal) in enumerate(zip(klines, signals)):
            price = kline["close"]
            action = signal.get("action", "HOLD")

            # Calculate current equity
            if position:
                if position.side == "LONG":
                    unrealized = (price - position.entry_price) * position.quantity
                else:
                    unrealized = (position.entry_price - price) * position.quantity
                equity = capital + unrealized
            else:
                equity = capital

            equity_curve.append({
                "date": kline["date"],
                "equity": round(equity, 2),
                "price": price,
            })

            # ── Execute signals ─────────────────────────────

            if action == "BUY" and position is None:
                # Open long position
                adj_price = price * (1 + self.slippage_pct)
                commission = capital * self.commission_pct
                qty = (capital - commission) / adj_price
                position = Position("LONG", adj_price, kline["date"], qty, i)
                capital -= commission
                signal_markers.append({"date": kline["date"], "type": "BUY", "price": price})

            elif action == "SELL" and position is None:
                # Open short position
                adj_price = price * (1 - self.slippage_pct)
                commission = capital * self.commission_pct
                qty = (capital - commission) / adj_price
                position = Position("SHORT", adj_price, kline["date"], qty, i)
                capital -= commission
                signal_markers.append({"date": kline["date"], "type": "SELL", "price": price})

            elif action == "CLOSE" and position is not None:
                # Close position
                if position.side == "LONG":
                    adj_price = price * (1 - self.slippage_pct)
                    pnl = (adj_price - position.entry_price) * position.quantity
                else:
                    adj_price = price * (1 + self.slippage_pct)
                    pnl = (position.entry_price - adj_price) * position.quantity

                commission = abs(pnl) * self.commission_pct
                pnl -= commission
                capital += position.quantity * position.entry_price + pnl
                pnl_pct = (pnl / (position.quantity * position.entry_price)) * 100

                trades.append(TradeRecord(
                    entry_date=position.entry_date,
                    exit_date=kline["date"],
                    side=position.side,
                    entry_price=position.entry_price,
                    exit_price=adj_price,
                    quantity=position.quantity,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    bars_held=i - position.entry_bar,
                ))
                signal_markers.append({"date": kline["date"], "type": "CLOSE", "price": price})
                position = None

            # Handle BUY when SHORT or SELL when LONG (flip)
            elif action == "BUY" and position and position.side == "SHORT":
                # Close short first
                adj_price = price * (1 + self.slippage_pct)
                pnl = (position.entry_price - adj_price) * position.quantity
                commission = abs(pnl) * self.commission_pct
                pnl -= commission
                capital += position.quantity * position.entry_price + pnl

                trades.append(TradeRecord(
                    entry_date=position.entry_date, exit_date=kline["date"],
                    side="SHORT", entry_price=position.entry_price,
                    exit_price=adj_price, quantity=position.quantity,
                    pnl=pnl,
                    pnl_pct=(pnl / (position.quantity * position.entry_price)) * 100,
                    bars_held=i - position.entry_bar,
                ))

                # Open long
                adj_price = price * (1 + self.slippage_pct)
                comm2 = capital * self.commission_pct
                qty = (capital - comm2) / adj_price
                position = Position("LONG", adj_price, kline["date"], qty, i)
                capital -= comm2
                signal_markers.append({"date": kline["date"], "type": "BUY", "price": price})

            elif action == "SELL" and position and position.side == "LONG":
                # Close long first
                adj_price = price * (1 - self.slippage_pct)
                pnl = (adj_price - position.entry_price) * position.quantity
                commission = abs(pnl) * self.commission_pct
                pnl -= commission
                capital += position.quantity * position.entry_price + pnl

                trades.append(TradeRecord(
                    entry_date=position.entry_date, exit_date=kline["date"],
                    side="LONG", entry_price=position.entry_price,
                    exit_price=adj_price, quantity=position.quantity,
                    pnl=pnl,
                    pnl_pct=(pnl / (position.quantity * position.entry_price)) * 100,
                    bars_held=i - position.entry_bar,
                ))

                # Open short
                adj_price = price * (1 - self.slippage_pct)
                comm2 = capital * self.commission_pct
                qty = (capital - comm2) / adj_price
                position = Position("SHORT", adj_price, kline["date"], qty, i)
                capital -= comm2
                signal_markers.append({"date": kline["date"], "type": "SELL", "price": price})

        # Close any remaining position at last price
        if position:
            price = closes[-1]
            if position.side == "LONG":
                pnl = (price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - price) * position.quantity
            capital += position.quantity * position.entry_price + pnl
            trades.append(TradeRecord(
                entry_date=position.entry_date, exit_date=klines[-1]["date"],
                side=position.side, entry_price=position.entry_price,
                exit_price=price, quantity=position.quantity,
                pnl=pnl,
                pnl_pct=(pnl / (position.quantity * position.entry_price)) * 100,
                bars_held=len(klines) - 1 - position.entry_bar,
            ))

        # ── Compute analytics ───────────────────────────
        return self._compute_results(
            strategy.name, symbol, interval, klines, capital,
            equity_curve, trades, signal_markers,
        )

    def _compute_results(self, name, symbol, interval, klines, final_capital,
                         equity_curve, trades, signals) -> BacktestResult:

        closes = [k["close"] for k in klines]
        buy_hold_ret = ((closes[-1] - closes[0]) / closes[0]) * 100
        total_ret = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = (len(wins) / len(trades) * 100) if trades else 0

        avg_win = (sum(t.pnl_pct for t in wins) / len(wins)) if wins else 0
        avg_loss = (sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        avg_bars = (sum(t.bars_held for t in trades) / len(trades)) if trades else 0

        # Drawdown
        equities = [e["equity"] for e in equity_curve]
        peak = equities[0]
        max_dd = 0
        max_dd_duration = 0
        dd_start = 0
        drawdown_curve = []

        for i, eq in enumerate(equities):
            if eq > peak:
                peak = eq
                dd_start = i
            dd = ((peak - eq) / peak) * 100
            drawdown_curve.append({"date": equity_curve[i]["date"], "drawdown": round(-dd, 2)})
            if dd > max_dd:
                max_dd = dd
                max_dd_duration = i - dd_start

        # Sharpe & Sortino (annualized, assuming daily data)
        returns = []
        for i in range(1, len(equities)):
            returns.append((equities[i] - equities[i - 1]) / equities[i - 1])

        if returns:
            avg_ret = sum(returns) / len(returns)
            std_ret = (sum((r - avg_ret) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0

            downside = [r for r in returns if r < 0]
            down_std = (sum(r ** 2 for r in downside) / len(downside)) ** 0.5 if downside else 0
            sortino = (avg_ret / down_std * math.sqrt(252)) if down_std > 0 else 0
        else:
            sharpe = 0
            sortino = 0

        annual_ret = total_ret / max(len(klines) / 252, 1)
        calmar = (annual_ret / max_dd) if max_dd > 0 else 0

        return BacktestResult(
            strategy_name=name,
            symbol=symbol,
            interval=interval,
            start_date=klines[0]["date"],
            end_date=klines[-1]["date"],
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return_pct=total_ret,
            buy_hold_return_pct=buy_hold_ret,
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            avg_win_pct=avg_win,
            avg_loss_pct=avg_loss,
            profit_factor=profit_factor,
            max_drawdown_pct=max_dd,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            avg_bars_held=avg_bars,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            trades=trades,
            signals=signals,
        )
