const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const fmt = {
    usd: n => "$" + n.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2}),
    pct: n => (n >= 0 ? "+" : "") + n.toFixed(2) + "%",
    num: n => n.toLocaleString("en-US", {maximumFractionDigits:2}),
};

const STRAT_PARAMS = {
    sma_crossover: [{key:"fast_period",label:"Fast SMA",val:20},{key:"slow_period",label:"Slow SMA",val:50}],
    rsi: [{key:"period",label:"RSI Period",val:14},{key:"oversold",label:"Oversold",val:30},{key:"overbought",label:"Overbought",val:70}],
    bollinger: [{key:"period",label:"BB Period",val:20},{key:"num_std",label:"Std Dev",val:2.0}],
    macd: [{key:"fast",label:"Fast EMA",val:12},{key:"slow",label:"Slow EMA",val:26},{key:"signal_period",label:"Signal",val:9}],
    mean_reversion: [{key:"lookback",label:"Lookback",val:30},{key:"entry_z",label:"Entry Z",val:2.0},{key:"exit_z",label:"Exit Z",val:0.5}],
    trend_following: [{key:"ma_period",label:"MA Period",val:200},{key:"atr_multiplier",label:"ATR Stop ×",val:3.0}],
    daily_reversion: [{key:"long_threshold",label:"Long Threshold %",val:-3.0},{key:"short_threshold",label:"Short Threshold %",val:3.0},{key:"hold_bars",label:"Hold Bars",val:3}],
    regime_detection: [{key:"fast_ma",label:"Fast MA",val:50},{key:"slow_ma",label:"Slow MA",val:200}],
    volatility_breakout: [{key:"atr_period",label:"ATR Period",val:14},{key:"lookback",label:"Lookback",val:20},{key:"atr_squeeze_ratio",label:"Squeeze Ratio",val:0.75}],
};

let equityChart=null, drawdownChart=null, signalsChart=null, compareEquityChart=null;
let lastResult = null;

// Tab nav
$$(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
        $$(".nav-item").forEach(i => i.classList.remove("active"));
        $$(".tab-content").forEach(t => t.classList.remove("active"));
        item.classList.add("active");
        $(`#tab-${item.dataset.tab}`).classList.add("active");
        $("#page-title").textContent = item.querySelector("span").textContent;
    });
});

// Strategy params
function renderStratParams() {
    const key = $("#cfg-strategy").value;
    const params = STRAT_PARAMS[key] || [];
    $("#strategy-params").innerHTML = params.map(p => `
        <div class="form-group">
            <label>${p.label}</label>
            <input type="number" step="any" value="${p.val}" data-param="${p.key}">
        </div>
    `).join("");
}
$("#cfg-strategy").addEventListener("change", renderStratParams);
renderStratParams();

// Run single backtest
$("#btn-run").addEventListener("click", async () => {
    const btn = $("#btn-run");
    btn.disabled = true; btn.textContent = "Running...";
    $("#status-badge").className = "status-badge status-running";
    $("#status-badge").textContent = "Running...";

    const params = {};
    $$("#strategy-params input").forEach(inp => {
        params[inp.dataset.param] = parseFloat(inp.value);
    });

    try {
        const res = await fetch("/api/backtest", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                strategy: $("#cfg-strategy").value,
                symbol: $("#cfg-symbol").value,
                interval: $("#cfg-interval").value,
                days: parseInt($("#cfg-days").value),
                capital: parseFloat($("#cfg-capital").value),
                commission: parseFloat($("#cfg-commission").value),
                params,
            }),
        });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        lastResult = data;
        renderResults(data);
        renderTradeLog(data.trades);
        $("#results-container").style.display = "block";
        $("#status-badge").className = "status-badge status-done";
        $("#status-badge").textContent = "Complete";
    } catch(e) {
        alert("Backtest failed: " + e.message);
    } finally {
        btn.disabled = false; btn.textContent = "Run Backtest";
    }
});

