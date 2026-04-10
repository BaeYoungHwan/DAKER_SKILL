"""
yfinance 기반 금융 데이터 수집 모듈
Skills/analysis.md 데이터 수집 기준 준수
"""

import time
import yfinance as yf
import pandas as pd
import requests
import streamlit as st
from typing import Optional


def _flatten_columns(data: pd.DataFrame) -> pd.DataFrame:
    """MultiIndex 컬럼 평탄화 (yfinance >= 0.2.x 대응)"""
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data


def _clean_price_outliers(data: pd.DataFrame) -> pd.DataFrame:
    """데이터 오류 필터링: 전일 대비 Close ±50% 초과 변동은 yfinance 오류로 간주 → NaN 후 ffill

    한국 주식(005930.KS 등)에서 yfinance가 간헐적으로 잘못된 가격을 반환하는 문제 대응.
    """
    if "Close" not in data.columns or len(data) < 2:
        return data
    daily_ret = data["Close"].pct_change().abs()
    outlier_mask = daily_ret > 0.5
    if not outlier_mask.any():
        return data
    data = data.copy()
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in data.columns:
            data.loc[outlier_mask, col] = pd.NA
    return data.ffill()


# 기간 선택 기준 (Skills/analysis.md §1)
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
DEFAULT_PERIOD = "1y"


@st.cache_data(ttl=3600)  # 1시간 캐싱 (Skills/analysis.md §4)
def fetch_price(ticker: str, period: str = DEFAULT_PERIOD) -> pd.DataFrame:
    """OHLCV 주가 데이터 조회 (Rate Limit 대응: 최대 2회 재시도)"""
    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD

    data = pd.DataFrame()
    for attempt in range(3):
        try:
            data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if not data.empty:
                break
        except Exception:
            pass
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))  # 1.5s → 3.0s 지연 후 재시도

    if data.empty:
        return pd.DataFrame()

    # MultiIndex 컬럼 평탄화 (yfinance >= 0.2.x 대응)
    data = _flatten_columns(data)

    # 결측값 처리: forward fill (Skills/analysis.md §4)
    data = data.ffill()

    # 이상치 필터링: yfinance 데이터 오류 제거 (±50% 초과 일별 변동)
    data = _clean_price_outliers(data)

    return data


@st.cache_data(ttl=3600)
def fetch_info(ticker: str) -> dict:
    """종목 기본 정보 및 재무지표 조회 (PER, PBR, EPS, 배당수익률)"""
    try:
        info = yf.Ticker(ticker).info
        return {
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", None),
            "pe_ratio": info.get("trailingPE", None),
            "pb_ratio": info.get("priceToBook", None),
            "eps": info.get("trailingEps", None),
            "dividend_yield": info.get("dividendYield", None),
            "currency": info.get("currency", "USD"),
        }
    except Exception:
        return {"name": ticker, "sector": "N/A"}


@st.cache_data(ttl=3600)
def fetch_multiple(tickers: list[str], period: str = DEFAULT_PERIOD) -> dict[str, pd.DataFrame]:
    """여러 종목 주가 데이터 일괄 조회 (요청 간 0.3s 지연 — Rate Limit 방지)"""
    result = {}
    for i, ticker in enumerate(tickers):
        df = fetch_price(ticker, period)
        if not df.empty:
            result[ticker] = df
        if i < len(tickers) - 1:
            time.sleep(0.3)
    return result


@st.cache_data(ttl=3600)
def fetch_market_indices(period: str = DEFAULT_PERIOD) -> dict[str, pd.DataFrame]:
    """주요 시장 지수 조회 (S&P500, NASDAQ, KOSPI)"""
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "KOSPI": "^KS11",
        "DOW JONES": "^DJI",
    }
    return fetch_multiple(list(indices.values()), period)


@st.cache_data(ttl=3600)
def fetch_exchange_rate_series(from_currency: str = "USD", to_currency: str = "KRW", period: str = DEFAULT_PERIOD) -> pd.Series:
    """환율 시계열 조회 (예: USDKRW=X). 원화 환산 포트폴리오 비교에 사용."""
    try:
        ticker = f"{from_currency}{to_currency}=X"
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if data.empty:
            return pd.Series(dtype=float)
        data = _flatten_columns(data)
        return data["Close"].ffill()
    except Exception:
        return pd.Series(dtype=float)


