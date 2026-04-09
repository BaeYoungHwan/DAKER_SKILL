"""
YFinanceProvider — DataProvider 인터페이스의 Yahoo Finance 구현체

DataProvider(base.py)를 상속하여 yfinance 기반으로 구현합니다.
다른 데이터 소스로 교체하려면:
  1. DataProvider를 상속하는 새 클래스를 작성
  2. get_provider() 팩토리에서 새 클래스를 반환
  3. fetcher.py 및 app.py의 나머지 코드 변경 불필요
"""

import pandas as pd
from .base import DataProvider
from . import fetcher as _f


class YFinanceProvider(DataProvider):
    """Yahoo Finance 기반 DataProvider 구현체 (yfinance 래퍼).

    내부적으로 fetcher.py 의 캐싱된 함수를 호출합니다.
    Streamlit @st.cache_data 는 모듈 수준 함수에서 관리되므로
    이 클래스는 얇은 위임(delegation) 계층 역할만 수행합니다.
    """

    def fetch_price(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        return _f.fetch_price(ticker, period)

    def fetch_info(self, ticker: str) -> dict:
        return _f.fetch_info(ticker)

    def fetch_multiple(self, tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
        return _f.fetch_multiple(tickers, period)

    def fetch_financials(self, ticker: str) -> pd.DataFrame:
        return _f.fetch_financials(ticker)

    def fetch_dividends(self, ticker: str) -> pd.Series:
        return _f.fetch_dividends(ticker)

    def fetch_news(self, ticker: str, max_count: int = 8) -> list[dict]:
        return _f.fetch_news(ticker, max_count)

    def fetch_earnings(self, ticker: str) -> pd.DataFrame:
        return _f.fetch_earnings(ticker)

    def fetch_exchange_rate_series(
        self, from_currency: str = "USD", to_currency: str = "KRW", period: str = "1y"
    ) -> pd.Series:
        return _f.fetch_exchange_rate_series(from_currency, to_currency, period)

    def fetch_market_overview(self) -> dict:
        return _f.fetch_market_overview()

    def search_ticker(self, query: str) -> list[dict]:
        return _f.search_ticker(query)


# ── 팩토리 함수 ───────────────────────────────────────────────────────────────

_provider_instance: DataProvider | None = None


def get_provider() -> DataProvider:
    """DataProvider 싱글턴 반환.

    데이터 소스 교체 시 이 함수 내부만 수정하면 됩니다.
    예시:
        return AlphaVantageProvider(api_key=os.environ["AV_KEY"])
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = YFinanceProvider()
    return _provider_instance
