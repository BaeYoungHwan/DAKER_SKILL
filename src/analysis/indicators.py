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


def generate_screener_signals(
    df: pd.DataFrame,
    info: dict,
    cfg: dict,
) -> list[str]:
    """종목 스크리너 기술적 신호 생성 (UI 의존성 없는 순수 함수).

    Args:
        df: OHLCV DataFrame (Close, Volume 포함)
        info: fetch_info() 반환값 (pe_ratio 포함)
        cfg: load_analysis_config() 반환값

    Returns:
        신호 문자열 리스트 (예: ["🟢 RSI 과매도", "🚀 52주 신고가"])
    """
    # 스크리너 임계값
    GOLDEN_CROSS_DAYS   = 30
    VOL_SURGE_RATIO     = 2.0
    LOW_PER_THRESHOLD   = 15.0
    LOW_RSI_FOR_PER     = 40.0
    HIGH_52W_PROXIMITY  = 0.99   # 52주 고가의 99% 이상이면 신고가 돌파

    c = df["Close"]
    signals: list[str] = []
    ob, os_ = cfg.get("rsi_overbought", 70), cfg.get("rsi_oversold", 30)

    rsi_val = float(calc_rsi(c).dropna().iloc[-1])
    if rsi_val < os_:
        signals.append("🟢 RSI 과매도")
    elif rsi_val > ob:
        signals.append("🔴 RSI 과매수")

    mas = calc_moving_averages(c)
    gc = detect_golden_cross(mas["MA20"], mas["MA60"])
    dc = detect_golden_cross(mas["MA60"], mas["MA20"])
    if gc and (c.index[-1] - gc).days <= GOLDEN_CROSS_DAYS:
        signals.append("🟢 골든크로스")
    if dc and (c.index[-1] - dc).days <= GOLDEN_CROSS_DAYS:
        signals.append("🔴 데드크로스")

    bb = calc_bollinger_bands(c)
    lp = float(c.iloc[-1])
    upper, lower = bb["upper"].dropna(), bb["lower"].dropna()
    if not upper.empty and lp > float(upper.iloc[-1]):
        signals.append("🟡 BB 상단")
    elif not lower.empty and lp < float(lower.iloc[-1]):
        signals.append("🟢 BB 하단")

    hist = calc_macd(c)["histogram"].dropna()
    if len(hist) >= 2:
        if float(hist.iloc[-1]) > 0 and float(hist.iloc[-2]) <= 0:
            signals.append("🟢 MACD↑")
        elif float(hist.iloc[-1]) < 0 and float(hist.iloc[-2]) >= 0:
            signals.append("🔴 MACD↓")

    w52 = calc_52week_range(c)
    if lp >= w52["high_52"] * HIGH_52W_PROXIMITY:
        signals.append("🚀 52주 신고가")

    if "Volume" in df.columns:
        vol = df["Volume"].dropna()
        if len(vol) >= 21:
            avg_vol = float(vol.iloc[-21:-1].mean())
            cur_vol = float(vol.iloc[-1])
            if avg_vol > 0 and cur_vol >= avg_vol * VOL_SURGE_RATIO:
                signals.append(f"📈 거래량 {cur_vol / avg_vol:.1f}배↑")

    per = info.get("pe_ratio")
    if per and 0 < float(per) < LOW_PER_THRESHOLD and rsi_val < LOW_RSI_FOR_PER:
        signals.append(f"💎 저PER({per:.0f})+저RSI")

    return signals


