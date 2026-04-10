"""
yfinance 기반 금융 데이터 수집 모듈
Skills/analysis.md 데이터 수집 기준 준수
"""

import logging
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
import pandas as pd
import requests
import streamlit as st
from typing import Optional
from skills.parser import load_kr_symbols

_logger = logging.getLogger(__name__)


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


def _download_and_clean(
    ticker: str,
    period: str,
    *,
    retries: int = 1,
    apply_outlier_filter: bool = False,
) -> pd.DataFrame:
    """yf.download → flatten → ffill → (optional) clean_outliers 통합 파이프라인."""
    df = pd.DataFrame()
    for attempt in range(retries):
        try:
            df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if not df.empty:
                break
        except Exception as e:
            _logger.debug("_download_and_clean(%s) attempt %d failed: %s", ticker, attempt, e)
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    if df.empty:
        return pd.DataFrame()
    df = _flatten_columns(df)
    df = df.ffill()
    if apply_outlier_filter:
        df = _clean_price_outliers(df)
    return df


def _strip_tz(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """timezone 정보 제거 — tz-aware 인덱스를 tz-naive로 변환."""
    if hasattr(index, "tz") and index.tz is not None:
        return index.tz_localize(None)
    return index


# 기간 선택 기준 (Skills/analysis.md §1)
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
DEFAULT_PERIOD = "1y"

# 주요 시장 지수 티커 매핑
_MAJOR_INDICES: dict[str, str] = {
    "S&P 500": "^GSPC",
    "NASDAQ":  "^IXIC",
    "DOW JONES": "^DJI",
    "KOSPI":   "^KS11",
}
_OVERVIEW_INDICES: dict[str, str] = {**_MAJOR_INDICES, "VIX": "^VIX"}


@st.cache_data(ttl=3600)  # 1시간 캐싱 (Skills/analysis.md §4)
def fetch_price(ticker: str, period: str = DEFAULT_PERIOD) -> pd.DataFrame:
    """OHLCV 주가 데이터 조회 (Rate Limit 대응: 최대 3회 재시도)"""
    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD
    return _download_and_clean(ticker, period, retries=3, apply_outlier_filter=True)


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
    """여러 종목 주가 데이터 병렬 조회 (ThreadPoolExecutor — 최대 5개 동시 요청, Rate Limit 방지)"""
    if not tickers:
        return {}

    def _fetch_one(ticker: str) -> tuple[str, pd.DataFrame]:
        return ticker, fetch_price(ticker, period)

    result = {}
    max_workers = min(len(tickers), 5)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            try:
                ticker, df = future.result()
                if not df.empty:
                    result[ticker] = df
            except Exception as e:
                _logger.debug("fetch_multiple future failed: %s", e)
    return result


@st.cache_data(ttl=3600)
def fetch_market_indices(period: str = DEFAULT_PERIOD) -> dict[str, pd.DataFrame]:
    """주요 시장 지수 조회 (S&P500, NASDAQ, KOSPI)"""
    return fetch_multiple(list(_MAJOR_INDICES.values()), period)


@st.cache_data(ttl=3600)
def fetch_exchange_rate_series(from_currency: str = "USD", to_currency: str = "KRW", period: str = DEFAULT_PERIOD) -> pd.Series:
    """환율 시계열 조회 (예: USDKRW=X). 원화 환산 포트폴리오 비교에 사용."""
    try:
        ticker = f"{from_currency}{to_currency}=X"
        df = _download_and_clean(ticker, period)
        if df.empty:
            return pd.Series(dtype=float)
        return df["Close"]
    except Exception:
        return pd.Series(dtype=float)


# 한국어 종목명 → yfinance 티커 매핑 (Skills/symbols.json 에서 런타임 로드)
KR_NAME_MAP: dict[str, str] = load_kr_symbols()

# KR_TICKER_TO_NAME 역방향: ticker → 한국어 이름 (공식명 우선 = 더 긴 이름)
KR_TICKER_TO_NAME: dict[str, str] = {}
for _kr_name, _ticker in KR_NAME_MAP.items():
    if _ticker not in KR_TICKER_TO_NAME or len(_kr_name) > len(KR_TICKER_TO_NAME[_ticker]):
        KR_TICKER_TO_NAME[_ticker] = _kr_name


# ── 레버리지·인버스 ETF 감지 ─────────────────────────────────────────────────

# 미국 대표 레버리지·인버스 ETF 티커 목록
_LEVERAGED_TICKERS: set[str] = {
    # 레버리지 (2x·3x)
    "TQQQ", "UPRO", "UDOW", "URTY", "SPXL", "TECL", "LABU", "FNGU", "TNA", "HIBL",
    "ERX", "NUGT", "JNUG", "YINN", "CURE", "DFEN", "FAS", "DPST",
    # 인버스·숏
    "SQQQ", "SPXU", "SDOW", "SRTY", "SPXS", "TECS", "LABD", "FNGD", "TZA", "HIBS",
    "ERY", "DUST", "JDST", "YANG", "FAZ", "SDS", "SH", "PSQ", "DOG", "RWM",
    # 국내 레버리지·인버스 ETF (KRX)
    "122630.KS",  # KODEX 레버리지
    "233740.KS",  # KODEX 코스닥150레버리지
    "252670.KS",  # KODEX 200선물인버스2X
    "251340.KS",  # KODEX 코스닥150선물인버스
}

_INVERSE_TICKERS: set[str] = {
    "SQQQ", "SPXU", "SDOW", "SRTY", "SPXS", "TECS", "LABD", "FNGD", "TZA", "HIBS",
    "ERY", "DUST", "JDST", "YANG", "FAZ", "SDS", "SH", "PSQ", "DOG", "RWM",
    "252670.KS", "251340.KS",
}

# 이름 기반 패턴 (ETF 이름에 포함 시 감지)
_LEV_NAME_PATTERN = re.compile(
    r"\b(2x|3x|ultra|ultrapro|proshares|direxion|leveraged|inverse|bear|short|인버스|레버리지)\b",
    re.IGNORECASE,
)


def classify_position(ticker: str, name: str = "") -> dict:
    """레버리지·인버스 ETF 여부 및 공매도(숏) 포지션 특성 반환.

    Returns:
        {
          "leveraged": bool,   # 레버리지 ETF 여부
          "inverse": bool,     # 인버스(방향 반대) ETF 여부
          "warning": str | None  # UI에 표시할 경고 메시지
        }
    """
    ticker_up = ticker.upper()
    name_match = bool(_LEV_NAME_PATTERN.search(name or ""))
    is_lev = ticker_up in _LEVERAGED_TICKERS or name_match
    is_inv = ticker_up in _INVERSE_TICKERS or (
        name_match and bool(re.search(r"\b(inverse|bear|short|인버스)\b", name or "", re.IGNORECASE))
    )

    warning = None
    if is_inv:
        warning = f"⚠️ **{ticker}**는 인버스(숏) ETF입니다. 기초자산 하락 시 수익, 상승 시 손실이 발생합니다."
    elif is_lev:
        warning = f"⚠️ **{ticker}**는 레버리지 ETF입니다. 변동성 비용(Volatility Decay)으로 장기 보유 시 추가 손실이 발생할 수 있습니다."

    return {"leveraged": is_lev, "inverse": is_inv, "warning": warning}


def _search_naver_finance(query: str) -> list[dict]:
    """Naver Finance 자동완성 API로 한국 종목 동적 검색.

    Returns: list of {symbol, shortname, quoteType}
    """
    try:
        encoded = urllib.parse.quote(query, encoding="utf-8")
        url = f"https://ac.finance.naver.com/ac?q={encoded}&q_enc=utf-8&target=stock&sm=all&st=0&ie=utf-8&type=stock"
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        data = resp.json()
        # items[0] = 자동완성 결과 리스트 [이름, 코드, 시장, ...]
        items = data.get("items", [[]])[0]
        results = []
        seen: set[str] = set()
        for item in items[:10]:
            if len(item) < 2:
                continue
            kr_name = item[0]
            code = item[1]
            market = item[2] if len(item) > 2 else ""
            # 시장 구분: 코스닥 → .KQ, 나머지(코스피·ETF 등) → .KS
            suffix = ".KQ" if "코스닥" in market else ".KS"
            symbol = f"{code}{suffix}"
            if symbol in seen:
                continue
            seen.add(symbol)
            results.append({"symbol": symbol, "shortname": kr_name, "quoteType": "EQUITY"})
        return results
    except Exception:
        return []


def search_ticker(query: str) -> list[dict]:
    """종목명 또는 티커로 검색 (한국어·영어 하이브리드).

    검색 순서:
      1. KR_NAME_MAP 로컬 매핑 (하드코딩된 주요 한국 종목)
      2. Naver Finance 자동완성 API (한국어 쿼리 → 전체 KRX 커버)
      3. Yahoo Finance 영어 검색 (ASCII 쿼리)
    """
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

    # 2단계: 한국어 쿼리 → Naver Finance 자동완성 (KRX 전체 커버)
    if not query.isascii():
        naver_results = _search_naver_finance(query)
        for r in naver_results:
            if r["symbol"] not in seen_tickers:
                # KR_TICKER_TO_NAME에 공식 한국어 이름이 있으면 우선 사용
                if r["symbol"] in KR_TICKER_TO_NAME:
                    r["shortname"] = KR_TICKER_TO_NAME[r["symbol"]]
                results.append(r)
                seen_tickers.add(r["symbol"])

    # 3단계: Yahoo Finance 영어 검색 (ASCII 쿼리만)
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
        except Exception as e:
            _logger.debug("search_ticker Yahoo API failed for %r: %s", query, e)

    return results[:8]


@st.cache_data(ttl=300)  # 5분 캐싱 (시장 데이터 자주 갱신)
def fetch_market_overview() -> dict:
    """주요 시장 지수 현황 (현재가 + 전일 대비 변동률)"""
    result = {}
    items = list(_OVERVIEW_INDICES.items())
    for i, (name, ticker) in enumerate(items):
        try:
            df = _download_and_clean(ticker, "5d")
            if df.empty or len(df) < 2:
                continue
            curr = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg = (curr - prev) / prev * 100
            result[name] = {"price": curr, "change": round(chg, 2), "ticker": ticker}
        except Exception:
            pass
        if i < len(items) - 1:
            time.sleep(0.2)
    return result


# 공포/탐욕 지수 레이블 임계값
_FG_EXTREME_GREED = 75
_FG_GREED         = 55
_FG_NEUTRAL_HIGH  = 45
_FG_FEAR          = 25


def _fg_vix_score(vix: pd.Series) -> "float | None":
    """VIX 기반 공포/탐욕 점수 (역방향: VIX 낮을수록 탐욕)."""
    if len(vix) < 2:
        return None
    vix_now, vmin, vmax = float(vix.iloc[-1]), float(vix.min()), float(vix.max())
    return 100 - ((vix_now - vmin) / (vmax - vmin) * 100) if vmax > vmin else 50.0


def _fg_momentum_score(sp_close: pd.Series) -> "float | None":
    """S&P500 125일 이평 대비 모멘텀 점수."""
    if len(sp_close) < 126:
        return None
    ma125 = float(sp_close.rolling(125).mean().dropna().iloc[-1])
    ratio = (float(sp_close.iloc[-1]) / ma125 - 1) * 100
    return float(min(max(50 + ratio * 5, 0), 100))


def _fg_bb_score(sp_close: pd.Series) -> "float | None":
    """볼린저 밴드 폭 기반 점수 (좁을수록 낮은 불확실성 = 탐욕)."""
    if len(sp_close) < 21:
        return None
    bb_width = (sp_close.rolling(20).std() / sp_close.rolling(20).mean() * 100).dropna()
    bw_now, bwmin, bwmax = float(bb_width.iloc[-1]), float(bb_width.min()), float(bb_width.max())
    return 100 - ((bw_now - bwmin) / (bwmax - bwmin) * 100) if bwmax > bwmin else 50.0


def _fg_label(score: float) -> str:
    """점수 → 공포/탐욕 레이블."""
    if score >= _FG_EXTREME_GREED:
        return "극단적 탐욕"
    if score >= _FG_GREED:
        return "탐욕"
    if score >= _FG_NEUTRAL_HIGH:
        return "중립"
    if score >= _FG_FEAR:
        return "공포"
    return "극단적 공포"


@st.cache_data(ttl=600)  # 10분 캐싱
def fetch_fear_greed() -> dict:
    """yfinance 지표 기반 자체 계산 공포/탐욕 지수 (0=극단공포, 100=극단탐욕)"""
    def _get_close(ticker: str) -> pd.Series:
        df = _download_and_clean(ticker, "1y", retries=2)
        if df.empty:
            return pd.Series(dtype=float)
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.dropna()

    sp_close = _get_close("^GSPC")
    vix_close = _get_close("^VIX")

    scores: list[tuple[str, float, float]] = []

    vix_score = _fg_vix_score(vix_close)
    if vix_score is not None:
        scores.append(("vix", vix_score, 0.4))

    mom_score = _fg_momentum_score(sp_close)
    if mom_score is not None:
        scores.append(("mom", mom_score, 0.4))

    bb_score = _fg_bb_score(sp_close)
    if bb_score is not None:
        scores.append(("bw", bb_score, 0.2))

    if not scores:
        return {"score": 50, "label": "중립", "vix": None}

    total_weight = sum(w for _, _, w in scores)
    score = round(float(min(max(sum(s * w for _, s, w in scores) / total_weight, 0), 100)), 1)
    vix_val = round(float(vix_close.iloc[-1]), 2) if not vix_close.empty else None

    return {"score": score, "label": _fg_label(score), "vix": vix_val}


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
        div.index = _strip_tz(div.index)
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
            df = _download_and_clean(sym, period)
            if df.empty:
                continue
            df.index = _strip_tz(df.index)
            result[label] = df["Close"].dropna()
        except Exception:
            continue
    return result
