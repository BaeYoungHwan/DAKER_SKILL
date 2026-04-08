"""
yfinance 기반 금융 데이터 수집 모듈
Skills/analysis.md 데이터 수집 기준 준수
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from typing import Optional


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


def get_close_prices(data_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """여러 종목 종가 데이터를 하나의 DataFrame으로 병합"""
    closes = {}
    for ticker, df in data_dict.items():
        if not df.empty and "Close" in df.columns:
            closes[ticker] = df["Close"]
    return pd.DataFrame(closes)
