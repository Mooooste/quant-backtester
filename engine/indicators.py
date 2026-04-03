"""Technical indicators — pure Python, no pandas dependency required."""


def sma(prices: list[float], period: int) -> list[float]:
    """Simple Moving Average."""
    result = [None] * len(prices)
    for i in range(period - 1, len(prices)):
        result[i] = sum(prices[i - period + 1: i + 1]) / period
    return result


def ema(prices: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    result = [None] * len(prices)
    k = 2 / (period + 1)
    # Seed with SMA
    if len(prices) >= period:
        result[period - 1] = sum(prices[:period]) / period
        for i in range(period, len(prices)):
            result[i] = prices[i] * k + result[i - 1] * (1 - k)
    return result


def rsi(prices: list[float], period: int = 14) -> list[float]:
    """Relative Strength Index."""
    result = [None] * len(prices)
    if len(prices) < period + 1:
        return result

    gains = []
    losses = []

    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    # Initial average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result[period] = 100
    else:
        rs = avg_gain / avg_loss
        result[period] = 100 - (100 / (1 + rs))

    # Smoothed averages
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            result[i + 1] = 100
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100 - (100 / (1 + rs))

    return result


def bollinger_bands(prices: list[float], period: int = 20,
                    num_std: float = 2.0) -> tuple[list, list, list]:
    """Bollinger Bands: returns (upper, middle, lower)."""
    middle = sma(prices, period)
    upper = [None] * len(prices)
    lower = [None] * len(prices)

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1: i + 1]
        mean = middle[i]
        std = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std

    return upper, middle, lower


def macd(prices: list[float], fast: int = 12, slow: int = 26,
         signal_period: int = 9) -> tuple[list, list, list]:
    """MACD: returns (macd_line, signal_line, histogram)."""
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)

    macd_line = [None] * len(prices)
    for i in range(len(prices)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]

    # Signal line = EMA of MACD line
    macd_values = [v if v is not None else 0 for v in macd_line]
    signal_line = ema(macd_values, signal_period)

    # Histogram
    histogram = [None] * len(prices)
    for i in range(len(prices)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, histogram


def atr(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> list[float]:
    """Average True Range — measures volatility."""
    result = [None] * len(closes)
    tr_list = [highs[0] - lows[0]]

    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)

    if len(tr_list) >= period:
        result[period - 1] = sum(tr_list[:period]) / period
        for i in range(period, len(tr_list)):
            result[i] = (result[i - 1] * (period - 1) + tr_list[i]) / period

    return result