# 주요 한국 종목 한국어 이름 → yfinance 티커 매핑
# Yahoo Finance API가 한국어 쿼리를 지원하지 않으므로 로컬 매핑으로 보완
KR_NAME_MAP: dict[str, str] = {
    # ── 반도체·IT
    "삼성전자": "005930.KS",
    "sk하이닉스": "000660.KS",
    "sk 하이닉스": "000660.KS",
    "삼성전기": "009150.KS",
    "삼성sdi": "006400.KS",
    "lg이노텍": "011070.KS",
    "한미반도체": "042700.KS",
    "리노공업": "058470.KQ",
    # ── 2차전지·배터리
    "lg에너지솔루션": "373220.KS",
    "에코프로비엠": "247540.KQ",
    "에코프로": "086520.KQ",
    "포스코퓨처엠": "003670.KS",
    "엘앤에프": "066970.KQ",
    "천보": "278280.KQ",
    # ── 바이오·제약
    "삼성바이오로직스": "207940.KS",
    "셀트리온": "068270.KS",
    "유한양행": "000100.KS",
    "한미약품": "128940.KS",
    "종근당": "185750.KS",
    "보령": "003850.KS",
    # ── 자동차
    "현대차": "005380.KS",
    "현대자동차": "005380.KS",
    "기아": "000270.KS",
    "현대모비스": "012330.KS",
    "한온시스템": "018880.KS",
    # ── 화학·에너지
    "lg화학": "051910.KS",
    "sk이노베이션": "096770.KS",
    "롯데케미칼": "011170.KS",
    "금호석유화학": "011780.KS",
    "효성첨단소재": "298050.KS",
    # ── 철강·소재
    "포스코홀딩스": "005490.KS",
    "고려아연": "010130.KS",
    "현대제철": "004020.KS",
    "동국제강": "460860.KS",
    # ── 인터넷·플랫폼
    "네이버": "035420.KS",
    "카카오": "035720.KS",
    "카카오뱅크": "323410.KS",
    "카카오페이": "377300.KS",
    "크래프톤": "259960.KS",
    "넷마블": "251270.KS",
    "엔씨소프트": "036570.KS",
    "펄어비스": "263750.KQ",
    # ── 금융·보험
    "kb금융": "105560.KS",
    "신한지주": "055550.KS",
    "하나금융지주": "086790.KS",
    "우리금융지주": "316140.KS",
    "삼성생명": "032830.KS",
    "삼성화재": "000810.KS",
    "미래에셋증권": "006800.KS",
    "키움증권": "039490.KS",
    # ── 유통·소비재
    "삼성물산": "028260.KS",
    "롯데쇼핑": "023530.KS",
    "신세계": "004170.KS",
    "현대백화점": "069960.KS",
    "cj제일제당": "097950.KS",
    "오리온": "271560.KS",
    "농심": "004370.KS",
    # ── 통신
    "sk텔레콤": "017670.KS",
    "kt": "030200.KS",
    "lg유플러스": "032640.KS",
    # ── 건설·인프라
    "삼성엔지니어링": "028050.KS",
    "현대건설": "000720.KS",
    "gS건설": "006360.KS",
    "두산에너빌리티": "034020.KS",
    # ── 가전·전자
    "lg전자": "066570.KS",
    # ── 항공·물류
    "대한항공": "003490.KS",
    "한진칼": "180640.KS",
    "현대글로비스": "086280.KS",
}

# KR_TICKER_TO_NAME 역방향: ticker → 한국어 이름 (공식명 우선 = 더 긴 이름)
KR_TICKER_TO_NAME: dict[str, str] = {}
for _kr_name, _ticker in KR_NAME_MAP.items():
    if _ticker not in KR_TICKER_TO_NAME or len(_kr_name) > len(KR_TICKER_TO_NAME[_ticker]):
        KR_TICKER_TO_NAME[_ticker] = _kr_name


def search_ticker(query: str) -> list[dict]:
    """종목명 또는 티커로 검색 (한국어 종목명 + Yahoo Finance 영어 검색 하이브리드)"""
    query_lower = query.lower().strip()
    results: list[dict] = []
    seen_tickers: set[str] = set()

    # 1단계: 한국어 종목명 로컬 매핑 검색 (티커 중복 제거)
    for kr_name, ticker in KR_NAME_MAP.items():
        if ticker in seen_tickers:
            continue
        if query_lower in kr_name or kr_name.startswith(query_lower):
            display_name = KR_TICKER_TO_NAME.get(ticker, kr_name)
            results.append({
                "symbol": ticker,
                "shortname": display_name,
                "quoteType": "EQUITY",
            })
            seen_tickers.add(ticker)

    # 2단계: Yahoo Finance 영어 검색 (ASCII 쿼리만)
    if query.isascii():
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 8, "lang": "ko-KR"}
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                quotes = resp.json().get("quotes", [])
                existing = {r["symbol"] for r in results}
                for q in quotes:
                    if q.get("quoteType") in ("EQUITY", "ETF") and q["symbol"] not in existing:
                        # 한국어 이름이 있으면 우선 표시
                        if q["symbol"] in KR_TICKER_TO_NAME:
                            q["shortname"] = KR_TICKER_TO_NAME[q["symbol"]]
                        results.append(q)
        except Exception:
            pass

    return results[:8]