function renderResults(r) {
    // Summary cards
    const retClass = r.total_return_pct >= 0 ? "positive" : "negative";
    $("#r-return").textContent = fmt.pct(r.total_return_pct);
    $("#r-return").className = `card-value ${retClass}`;
    const alpha = r.total_return_pct - r.buy_hold_return_pct;
    $("#r-vs-hold").textContent = `B&H: ${fmt.pct(r.buy_hold_return_pct)} | Alpha: ${fmt.pct(alpha)}`;
    $("#r-vs-hold").className = `card-sub ${alpha >= 0 ? "positive" : "negative"}`;

    $("#r-sharpe").textContent = r.sharpe_ratio.toFixed(2);
    $("#r-sharpe").className = `card-value ${r.sharpe_ratio >= 1 ? "positive" : r.sharpe_ratio >= 0 ? "" : "negative"}`;
    $("#r-sortino").textContent = `Sortino: ${r.sortino_ratio.toFixed(2)}`;

    $("#r-winrate").textContent = r.win_rate.toFixed(1) + "%";
    $("#r-winrate").className = `card-value ${r.win_rate >= 50 ? "positive" : "negative"}`;
    $("#r-trades").textContent = `${r.total_trades} trades (${r.winning_trades}W / ${r.losing_trades}L)`;

    $("#r-drawdown").textContent = "-" + r.max_drawdown_pct.toFixed(2) + "%";
    $("#r-drawdown").className = "card-value negative";
    $("#r-calmar").textContent = `Calmar: ${r.calmar_ratio.toFixed(2)}`;

    // Metrics grid
    const metrics = [
        {label:"Final Capital", value: fmt.usd(r.final_capital)},
        {label:"Initial Capital", value: fmt.usd(r.initial_capital)},
        {label:"Avg Win", value: fmt.pct(r.avg_win_pct)},
        {label:"Avg Loss", value: fmt.pct(r.avg_loss_pct)},
        {label:"Profit Factor", value: r.profit_factor === Infinity ? "∞" : r.profit_factor.toFixed(2)},
        {label:"Avg Bars Held", value: r.avg_bars_held.toFixed(1)},
        {label:"Max DD Duration", value: r.max_drawdown_duration + " bars"},
        {label:"Period", value: r.start_date + " → " + r.end_date},
    ];
    $("#metrics-grid").innerHTML = metrics.map(m => `
        <div class="metric-item">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}</div>
        </div>
    `).join("");

    renderEquityChart(r);
    renderDrawdownChart(r);
    renderSignalsChart(r);
}

function renderEquityChart(r) {
    const ctx = $("#equity-chart").getContext("2d");
    if (equityChart) equityChart.destroy();

    // Thin out data for performance
    const eq = thin(r.equity_curve, 500);

    equityChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: eq.map(e => e.date),
            datasets: [{
                label: "Strategy Equity",
                data: eq.map(e => e.equity),
                borderColor: "#8b5cf6",
                backgroundColor: "rgba(139,92,246,0.1)",
                fill: true, tension: 0.2, pointRadius: 0, borderWidth: 2,
            }, {
                label: "Buy & Hold",
                data: eq.map(e => (e.price / r.equity_curve[0].price) * r.initial_capital),
                borderColor: "#5a6580",
                borderDash: [5,5],
                fill: false, tension: 0.2, pointRadius: 0, borderWidth: 1.5,
            }],
        },
        options: chartOpts("$"),
    });
}

function renderDrawdownChart(r) {
    const ctx = $("#drawdown-chart").getContext("2d");
    if (drawdownChart) drawdownChart.destroy();
    const dd = thin(r.drawdown_curve, 500);

    drawdownChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: dd.map(d => d.date),
            datasets: [{
                label: "Drawdown",
                data: dd.map(d => d.drawdown),
                borderColor: "#ef4444",
                backgroundColor: "rgba(239,68,68,0.15)",
                fill: true, tension: 0.2, pointRadius: 0, borderWidth: 1.5,
            }],
        },
        options: chartOpts("%"),
    });
}

function renderSignalsChart(r) {
    const ctx = $("#signals-chart").getContext("2d");
    if (signalsChart) signalsChart.destroy();
    const eq = thin(r.equity_curve, 500);

    // Signal markers
    const buys = r.signals.filter(s => s.type === "BUY");
    const sells = r.signals.filter(s => s.type === "SELL" || s.type === "CLOSE");

    signalsChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: eq.map(e => e.date),
            datasets: [{
                label: "Price",
                data: eq.map(e => e.price),
                borderColor: "#3b82f6", fill: false, tension: 0.2, pointRadius: 0, borderWidth: 2,
            }, {
                label: "Buy Signals",
                data: eq.map(e => {
                    const sig = buys.find(s => s.date === e.date);
                    return sig ? sig.price : null;
                }),
                borderColor: "#10b981", backgroundColor: "#10b981",
                pointRadius: 6, pointStyle: "triangle", showLine: false,
            }, {
                label: "Sell Signals",
                data: eq.map(e => {
                    const sig = sells.find(s => s.date === e.date);
                    return sig ? sig.price : null;
                }),
                borderColor: "#ef4444", backgroundColor: "#ef4444",
                pointRadius: 6, pointStyle: "triangle", rotation: 180, showLine: false,
            }],
        },
        options: chartOpts("$"),
    });
}

