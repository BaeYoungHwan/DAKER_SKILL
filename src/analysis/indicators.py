"""
투자 기술적 지표 계산 모듈
Skills/analysis.md §2 지표 계산 규칙 준수
"""

import pandas as pd
import numpy as np
from typing import Optional


def calc_returns(prices: pd.Series) -> pd.Series:
    """일별 수익률 계산 (Skills/analysis.md §2.1)"""
    return prices.pct_change() * 100


def calc_cumulative_return(prices: pd.Series) -> pd.Series:
    """누적 수익률 계산 (기준일 대비 %)"""
    return (prices / prices.iloc[0] - 1) * 100


def calc_annualized_return(prices: pd.Series) -> float:
    """연환산 수익률 계산"""
    total_return = (prices.iloc[-1] / prices.iloc[0]) - 1
    days = len(prices)
    if days < 2:
        return 0.0
    return ((1 + total_return) ** (365 / days) - 1) * 100


def calc_moving_averages(prices: pd.Series) -> dict[str, pd.Series]:
    """이동평균선 계산 (Skills/analysis.md §2.2)"""
    return {
        "MA5": prices.rolling(5).mean(),
        "MA20": prices.rolling(20).mean(),
        "MA60": prices.rolling(60).mean(),
        "MA120": prices.rolling(120).mean(),
        "MA200": prices.rolling(200).mean(),
    }


def calc_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산 (Skills/analysis.md §2.3)"""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict[str, pd.Series]:
    """볼린저 밴드 계산 (Skills/analysis.md §2.4)"""
    middle = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    return {
        "upper": middle + std_dev * std,
        "middle": middle,
        "lower": middle - std_dev * std,
        "bandwidth": (std_dev * 2 * std) / middle * 100,  # 밴드 폭 (%)
    }


def calc_volatility(prices: pd.Series) -> dict[str, float]:
    """변동성 계산 (Skills/analysis.md §2.5)"""
    daily_returns = prices.pct_change().dropna()
    daily_vol = daily_returns.std() * 100
    annual_vol = daily_vol * np.sqrt(252)
    return {
        "daily_volatility": round(daily_vol, 2),
        "annual_volatility": round(annual_vol, 2),
    }


def calc_sharpe_ratio(prices: pd.Series, risk_free_rate: float = 0.035) -> float:
    """샤프 비율 계산 (Skills/analysis.md §2.6)"""
    daily_returns = prices.pct_change().dropna()
    annual_return = calc_annualized_return(prices) / 100
    annual_vol = calc_volatility(prices)["annual_volatility"] / 100

    if annual_vol == 0:
        return 0.0

    return round((annual_return - risk_free_rate) / annual_vol, 2)


def calc_max_drawdown(prices: pd.Series) -> float:
    """최대 낙폭(MDD) 계산"""
    peak = prices.cummax()
    drawdown = (prices - peak) / peak * 100
    return round(drawdown.min(), 2)


def calc_drawdown_series(prices: pd.Series) -> pd.Series:
    """낙폭 시계열 반환 (%) — 모든 시점의 drawdown 값"""
    peak = prices.cummax()
    return (prices - peak) / peak * 100


def calc_correlation_matrix(close_prices: pd.DataFrame) -> pd.DataFrame:
    """종목 간 상관관계 행렬 계산"""
    returns = close_prices.pct_change().dropna()
    return returns.corr().round(2)


def get_rsi_signal(rsi_value: float) -> str:
    """RSI 신호 판단 (Skills/analysis.md §2.3)"""
    if rsi_value > 70:
        return "과매수"
    elif rsi_value < 30:
        return "과매도"
    return "중립"


def detect_golden_cross(ma_short: pd.Series, ma_long: pd.Series) -> Optional[pd.Timestamp]:
    """골든크로스 최근 발생 시점 탐지"""
    # 공통 인덱스로 정렬 후 NaN 제거
    aligned = pd.DataFrame({"short": ma_short, "long": ma_long}).dropna()
    if aligned.empty:
        return None
    cross = (aligned["short"] > aligned["long"]) & (aligned["short"].shift(1) <= aligned["long"].shift(1))
    if cross.any():
        return cross[cross].index[-1]
    return None


# ── 신규 지표 ─────────────────────────────────────────────────

def calc_52week_range(prices: pd.Series) -> dict:
    """52주 고가/저가 및 현재가 위치 (%)"""
    window = min(252, len(prices))
    recent = prices.iloc[-window:]
    high_52 = float(recent.max())
    low_52 = float(recent.min())
    current = float(prices.iloc[-1])
    position_pct = (current - low_52) / (high_52 - low_52) * 100 if high_52 > low_52 else 50.0
    return {
        "high_52": high_52,
        "low_52": low_52,
        "current": current,
        "position_pct": round(position_pct, 1),
    }


def calc_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD (이동평균 수렴·확산 지표)"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def calc_beta(prices: pd.Series, benchmark_prices: pd.Series) -> float:
    """베타 계수 계산 (벤치마크 대비 민감도)"""
    asset_ret = prices.pct_change().dropna()
    bench_ret = benchmark_prices.pct_change().dropna()
    aligned = pd.DataFrame({"asset": asset_ret, "bench": bench_ret}).dropna()
    if len(aligned) < 20:
        return 0.0
    cov = aligned.cov()
    beta = cov.loc["asset", "bench"] / cov.loc["bench", "bench"]
    return round(float(beta), 2)


def calc_momentum(prices: pd.Series) -> dict:
    """단기·중기 모멘텀 (%) - 1주/1개월/3개월"""
    current = float(prices.iloc[-1])
    result: dict = {}
    for label, days in [("1W", 5), ("1M", 21), ("3M", 63)]:
        if len(prices) >= days:
            past = float(prices.iloc[-days])
            result[label] = round((current / past - 1) * 100, 2)
        else:
            result[label] = None
    return result


def calc_rolling_sharpe(prices: pd.Series, window: int = 60, risk_free_rate: float = 0.035) -> pd.Series:
    """롤링 샤프 비율 계산 (trailing window 기준)"""
    daily_returns = prices.pct_change()
    daily_rf = risk_free_rate / 252
    excess = daily_returns - daily_rf
    rolling_mean = excess.rolling(window).mean()
    rolling_std = daily_returns.rolling(window).std()
    sharpe = (rolling_mean / rolling_std.replace(0, np.nan)) * np.sqrt(252)
    return sharpe.round(2)


def calc_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> dict:
    """스토캐스틱 %K, %D 계산"""
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    k = (df["Close"] - low_min) / (high_max - low_min) * 100
    d = k.rolling(window=d_period).mean()
    return {"k": k, "d": d}
