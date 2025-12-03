# strategy_rules.py
from typing import List, Dict, Any
from statistics import mean

def _sma(values: List[float], window: int) -> float:
    if window <= 0 or len(values) < window:
        return float("nan")
    return mean(values[-window:])

def decide_from_history(ticker: str, history_rows: List[Dict[str, Any]]) -> str:
    """
    Given all history rows for one ticker: [{"ticker":"AAPL","price":..., "day":...}, ...]
    Return one of: "BUY", "SELL", "HOLD"
    """
    prices = [float(r["price"]) for r in sorted(history_rows, key=lambda r: r["day"])]
    if len(prices) < 3:  # not enough history, be conservative
        return "HOLD"
    short = _sma(prices, 3)
    long = _sma(prices, 5) if len(prices) >= 5 else _sma(prices, len(prices))
    if short != short or long != long:  # NaN check
        return "HOLD"
    if short > long:
        return "BUY"
    if short < long:
        return "SELL"
    return "HOLD"