@st.cache_data(ttl=300)  # 5분 캐싱 (시장 데이터 자주 갱신)
def fetch_market_overview() -> dict:
    """주요 시장 지수 현황 (현재가 + 전일 대비 변동률)"""
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW": "^DJI",
        "KOSPI": "^KS11",
        "VIX": "^VIX",
    }
    result = {}
    for i, (name, ticker) in enumerate(indices.items()):
        try:
            df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.ffill()
            if len(df) >= 2:
                curr = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2])
                chg = (curr - prev) / prev * 100
                result[name] = {"price": curr, "change": round(chg, 2), "ticker": ticker}
        except Exception:
            pass
        if i < len(indices) - 1:
            time.sleep(0.2)
    return result


@st.cache_data(ttl=600)  # 10분 캐싱
def fetch_fear_greed() -> dict:
    """yfinance 지표 기반 자체 계산 공포/탐욕 지수 (0=극단공포, 100=극단탐욕)"""
    def _close(ticker: str, period: str = "1y") -> pd.Series:
        for attempt in range(2):
            try:
                df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
                if not df.empty:
                    break
            except Exception:
                pass
            if attempt == 0:
                time.sleep(1.0)
        else:
            return pd.Series(dtype=float)
        if df.empty:
            return pd.Series(dtype=float)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.dropna()

    scores = []

    # 1. VIX (역방향: VIX 낮을수록 탐욕)
    try:
        vix = _close("^VIX")
        if len(vix) >= 2:
            vix_now = float(vix.iloc[-1])
            vix_min, vix_max = float(vix.min()), float(vix.max())
            vix_score = 100 - ((vix_now - vix_min) / (vix_max - vix_min) * 100) if vix_max > vix_min else 50
            scores.append(("vix", vix_score, 0.4))
    except Exception:
        pass

    # 2. S&P500 모멘텀 (현재가 vs 125일 이평)
    sp_close = _close("^GSPC")
    try:
        if len(sp_close) >= 126:
            sp_ma125 = sp_close.rolling(125).mean().dropna()
            ma_val = float(sp_ma125.iloc[-1])
            curr_val = float(sp_close.iloc[-1])
            ratio = (curr_val / ma_val - 1) * 100
            mom_score = float(min(max(50 + ratio * 5, 0), 100))
            scores.append(("mom", mom_score, 0.4))
    except Exception:
        pass

    # 3. 볼린저 밴드 폭 (좁을수록 낮은 불확실성 = 탐욕)
    try:
        if len(sp_close) >= 21:
            bb_width = (sp_close.rolling(20).std() / sp_close.rolling(20).mean() * 100).dropna()
            bw_now = float(bb_width.iloc[-1])
            bw_min, bw_max = float(bb_width.min()), float(bb_width.max())
            bw_score = 100 - ((bw_now - bw_min) / (bw_max - bw_min) * 100) if bw_max > bw_min else 50
            scores.append(("bw", bw_score, 0.2))
    except Exception:
        pass

    if not scores:
        return {"score": 50, "label": "중립", "vix": None}

    total_weight = sum(w for _, _, w in scores)
    score = round(sum(s * w for _, s, w in scores) / total_weight, 1)
    score = float(min(max(score, 0), 100))

    if score >= 75:
        label = "극단적 탐욕"
    elif score >= 55:
        label = "탐욕"
    elif score >= 45:
        label = "중립"
    elif score >= 25:
        label = "공포"
    else:
        label = "극단적 공포"

    vix_val = None
    for name, s, _ in scores:
        if name == "vix":
            try:
                vix_val = round(float(_close("^VIX").iloc[-1]), 2)
            except Exception:
                pass
            break

    return {"score": score, "label": label, "vix": vix_val}


def fetch_earnings(ticker: str) -> pd.DataFrame:
    """분기별 EPS 예상치 vs 실제치 (어닝 서프라이즈)"""
    try:
        t = yf.Ticker(ticker)
        df = t.earnings_dates
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.dropna(subset=["EPS Estimate", "Reported EPS"]).copy()
        df = df.sort_index().tail(8)
        df["Surprise"] = df["Reported EPS"] - df["EPS Estimate"]
        df["Surprise %"] = (df["Surprise"] / df["EPS Estimate"].abs() * 100).round(1)
        df.index = df.index.strftime("%Y-%m-%d")
        return df[["EPS Estimate", "Reported EPS", "Surprise %"]]
    except Exception:
        return pd.DataFrame()


