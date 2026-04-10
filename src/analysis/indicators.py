"""
투자 기술적 지표 계산 모듈
Skills/analysis.md §2 지표 계산 규칙 준수

임계치(RSI 30/70, 샤프비율 1/2, 연환산 거래일 252 등)는
skills.parser.load_analysis_config() 에서 런타임에 로드됩니다.
Skills/analysis.md 수정 시 코드 변경 없이 자동 반영됩니다.
"""

import pandas as pd
import numpy as np
from typing import Optional

from skills.parser import load_analysis_config


def _cfg() -> dict:
    """Skills/analysis.md 파싱 결과 반환 (lru_cache 로 1회만 파싱)"""
    return load_analysis_config()


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
    """이동평균선 계산 (Skills/analysis.md §2.2 — 기간은 Skills 파일에서 로드)"""
    periods = _cfg()["ma_periods"]
    return {f"MA{p}": prices.rolling(p).mean() for p in periods}


def calc_rsi(prices: pd.Series, period: int | None = None) -> pd.Series:
    """RSI 계산 (Skills/analysis.md §2.3 — 기간은 Skills 파일에서 로드)"""
    if period is None:
        period = _cfg()["rsi_period"]
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_bollinger_bands(prices: pd.Series, period: int | None = None, std_dev: float | None = None) -> dict[str, pd.Series]:
    """볼린저 밴드 계산 (Skills/analysis.md §2.4 — 기간·표준편차는 Skills 파일에서 로드)"""
    if period is None:
        period = _cfg()["bb_period"]
    if std_dev is None:
        std_dev = _cfg()["bb_std"]
    middle = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    return {
        "upper": middle + std_dev * std,
        "middle": middle,
        "lower": middle - std_dev * std,
        "bandwidth": (std_dev * 2 * std) / middle * 100,  # 밴드 폭 (%)
    }


def calc_volatility(prices: pd.Series) -> dict[str, float]:
    """변동성 계산 (Skills/analysis.md §2.5 — 거래일수는 Skills 파일에서 로드)"""
    trading_days = _cfg()["trading_days"]
    daily_returns = prices.pct_change().dropna()
    daily_vol = daily_returns.std() * 100
    annual_vol = daily_vol * np.sqrt(trading_days)
    return {
        "daily_volatility": round(daily_vol, 2),
        "annual_volatility": round(annual_vol, 2),
    }


def calc_sharpe_ratio(prices: pd.Series, risk_free_rate: float | None = None) -> float:
    """샤프 비율 계산 (Skills/analysis.md §2.6 — 무위험 수익률은 Skills 파일에서 로드)"""
    if risk_free_rate is None:
        risk_free_rate = _cfg()["risk_free_rate"]
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
    """RSI 신호 판단 (Skills/analysis.md §2.3 — 임계치는 Skills 파일에서 로드)"""
    cfg = _cfg()
    if rsi_value > cfg["rsi_overbought"]:
        return "과매수"
    elif rsi_value < cfg["rsi_oversold"]:
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


def calc_rolling_sharpe(prices: pd.Series, window: int = 60, risk_free_rate: float | None = None) -> pd.Series:
    """롤링 샤프 비율 계산 (trailing window 기준 — 무위험 수익률은 Skills 파일에서 로드)"""
    if risk_free_rate is None:
        risk_free_rate = _cfg()["risk_free_rate"]
    trading_days = _cfg()["trading_days"]
    daily_returns = prices.pct_change()
    daily_rf = risk_free_rate / trading_days
    excess = daily_returns - daily_rf
    rolling_mean = excess.rolling(window).mean()
    rolling_std = daily_returns.rolling(window).std()
    sharpe = (rolling_mean / rolling_std.replace(0, np.nan)) * np.sqrt(trading_days)
    return sharpe.round(2)


def calc_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> dict:
    """스토캐스틱 %K, %D 계산"""
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    k = (df["Close"] - low_min) / (high_max - low_min) * 100
    d = k.rolling(window=d_period).mean()
    return {"k": k, "d": d}


def run_backtest(
    close: pd.Series,
    strategy: str = "ma_cross",
    initial_capital: float = 10_000_000,
) -> dict:
    """백테스트 시뮬레이션
    strategy: "ma_cross" (MA20/MA60 크로스) | "rsi_reversal" (RSI 30/70 반전)
    반환: portfolio, benchmark, trades, metrics
    """
    cfg = _cfg()
    close = close.dropna()
    if len(close) < 70:
        return {}

    if strategy == "ma_cross":
        ma_short = close.rolling(20).mean()
        ma_long = close.rolling(60).mean()
        buy_signal = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        sell_signal = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
    else:  # rsi_reversal
        rsi = calc_rsi(close)
        ob = cfg.get("rsi_overbought", 70)
        os_ = cfg.get("rsi_oversold", 30)
        buy_signal = (rsi < os_) & (rsi.shift(1) >= os_)
        sell_signal = (rsi > ob) & (rsi.shift(1) <= ob)

    cash = float(initial_capital)
    shares = 0.0
    in_position = False
    portfolio_values = []
    trades = []

    for date, price in close.items():
        if pd.isna(price):
            portfolio_values.append(cash + shares * (price if not pd.isna(price) else 0))
            continue

        is_buy = bool(buy_signal.get(date, False))
        is_sell = bool(sell_signal.get(date, False))

        if is_buy and not in_position:
            shares = cash / float(price)
            cash = 0.0
            in_position = True
            trades.append({
                "날짜": date.strftime("%Y-%m-%d"),
                "신호": "매수",
                "가격": round(float(price), 2),
            })
        elif is_sell and in_position:
            cash = shares * float(price)
            shares = 0.0
            in_position = False
            trades.append({
                "날짜": date.strftime("%Y-%m-%d"),
                "신호": "매도",
                "가격": round(float(price), 2),
            })

        portfolio_values.append(cash + shares * float(price))

    portfolio = pd.Series(portfolio_values, index=close.index)
    benchmark = initial_capital * (close / float(close.iloc[0]))

    # 승률 계산
    buy_prices = [t["가격"] for t in trades if t["신호"] == "매수"]
    sell_prices = [t["가격"] for t in trades if t["신호"] == "매도"]
    pairs = min(len(buy_prices), len(sell_prices))
    wins = sum(1 for i in range(pairs) if sell_prices[i] > buy_prices[i])
    win_rate = (wins / pairs * 100) if pairs > 0 else 0.0

    running_max = portfolio.cummax()
    mdd = float(((portfolio - running_max) / running_max * 100).min())

    final_return = (float(portfolio.iloc[-1]) / initial_capital - 1) * 100
    bench_return = (float(benchmark.iloc[-1]) / initial_capital - 1) * 100

    metrics = {
        "전략수익률(%)": round(final_return, 1),
        "Buy&Hold(%)": round(bench_return, 1),
        "초과수익(%p)": round(final_return - bench_return, 1),
        "총거래횟수": len(trades),
        "승률(%)": round(win_rate, 1),
        "MDD(%)": round(mdd, 1),
    }

    return {
        "portfolio": portfolio,
        "benchmark": benchmark,
        "trades": trades,
        "metrics": metrics,
    }
