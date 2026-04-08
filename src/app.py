"""
금융 투자 대시보드 — Streamlit 메인 앱
Skills/analysis.md + Skills/visualization.md + Skills/insight.md 기준 준수
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd

from data.fetcher import fetch_price, fetch_info, fetch_multiple, get_close_prices, VALID_PERIODS
from analysis.indicators import (
    calc_returns, calc_cumulative_return, calc_annualized_return,
    calc_moving_averages, calc_rsi, calc_bollinger_bands,
    calc_volatility, calc_sharpe_ratio, calc_max_drawdown,
    calc_correlation_matrix, get_rsi_signal,
)
from viz.charts import (
    candlestick_chart, line_chart_multi,
    portfolio_pie, correlation_heatmap, rsi_chart,
)

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="금융 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 투자 대시보드")
    st.divider()

    # 종목 입력
    st.subheader("종목 설정")
    tickers_input = st.text_input(
        "티커 입력 (쉼표 구분)",
        value="AAPL, MSFT, GOOGL",
        help="예: AAPL, MSFT, 005930.KS (삼성전자)",
    )
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    # 기간 선택
    period = st.selectbox(
        "분석 기간",
        options=VALID_PERIODS,
        index=VALID_PERIODS.index("1y"),
        format_func=lambda x: {
            "1mo": "1개월", "3mo": "3개월", "6mo": "6개월",
            "1y": "1년", "2y": "2년", "5y": "5년"
        }[x],
    )

    # 주 종목 선택
    main_ticker = st.selectbox("주 분석 종목", options=tickers) if tickers else None

    # 이동평균 옵션
    st.divider()
    st.subheader("차트 옵션")
    show_ma = st.multiselect("이동평균선", ["MA5", "MA20", "MA60", "MA120", "MA200"], default=["MA20", "MA60"])
    show_bb = st.checkbox("볼린저 밴드", value=True)

    st.divider()
    st.caption("데이터: Yahoo Finance (yfinance)")

# ── 메인 영역 ────────────────────────────────────────────────
if not tickers:
    st.warning("사이드바에서 종목을 입력해주세요.")
    st.stop()

# 데이터 로딩
with st.spinner("데이터 로딩 중..."):
    all_data = fetch_multiple(tickers, period)

if not all_data:
    st.error("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")
    st.stop()

main_df = all_data.get(main_ticker, next(iter(all_data.values())))
close = main_df["Close"]

# ── KPI 카드 (Skills/visualization.md §3.2) ──────────────────
st.subheader("핵심 지표")
col1, col2, col3, col4 = st.columns(4)

current_price = close.iloc[-1]
prev_price = close.iloc[-2]
daily_change = (current_price - prev_price) / prev_price * 100
cum_return = calc_cumulative_return(close).iloc[-1]
volatility = calc_volatility(close)["annual_volatility"]
sharpe = calc_sharpe_ratio(close)

col1.metric("현재가", f"${current_price:,.2f}", f"{daily_change:+.2f}%")
col2.metric("누적 수익률", f"{cum_return:+.2f}%")
col3.metric("연환산 변동성", f"{volatility:.1f}%")
col4.metric("샤프 비율", f"{sharpe:.2f}", help="1 이상: 양호, 2 이상: 우수")

st.divider()

# ── 주가 차트 + 포트폴리오 비중 ──────────────────────────────
col_chart, col_pie = st.columns([2, 1])

with col_chart:
    mas = calc_moving_averages(close)
    selected_mas = {k: v for k, v in mas.items() if k in show_ma}
    bb = calc_bollinger_bands(close) if show_bb else None
    st.plotly_chart(
        candlestick_chart(main_df, main_ticker, selected_mas, bb),
        use_container_width=True,
    )

with col_pie:
    # 포트폴리오 비중: 각 종목 현재가 기준 균등 배분 (시연용)
    weights = {t: 100 / len(all_data) for t in all_data}
    st.plotly_chart(portfolio_pie(weights), use_container_width=True)

# ── 수익률 비교 + RSI ─────────────────────────────────────────
col_ret, col_rsi = st.columns(2)

with col_ret:
    close_prices = get_close_prices(all_data)
    if not close_prices.empty:
        st.plotly_chart(line_chart_multi(close_prices, "누적 수익률 비교"), use_container_width=True)

with col_rsi:
    rsi_values = calc_rsi(close)
    st.plotly_chart(rsi_chart(rsi_values, main_ticker), use_container_width=True)

# ── 상관관계 히트맵 (종목 2개 이상) ──────────────────────────
if len(all_data) >= 2:
    close_prices = get_close_prices(all_data)
    corr = calc_correlation_matrix(close_prices)
    st.plotly_chart(correlation_heatmap(corr), use_container_width=True)

# ── 인사이트 (Skills/insight.md §2, §3) ──────────────────────
st.divider()
st.subheader("📊 투자 인사이트")

insights = []

# RSI 신호
latest_rsi = rsi_values.dropna().iloc[-1]
rsi_signal = get_rsi_signal(latest_rsi)
if rsi_signal == "과매수":
    insights.append(("🔴 High", "과매수 구간 진입 (RSI)", f"RSI = {latest_rsi:.1f}", "단기 차익실현 고려 구간"))
elif rsi_signal == "과매도":
    insights.append(("🟢 High", "과매도 구간 진입 (RSI)", f"RSI = {latest_rsi:.1f}", "저점 매수 기회 탐색 구간"))

# 샤프 비율 평가
if sharpe > 2:
    insights.append(("🟢 Medium", "우수한 위험 대비 수익률", f"샤프 비율 = {sharpe:.2f}", "현재 전략 유지"))
elif sharpe < 1:
    insights.append(("🟡 Medium", "위험 대비 수익률 개선 필요", f"샤프 비율 = {sharpe:.2f}", "포트폴리오 재검토 고려"))

# MDD 경고
mdd = calc_max_drawdown(close)
if mdd < -20:
    insights.append(("🔴 High", "큰 낙폭 기록", f"최대 낙폭(MDD) = {mdd:.1f}%", "손절 기준 재검토 권장"))

if insights:
    for badge, title, signal, action in insights:
        with st.expander(f"{badge} — {title}"):
            st.write(f"**신호:** {signal}")
            st.write(f"**행동 제안:** {action}")
else:
    st.info("현재 특이 신호 없음 — 정상 범위 내 거래 중")