def fetch_news(ticker: str, max_count: int = 8) -> list[dict]:
    """종목 관련 최신 뉴스 반환 (yfinance .news)"""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        result = []
        for item in news[:max_count]:
            content = item.get("content", {})
            title = content.get("title", "") or item.get("title", "")
            url = content.get("canonicalUrl", {}).get("url", "") or item.get("link", "")
            publisher = content.get("provider", {}).get("displayName", "") or item.get("publisher", "")
            pub_time = content.get("pubDate", "") or ""
            if title and url:
                result.append({
                    "title": title,
                    "url": url,
                    "publisher": publisher,
                    "pub_time": pub_time[:10] if pub_time else "",
                })
        return result
    except Exception:
        return []


def fetch_financials(ticker: str) -> pd.DataFrame:
    """분기별 매출/순이익 데이터 조회 (quarterly_income_stmt)"""
    try:
        t = yf.Ticker(ticker)
        df = t.quarterly_income_stmt
        if df is None or df.empty:
            return pd.DataFrame()
        rows = {}
        for field, label in [
            ("Total Revenue", "매출"),
            ("Net Income", "순이익"),
            ("Gross Profit", "매출총이익"),
        ]:
            if field in df.index:
                rows[label] = df.loc[field]
        if not rows:
            return pd.DataFrame()
        result = pd.DataFrame(rows).sort_index()
        result.index = result.index.strftime("%Y-%m")
        return result / 1e9  # 십억 달러 단위
    except Exception:
        return pd.DataFrame()


def fetch_dividends(ticker: str) -> pd.Series:
    """배당금 히스토리 (날짜별 배당금액)"""
    try:
        t = yf.Ticker(ticker)
        div = t.dividends
        if div is None or div.empty:
            return pd.Series(dtype=float)
        if hasattr(div.index, "tz") and div.index.tz is not None:
            div.index = div.index.tz_localize(None)
        return div.sort_index()
    except Exception:
        return pd.Series(dtype=float)


def get_close_prices(data_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """여러 종목 종가 데이터를 하나의 DataFrame으로 병합"""
    closes = {}
    for ticker, df in data_dict.items():
        if not df.empty and "Close" in df.columns:
            closes[ticker] = df["Close"]
    return pd.DataFrame(closes)


def fetch_next_earnings(ticker: str) -> dict:
    """다음 실적 발표일 및 과거 실적일 반환"""
    try:
        t = yf.Ticker(ticker)
        df = t.earnings_dates
        if df is None or df.empty:
            return {}
        now = pd.Timestamp.now(tz="UTC")
        # tz-aware 인덱스 처리
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        future = df[df.index > now].sort_index()
        past = df[df.index <= now].sort_index()
        result = {}
        if not future.empty:
            next_date = future.index[0]
            result["next_date"] = next_date.strftime("%Y-%m-%d")
            result["days_until"] = (next_date - now).days
        if not past.empty:
            last_date = past.index[-1]
            result["last_date"] = last_date.strftime("%Y-%m-%d")
            row = past.iloc[-1]
            result["last_eps_estimate"] = row.get("EPS Estimate", None)
            result["last_eps_actual"] = row.get("Reported EPS", None)
        return result
    except Exception:
        return {}


def fetch_institutional_holders(ticker: str) -> dict:
    """기관 투자자 보유 비중 반환"""
    try:
        t = yf.Ticker(ticker)
        major = t.major_holders
        inst = t.institutional_holders
        result = {}
        if major is not None and not major.empty:
            # major_holders: 행=비율값, 열=[0(값), 1(레이블)]
            rows = {}
            for _, row in major.iterrows():
                val = row.iloc[0] if len(row) > 0 else None
                label = row.iloc[1] if len(row) > 1 else ""
                rows[str(label)] = val
            result["major"] = rows
        if inst is not None and not inst.empty:
            inst = inst.copy()
            # 상위 10개 기관만
            if "% Out" in inst.columns:
                inst = inst.sort_values("% Out", ascending=False).head(10)
            result["institutional"] = inst.to_dict("records")
        return result
    except Exception:
        return {}


def fetch_macro_data(period: str = "1y") -> dict:
    """매크로 지표 데이터 — yfinance 기반 (API Key 불필요)
    반환: USD/KRW 환율, 미국 10년물 국채 수익률, 달러인덱스(DX-Y.NYB)
    """
    symbols = {
        "USD/KRW": "USDKRW=X",
        "10년물 국채(%)": "^TNX",
        "달러인덱스": "DX-Y.NYB",
    }
    result = {}
    for label, sym in symbols.items():
        try:
            df = yf.download(sym, period=period, auto_adjust=True, progress=False)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            result[label] = df["Close"].dropna()
        except Exception:
            continue
    return result