def calc_holdings_pnl(
    holdings: dict,
    current_prices: dict,
) -> dict:
    """보유 종목 평가손익 계산 (공매도 포함).

    Args:
        holdings: {ticker: {"avg_cost": float, "quantity": float}}
        current_prices: {ticker: float}

    Returns:
        {ticker: {"current_price", "avg_cost", "quantity", "is_short",
                  "eval_amount", "cost_amount", "pnl", "pnl_pct"}}
    """
    result: dict = {}
    for ticker, h in holdings.items():
        curr = current_prices.get(ticker)
        if curr is None or h.get("avg_cost", 0) <= 0 or h.get("quantity", 0) == 0:
            continue
        cost = float(h["avg_cost"])
        qty  = float(h["quantity"])
        is_short = qty < 0
        pnl     = (cost - curr) * abs(qty) if is_short else (curr - cost) * qty
        pnl_pct = (cost / curr - 1) * 100  if is_short else (curr / cost - 1) * 100
        result[ticker] = {
            "current_price": curr,
            "avg_cost":      cost,
            "quantity":      qty,
            "is_short":      is_short,
            "eval_amount":   curr * abs(qty),
            "cost_amount":   cost * abs(qty),
            "pnl":           pnl,
            "pnl_pct":       pnl_pct,
        }
    return result


def _generate_signals(
    close: pd.Series,
    strategy: str,
    cfg: dict,
) -> tuple[pd.Series, pd.Series]:
    """전략별 매수/매도 신호 시리즈 반환."""
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
    return buy_signal, sell_signal


def _simulate_portfolio(
    close: pd.Series,
    buy_signal: pd.Series,
    sell_signal: pd.Series,
    initial_capital: float,
) -> tuple[pd.Series, list[dict]]:
    """매수/매도 신호 기반 포트폴리오 시뮬레이션."""
    cash, shares, in_position = float(initial_capital), 0.0, False
    portfolio_values: list[float] = []
    trades: list[dict] = []

    for date, price in close.items():
        if pd.isna(price):
            portfolio_values.append(cash)
            continue
        if bool(buy_signal.get(date, False)) and not in_position:
            shares, cash, in_position = cash / float(price), 0.0, True
            trades.append({"날짜": date.strftime("%Y-%m-%d"), "신호": "매수", "가격": round(float(price), 2)})
        elif bool(sell_signal.get(date, False)) and in_position:
            cash, shares, in_position = shares * float(price), 0.0, False
            trades.append({"날짜": date.strftime("%Y-%m-%d"), "신호": "매도", "가격": round(float(price), 2)})
        portfolio_values.append(cash + shares * float(price))

    return pd.Series(portfolio_values, index=close.index), trades


def _calc_backtest_metrics(
    portfolio: pd.Series,
    benchmark: pd.Series,
    trades: list[dict],
    initial_capital: float,
) -> dict:
    """백테스트 성과 지표 계산 (수익률, 승률, MDD)."""
    buy_prices  = [t["가격"] for t in trades if t["신호"] == "매수"]
    sell_prices = [t["가격"] for t in trades if t["신호"] == "매도"]
    pairs = min(len(buy_prices), len(sell_prices))
    wins  = sum(1 for i in range(pairs) if sell_prices[i] > buy_prices[i])
    running_max = portfolio.cummax()
    mdd = float(((portfolio - running_max) / running_max * 100).min())
    final_ret = (float(portfolio.iloc[-1]) / initial_capital - 1) * 100
    bench_ret  = (float(benchmark.iloc[-1]) / initial_capital - 1) * 100
    return {
        "전략수익률(%)": round(final_ret, 1),
        "Buy&Hold(%)":   round(bench_ret, 1),
        "초과수익(%p)":  round(final_ret - bench_ret, 1),
        "총거래횟수":    len(trades),
        "승률(%)":       round((wins / pairs * 100) if pairs > 0 else 0.0, 1),
        "MDD(%)":        round(mdd, 1),
    }


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

    buy_signal, sell_signal = _generate_signals(close, strategy, cfg)
    portfolio, trades = _simulate_portfolio(close, buy_signal, sell_signal, initial_capital)
    benchmark = initial_capital * (close / float(close.iloc[0]))
    metrics = _calc_backtest_metrics(portfolio, benchmark, trades, initial_capital)

    return {
        "portfolio": portfolio,
        "benchmark": benchmark,
        "trades": trades,
        "metrics": metrics,
    }