// Trade log
function renderTradeLog(trades) {
    const tbody = $("#trade-log-table");
    if (!trades.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No trades</td></tr>';
        return;
    }
    tbody.innerHTML = trades.map((t, i) => `
        <tr class="${t.side === 'LONG' ? 'trade-long' : 'trade-short'}">
            <td>${i + 1}</td>
            <td style="color:${t.side === 'LONG' ? 'var(--green)' : 'var(--red)'};font-weight:600;">${t.side}</td>
            <td>${t.entry_date}</td>
            <td>${t.exit_date}</td>
            <td>${fmt.usd(t.entry_price)}</td>
            <td>${fmt.usd(t.exit_price)}</td>
            <td class="${t.pnl >= 0 ? 'positive' : 'negative'}">${fmt.usd(t.pnl)}</td>
            <td class="${t.pnl_pct >= 0 ? 'positive' : 'negative'}">${fmt.pct(t.pnl_pct)}</td>
            <td>${t.bars_held}</td>
        </tr>
    `).join("");
}

// Compare
$("#btn-compare").addEventListener("click", async () => {
    const btn = $("#btn-compare");
    btn.disabled = true; btn.textContent = "Running all strategies...";

    try {
        const res = await fetch("/api/compare", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                symbol: $("#cmp-symbol").value,
                days: parseInt($("#cmp-days").value),
                capital: parseFloat($("#cmp-capital").value),
            }),
        });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        renderComparison(data.results);
        $("#compare-container").style.display = "block";
    } catch(e) {
        alert("Compare failed: " + e.message);
    } finally {
        btn.disabled = false; btn.textContent = "Compare All Strategies";
    }
});

function renderComparison(results) {
    // Table
    const tbody = $("#compare-table");
    const sorted = [...results].sort((a,b) => b.total_return_pct - a.total_return_pct);
    tbody.innerHTML = sorted.map(r => {
        const alpha = r.total_return_pct - r.buy_hold_return_pct;
        return `<tr>
            <td><strong>${r.strategy_name}</strong></td>
            <td class="${r.total_return_pct >= 0 ? 'positive' : 'negative'}">${fmt.pct(r.total_return_pct)}</td>
            <td>${r.sharpe_ratio.toFixed(2)}</td>
            <td>${r.win_rate.toFixed(1)}%</td>
            <td class="negative">-${r.max_drawdown_pct.toFixed(2)}%</td>
            <td>${r.total_trades}</td>
            <td>${r.profit_factor === Infinity ? "∞" : r.profit_factor.toFixed(2)}</td>
            <td class="${alpha >= 0 ? 'positive' : 'negative'}">${fmt.pct(alpha)}</td>
        </tr>`;
    }).join("");

    // Equity comparison chart
    const ctx = $("#compare-equity-chart").getContext("2d");
    if (compareEquityChart) compareEquityChart.destroy();

    const colors = ["#8b5cf6","#3b82f6","#10b981","#f59e0b","#ef4444"];
    const datasets = results.map((r, i) => {
        const eq = thin(r.equity_curve, 300);
        return {
            label: r.strategy_name,
            data: eq.map(e => e.equity),
            borderColor: colors[i % colors.length],
            fill: false, tension: 0.2, pointRadius: 0, borderWidth: 2,
        };
    });

    // Use first result's dates as labels
    const labels = thin(results[0].equity_curve, 300).map(e => e.date);

    // Add buy & hold
    const bh = thin(results[0].equity_curve, 300);
    datasets.push({
        label: "Buy & Hold",
        data: bh.map(e => (e.price / results[0].equity_curve[0].price) * results[0].initial_capital),
        borderColor: "#5a6580", borderDash: [5,5],
        fill: false, tension: 0.2, pointRadius: 0, borderWidth: 1.5,
    });

    compareEquityChart = new Chart(ctx, {
        type: "line",
        data: { labels, datasets },
        options: chartOpts("$"),
    });
}

// Helpers
function chartOpts(unit) {
    return {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#8892a8", font: { size: 11 } } } },
        scales: {
            x: { ticks: { color: "#5a6580", maxTicksLimit: 10, font: {size: 10} }, grid: { display: false } },
            y: { ticks: { color: "#8892a8", callback: v => unit === "$" ? "$" + v.toLocaleString() : v.toFixed(1) + "%" }, grid: { color: "rgba(42,53,85,.4)" } },
        },
        interaction: { intersect: false, mode: "index" },
    };
}

function thin(arr, max) {
    if (arr.length <= max) return arr;
    const step = Math.ceil(arr.length / max);
    return arr.filter((_, i) => i % step === 0);
}
