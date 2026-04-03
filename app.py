"""Quant Backtester — Web Dashboard for running and comparing strategies."""

from flask import Flask, render_template, request, jsonify
from engine.data_fetcher import fetch_klines, get_available_symbols
from engine.backtester import Backtester
from strategies.sma_crossover import SMACrossover
from strategies.rsi_strategy import RSIStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.mean_reversion import MeanReversionStrategy

app = Flask(__name__)

STRATEGIES = {
    "sma_crossover": {"class": SMACrossover, "params": {"fast_period": 20, "slow_period": 50}},
    "rsi": {"class": RSIStrategy, "params": {"period": 14, "oversold": 30, "overbought": 70}},
    "bollinger": {"class": BollingerStrategy, "params": {"period": 20, "num_std": 2.0}},
    "macd": {"class": MACDStrategy, "params": {"fast": 12, "slow": 26, "signal_period": 9}},
    "mean_reversion": {"class": MeanReversionStrategy, "params": {"lookback": 30, "entry_z": 2.0, "exit_z": 0.5}},
}


@app.route("/")
def index():
    return render_template("index.html",
                           strategies=STRATEGIES,
                           symbols=get_available_symbols())


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    data = request.json
    strategy_key = data.get("strategy", "sma_crossover")
    symbol = data.get("symbol", "BTCUSDT")
    interval = data.get("interval", "1d")
    days = int(data.get("days", 365))
    capital = float(data.get("capital", 100000))
    commission = float(data.get("commission", 0.1))
    params = data.get("params", {})

    # Build strategy with custom params
    strat_info = STRATEGIES.get(strategy_key)
    if not strat_info:
        return jsonify({"error": "Unknown strategy"}), 400

    merged_params = {**strat_info["params"], **params}
    # Convert numeric strings
    for k, v in merged_params.items():
        if isinstance(v, str):
            try:
                merged_params[k] = float(v) if '.' in v else int(v)
            except ValueError:
                pass

    strategy = strat_info["class"](**merged_params)

    # Fetch data
    klines = fetch_klines(symbol, interval, days)
    if not klines or len(klines) < 10:
        return jsonify({"error": f"Insufficient data for {symbol}"}), 400

    # Run backtest
    bt = Backtester(initial_capital=capital, commission_pct=commission)
    result = bt.run(strategy, klines, symbol, interval)

    return jsonify(result.to_dict())


@app.route("/api/compare", methods=["POST"])
def api_compare():
    """Run multiple strategies on the same data and compare."""
    data = request.json
    strategy_keys = data.get("strategies", list(STRATEGIES.keys()))
    symbol = data.get("symbol", "BTCUSDT")
    interval = data.get("interval", "1d")
    days = int(data.get("days", 365))
    capital = float(data.get("capital", 100000))

    klines = fetch_klines(symbol, interval, days)
    if not klines or len(klines) < 10:
        return jsonify({"error": "Insufficient data"}), 400

    bt = Backtester(initial_capital=capital)
    results = []

    for key in strategy_keys:
        strat_info = STRATEGIES.get(key)
        if not strat_info:
            continue
        strategy = strat_info["class"](**strat_info["params"])
        result = bt.run(strategy, klines, symbol, interval)
        results.append(result.to_dict())

    return jsonify({"results": results, "klines_count": len(klines)})


if __name__ == "__main__":
    print("\n  Quant Backtester")
    print("  http://localhost:5002\n")
    app.run(host="0.0.0.0", port=5002, debug=True)
