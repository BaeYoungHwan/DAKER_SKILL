"""
데이터 프로바이더 추상 인터페이스
데이터 소스를 교체하려면 DataProvider를 상속·구현하고
get_provider() 팩토리에서 반환하기만 하면 됩니다.
"""

from abc import ABC, abstractmethod
import pandas as pd


class DataProvider(ABC):
    """금융 데이터 수집 추상 인터페이스.

    현재 구현체: YFinanceProvider (yfinance 기반)
    교체 가능 구현체 예시:
      - AlphaVantageProvider — Alpha Vantage API
      - KrxProvider         — KRX 직접 연동
      - MockProvider        — 테스트용 더미 데이터
    """

    @abstractmethod
    def fetch_price(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """OHLCV 주가 데이터 조회.
        Returns: DataFrame with columns [Open, High, Low, Close, Volume]
        """

    @abstractmethod
    def fetch_info(self, ticker: str) -> dict:
        """종목 기본 정보 및 재무지표 조회.
        Returns: dict with keys [name, sector, industry, pe_ratio, pb_ratio, eps, dividend_yield, currency]
        """

    @abstractmethod
    def fetch_multiple(self, tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
        """여러 종목 주가 데이터 일괄 조회.
        Returns: {ticker: DataFrame} 딕셔너리
        """

    @abstractmethod
    def fetch_financials(self, ticker: str) -> pd.DataFrame:
        """분기별 매출/순이익 데이터 조회.
        Returns: DataFrame with columns [매출, 순이익, 매출총이익], index=분기
        """

    @abstractmethod
    def fetch_dividends(self, ticker: str) -> pd.Series:
        """배당금 히스토리.
        Returns: Series(날짜 → 배당금액)
        """

    @abstractmethod
    def fetch_news(self, ticker: str, max_count: int = 8) -> list[dict]:
        """종목 관련 최신 뉴스.
        Returns: list of {title, url, publisher, pub_time}
        """

    @abstractmethod
    def fetch_earnings(self, ticker: str) -> pd.DataFrame:
        """분기별 EPS 예상치 vs 실제치.
        Returns: DataFrame with columns [EPS Estimate, Reported EPS, Surprise %]
        """

    @abstractmethod
    def fetch_exchange_rate_series(
        self, from_currency: str = "USD", to_currency: str = "KRW", period: str = "1y"
    ) -> pd.Series:
        """환율 시계열 조회.
        Returns: Series(날짜 → 환율)
        """

    @abstractmethod
    def fetch_market_overview(self) -> dict:
        """주요 시장 지수 현황 (현재가 + 전일 대비 변동률).
        Returns: {지수명: {price, change, ticker}}
        """

    @abstractmethod
    def search_ticker(self, query: str) -> list[dict]:
        """종목명 또는 티커 검색.
        Returns: list of {symbol, shortname, quoteType}
        """
