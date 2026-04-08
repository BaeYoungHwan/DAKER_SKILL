"""
yfinance 기반 금융 데이터 수집 모듈
Skills/analysis.md 데이터 수집 기준 준수
"""

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


# 기간 선택 기준 (Skills/analysis.md §1)
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
DEFAULT_PERIOD = "1y"


@st.cache_data(ttl=3600)  # 1시간 캐싱 (Skills/analysis.md §4)
def fetch_price(ticker: str, period: str = DEFAULT_PERIOD) -> pd.DataFrame:
    """OHLCV 주가 데이터 조회"""
    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD

    data = yf.download(ticker, period=period, progress=False, auto_adjust=True)

    if data.empty:
        return pd.DataFrame()

    # MultiIndex 컬럼 평탄화 (yfinance >= 0.2.x 대응)
    data = _flatten_columns(data)

    # 결측값 처리: forward fill (Skills/analysis.md §4)
    data = data.ffill()

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
    """여러 종목 주가 데이터 일괄 조회"""
    result = {}
    for ticker in tickers:
        df = fetch_price(ticker, period)
        if not df.empty:
            result[ticker] = df
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
    "삼성전자": "005930.KS",
    "sk하이닉스": "000660.KS",
    "sk 하이닉스": "000660.KS",
    "lg에너지솔루션": "373220.KS",
    "삼성바이오로직스": "207940.KS",
    "현대차": "005380.KS",
    "현대자동차": "005380.KS",
    "기아": "000270.KS",
    "셀트리온": "068270.KS",
    "삼성sdi": "006400.KS",
    "포스코홀딩스": "005490.KS",
    "lg화학": "051910.KS",
    "카카오": "035720.KS",
    "네이버": "035420.KS",
    "삼성물산": "028260.KS",
    "kb금융": "105560.KS",
    "신한지주": "055550.KS",
    "하나금융지주": "086790.KS",
    "sk이노베이션": "096770.KS",
    "sk텔레콤": "017670.KS",
    "lg전자": "066570.KS",
    "현대모비스": "012330.KS",
    "크래프톤": "259960.KS",
    "카카오뱅크": "323410.KS",
    "에코프로비엠": "247540.KQ",
    "에코프로": "086520.KQ",
    "고려아연": "010130.KS",
    "삼성생명": "032830.KS",
    "두산에너빌리티": "034020.KS",
}

# KR_NAME_MAP 역방향: ticker → 한국어 이름
KR_TICKER_TO_NAME: dict[str, str] = {v: k for k, v in KR_NAME_MAP.items()}


def search_ticker(query: str) -> list[dict]:
    """종목명 또는 티커로 검색 (한국어 종목명 + Yahoo Finance 영어 검색 하이브리드)"""
    query_lower = query.lower().strip()
    results: list[dict] = []

    # 1단계: 한국어 종목명 로컬 매핑 검색
    for kr_name, ticker in KR_NAME_MAP.items():
        if query_lower in kr_name or kr_name.startswith(query_lower):
            results.append({
                "symbol": ticker,
                "shortname": kr_name,
                "quoteType": "EQUITY",
            })

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


def get_close_prices(data_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """여러 종목 종가 데이터를 하나의 DataFrame으로 병합"""
    closes = {}
    for ticker, df in data_dict.items():
        if not df.empty and "Close" in df.columns:
            closes[ticker] = df["Close"]
    return pd.DataFrame(closes)
