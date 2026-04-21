# Quant Backtester

A professional-grade quantitative trading backtesting engine with a web dashboard. Built for evaluating trading strategies against real historical market data from Binance.

Designed for a quant research workflow

## Features

- **5 Built-in Strategies** — SMA Crossover, RSI Mean Reversion, Bollinger Bands, MACD Crossover, Z-Score Mean Reversion
- **Real Market Data** — Fetches historical OHLCV from Binance API (20+ trading pairs)
- **Full Analytics Suite** — Sharpe ratio, Sortino ratio, Calmar ratio, max drawdown, win rate, profit factor
- **Interactive Web Dashboard** — Run backtests, visualize equity curves, compare strategies
- **Trade-Level Detail** — Every entry/exit logged with P&L, bars held, and signal markers
- **Strategy Comparison** — Run all strategies side-by-side on the same data
- **Configurable Parameters** — Adjust strategy params, commission, slippage, timeframe, and capital
- **Commission & Slippage** — Realistic execution modeling

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5002** in your browser.

## Strategies

| Strategy | Type | Signal |
|---|---|---|
| SMA Crossover | Trend Following | Fast SMA crosses slow SMA |
| RSI Mean Reversion | Mean Reversion | RSI oversold/overbought levels |
| Bollinger Bands | Mean Reversion | Price touches upper/lower bands |
| MACD Crossover | Momentum | MACD line crosses signal line |
| Z-Score Mean Reversion | Statistical | Price deviates N std from rolling mean |

## Performance Metrics

- **Total Return** — Strategy profit/loss percentage
- **Sharpe Ratio** — Risk-adjusted return (annualized)
- **Sortino Ratio** — Downside risk-adjusted return
- **Calmar Ratio** — Return / Max Drawdown
- **Max Drawdown** — Worst peak-to-trough decline
- **Win Rate** — Percentage of profitable trades
- **Profit Factor** — Gross profit / Gross loss
- **Alpha** — Excess return vs. Buy & Hold

## Project Structure

```
quant-backtester/
├── app.py                          # Flask web server
├── engine/
│   ├── backtester.py               # Core backtesting engine
│   ├── data_fetcher.py             # Binance API data fetching
│   └── indicators.py               # Technical indicators (SMA, EMA, RSI, MACD, BB, ATR)
├── strategies/
│   ├── sma_crossover.py            # SMA Crossover strategy
│   ├── rsi_strategy.py             # RSI Mean Reversion
│   ├── bollinger_strategy.py       # Bollinger Bands
│   ├── macd_strategy.py            # MACD Crossover
│   └── mean_reversion.py           # Z-Score Mean Reversion
├── templates/
│   └── index.html                  # Web dashboard
├── static/
│   ├── css/style.css
│   └── js/app.js
└── requirements.txt
```

## API

```
POST /api/backtest     — Run a single strategy backtest
POST /api/compare      — Compare all strategies on same data
```

## Adding Custom Strategies

Create a new file in `strategies/` implementing:

```python
class MyStrategy:
    name = "My Strategy"

    def generate_signals(self, klines: list[dict]) -> list[dict]:
        # Return list of {"action": "BUY"/"SELL"/"CLOSE"/"HOLD"}
        ...
```

Then register it in `app.py` under `STRATEGIES`.

## License

MIT
