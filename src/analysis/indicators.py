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
    cross = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
    if cross.any():
        return cross[cross].index[-1]
    return None
