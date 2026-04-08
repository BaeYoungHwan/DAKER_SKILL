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
    calc_correlation_matrix, get_rsi_signal, detect_golden_cross,
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

    st.subheader("종목 설정")
    tickers_input = st.text_input(
        "티커 입력 (쉼표 구분)",
        value="AAPL, MSFT, GOOGL",
        help="예: AAPL, MSFT, 005930.KS (삼성전자), SPY (S&P500 ETF)",
    )
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    period = st.selectbox(
        "분석 기간",
        options=VALID_PERIODS,
        index=VALID_PERIODS.index("1y"),
        format_func=lambda x: {
            "1mo": "1개월", "3mo": "3개월", "6mo": "6개월",
            "1y": "1년", "2y": "2년", "5y": "5년"
        }[x],
    )

    main_ticker = st.selectbox("주 분석 종목", options=tickers) if tickers else None

    st.divider()
    st.subheader("차트 옵션")
    show_ma = st.multiselect("이동평균선", ["MA5", "MA20", "MA60", "MA120", "MA200"], default=["MA20", "MA60"])
    show_bb = st.checkbox("볼린저 밴드", value=True)
    show_benchmark = st.checkbox("S&P500 벤치마크 비교", value=True)

    st.divider()
    st.subheader("포트폴리오 비중 (%)")
    weights_input = {}
    if tickers:
        equal_w = round(100 / len(tickers), 1)
        for t in tickers:
            weights_input[t] = st.number_input(t, min_value=0.0, max_value=100.0, value=equal_w, step=0.5)
        total_w = sum(weights_input.values())
        if abs(total_w - 100) > 1.0:
            st.warning(f"비중 합계: {total_w:.1f}%")
        else:
            st.caption(f"합계: {total_w:.1f}%")

    st.divider()
    st.caption("데이터: Yahoo Finance (yfinance) — API Key 불필요")

# ── 메인 ────────────────────────────────────────────────────
if not tickers:
    st.warning("사이드바에서 종목을 입력해주세요.")
    st.stop()

with st.spinner("데이터 로딩 중..."):
    all_data = fetch_multiple(tickers, period)
    info_data = {t: fetch_info(t) for t in tickers}
    benchmark_data = fetch_price("^GSPC", period) if show_benchmark else pd.DataFrame()

if not all_data:
    st.error("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")
    st.stop()

if main_ticker not in all_data:
    main_ticker = next(iter(all_data))

main_df = all_data[main_ticker]
close = main_df["Close"]

currency = info_data.get(main_ticker, {}).get("currency", "USD")
currency_sym = "₩" if currency == "KRW" else ("¥" if currency == "JPY" else "$")

# ── KPI ──────────────────────────────────────────────────────
current_price = float(close.iloc[-1])
prev_price = float(close.iloc[-2])
daily_change = (current_price - prev_price) / prev_price * 100
cum_return = float(calc_cumulative_return(close).iloc[-1])
ann_return = calc_annualized_return(close)
volatility = calc_volatility(close)["annual_volatility"]
sharpe = calc_sharpe_ratio(close)
mdd = calc_max_drawdown(close)

if currency == "KRW" or current_price >= 1000:
    price_str = f"{currency_sym}{current_price:,.0f}"
else:
    price_str = f"{currency_sym}{current_price:.2f}"

# ── 탭 구조 ──────────────────────────────────────────────────
tab_main, tab_portfolio, tab_compare, tab_insight = st.tabs([
    "📊 종목 분석", "💼 포트폴리오", "📈 비교 분석", "💡 투자 인사이트"
])

# ══════════════════════════════════════════════════════════════
# 탭 1: 종목 분석
# ══════════════════════════════════════════════════════════════
with tab_main:
    # KPI 카드
    st.subheader(f"{main_ticker} 핵심 지표")
    info = info_data.get(main_ticker, {})
    name = info.get("name", main_ticker)
    sector = info.get("sector", "N/A")
    st.caption(f"**{name}** | {sector} | {info.get('industry', 'N/A')}")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("현재가", price_str, f"{daily_change:+.2f}%")
    col2.metric("누적 수익률", f"{cum_return:+.1f}%", help=f"연환산: {ann_return:+.1f}%")
    col3.metric("연환산 변동성", f"{volatility:.1f}%")
    col4.metric("샤프 비율", f"{sharpe:.2f}", help="≥2: 우수 / ≥1: 양호 / <1: 검토")
    col5.metric("최대 낙폭(MDD)", f"{mdd:.1f}%")

    # 재무 지표 보조 행
    fin_cols = st.columns(4)
    if info.get("pe_ratio"):
        fin_cols[0].metric("PER", f"{info['pe_ratio']:.1f}x")
    if info.get("pb_ratio"):
        fin_cols[1].metric("PBR", f"{info['pb_ratio']:.2f}x")
    if info.get("eps"):
        fin_cols[2].metric("EPS", f"{info['eps']:.2f}")
    if info.get("dividend_yield"):
        fin_cols[3].metric("배당수익률", f"{info['dividend_yield']:.2f}%")

    st.divider()

    # 캔들스틱 차트
    mas = calc_moving_averages(close)
    selected_mas = {k: v for k, v in mas.items() if k in show_ma}
    bb = calc_bollinger_bands(close) if show_bb else None
    st.plotly_chart(
        candlestick_chart(main_df, main_ticker, selected_mas, bb),
        width="stretch",
    )

    # RSI 차트
    rsi_values = calc_rsi(close)
    st.plotly_chart(rsi_chart(rsi_values, main_ticker), width="stretch")

    # 원시 데이터
    with st.expander("📋 최근 30일 데이터"):
        st.dataframe(
            main_df.tail(30).sort_index(ascending=False).style.format("{:.2f}"),
            width="stretch",
        )

# ══════════════════════════════════════════════════════════════
# 탭 2: 포트폴리오
# ══════════════════════════════════════════════════════════════
with tab_portfolio:
    st.subheader("포트폴리오 분석")

    valid_weights = {t: w for t, w in weights_input.items() if t in all_data and w > 0}
    if not valid_weights:
        valid_weights = {t: 100 / len(all_data) for t in all_data}

    col_pie, col_stats = st.columns([1, 1])

    with col_pie:
        st.plotly_chart(portfolio_pie(valid_weights), width="stretch")

    with col_stats:
        st.subheader("종목별 성과")
        rows = []
        for t in all_data:
            c = all_data[t]["Close"]
            rows.append({
                "종목": t,
                "현재가": f"{float(c.iloc[-1]):.2f}",
                "누적수익률(%)": f"{float(calc_cumulative_return(c).iloc[-1]):+.1f}",
                "변동성(%)": f"{calc_volatility(c)['annual_volatility']:.1f}",
                "샤프": f"{calc_sharpe_ratio(c):.2f}",
                "MDD(%)": f"{calc_max_drawdown(c):.1f}",
                "비중(%)": f"{valid_weights.get(t, 0):.1f}",
            })
        st.dataframe(pd.DataFrame(rows).set_index("종목"), width="stretch")

    # 포트폴리오 가중 수익률
    if len(all_data) >= 2:
        st.divider()
        close_prices = get_close_prices(all_data)
        total_w_sum = sum(valid_weights.values())
        if total_w_sum > 0:
            port_return = sum(
                calc_cumulative_return(close_prices[t]) * (valid_weights.get(t, 0) / total_w_sum)
                for t in close_prices.columns if t in valid_weights
            )
            st.subheader("포트폴리오 가중 누적 수익률")
            port_df = pd.DataFrame({"포트폴리오": port_return})
            if not benchmark_data.empty:
                port_df["S&P500"] = calc_cumulative_return(benchmark_data["Close"])
            st.plotly_chart(
                line_chart_multi(port_df, "포트폴리오 vs 벤치마크", normalize=False),
                width="stretch",
            )

        # 상관관계 히트맵
        if len(all_data) >= 2:
            corr = calc_correlation_matrix(close_prices)
            st.plotly_chart(correlation_heatmap(corr), width="stretch")

# ══════════════════════════════════════════════════════════════
# 탭 3: 비교 분석
# ══════════════════════════════════════════════════════════════
with tab_compare:
    st.subheader("종목 수익률 비교")

    close_prices = get_close_prices(all_data)

    # 벤치마크 포함 비교
    compare_df = close_prices.copy()
    if show_benchmark and not benchmark_data.empty:
        compare_df["S&P500"] = benchmark_data["Close"]

    st.plotly_chart(
        line_chart_multi(compare_df, "누적 수익률 비교 (기간 시작점 = 0%)"),
        width="stretch",
    )

    # 기간별 수익률 테이블
    st.subheader("기간별 수익률 (%)")
    period_returns = []
    compare_tickers = list(all_data.keys())
    if show_benchmark and not benchmark_data.empty:
        compare_tickers.append("S&P500")

    for t in compare_tickers:
        if t == "S&P500":
            c = benchmark_data["Close"] if not benchmark_data.empty else None
        else:
            c = all_data[t]["Close"] if t in all_data else None
        if c is None or c.empty:
            continue
        row = {"종목": t}
        for label, days in [("1개월", 21), ("3개월", 63), ("6개월", 126), ("1년", 252)]:
            if len(c) >= days:
                ret = (float(c.iloc[-1]) / float(c.iloc[-days]) - 1) * 100
                row[label] = f"{ret:+.1f}%"
            else:
                row[label] = "N/A"
        row["기간 전체"] = f"{float(calc_cumulative_return(c).iloc[-1]):+.1f}%"
        period_returns.append(row)

    if period_returns:
        st.dataframe(pd.DataFrame(period_returns).set_index("종목"), width="stretch")

# ══════════════════════════════════════════════════════════════
# 탭 4: 투자 인사이트
# ══════════════════════════════════════════════════════════════
with tab_insight:
    st.subheader("💡 자동 생성 투자 인사이트")
    st.caption("Skills/insight.md 규칙 기반 자동 분석")

    rsi_values = calc_rsi(close)
    insights = []

    # RSI 신호
    latest_rsi = float(rsi_values.dropna().iloc[-1])
    rsi_signal = get_rsi_signal(latest_rsi)
    if rsi_signal == "과매수":
        insights.append(("🔴", "High", "과매수 구간 진입 (RSI)", f"RSI = {latest_rsi:.1f} (기준: >70)", "단기 차익실현 고려. 포지션 축소 검토."))
    elif rsi_signal == "과매도":
        insights.append(("🟢", "High", "과매도 구간 진입 (RSI)", f"RSI = {latest_rsi:.1f} (기준: <30)", "저점 매수 기회 탐색. 분할 매수 고려."))
    else:
        insights.append(("🔵", "Info", "RSI 중립 구간", f"RSI = {latest_rsi:.1f} (30~70)", "특이 신호 없음. 추세 방향 확인 권장."))

    # 골든크로스 / 데드크로스
    mas_all = calc_moving_averages(close)
    gc = detect_golden_cross(mas_all["MA20"], mas_all["MA60"])
    if gc is not None:
        days_ago = (close.index[-1] - gc).days
        if days_ago <= 30:
            insights.append(("🟢", "Medium", f"골든크로스 발생 ({days_ago}일 전)", "MA20이 MA60 상향 돌파", "중기 상승 추세 진입 신호. 추세 추종 전략 고려."))
        elif days_ago <= 90:
            insights.append(("🔵", "Info", f"골든크로스 유지 중 ({days_ago}일 전 발생)", "MA20 > MA60 상태 유지", "중기 강세 추세 지속. 모니터링 권장."))

    # 데드크로스 확인 (골든크로스 역방향)
    dc = detect_golden_cross(mas_all["MA60"], mas_all["MA20"])  # MA60이 MA20 상향 돌파 = 데드크로스
    if dc is not None:
        days_ago_dc = (close.index[-1] - dc).days
        if days_ago_dc <= 30:
            insights.append(("🔴", "High", f"데드크로스 발생 ({days_ago_dc}일 전)", "MA20이 MA60 하향 돌파", "중기 약세 추세 진입. 손절선 재검토 권장."))

    # 볼린저 밴드 이탈
    bb_data = calc_bollinger_bands(close)
    last_price = float(close.iloc[-1])
    upper = float(bb_data["upper"].iloc[-1]) if not pd.isna(bb_data["upper"].iloc[-1]) else None
    lower = float(bb_data["lower"].iloc[-1]) if not pd.isna(bb_data["lower"].iloc[-1]) else None
    if upper and last_price > upper:
        insights.append(("🟡", "Medium", "볼린저 밴드 상단 돌파", f"현재가 {price_str} > 상단 ${upper:.2f}", "과열 신호. 단기 조정 가능성 모니터링."))
    elif lower and last_price < lower:
        insights.append(("🟡", "Medium", "볼린저 밴드 하단 이탈", f"현재가 {price_str} < 하단 ${lower:.2f}", "과매도 영역. 반등 탐색 구간."))

    # 샤프 비율
    if sharpe >= 2:
        insights.append(("🟢", "Medium", "우수한 위험 대비 수익률", f"샤프 비율 = {sharpe:.2f} (≥2)", "현재 전략 유지. 비중 확대 고려."))
    elif sharpe < 0:
        insights.append(("🔴", "Medium", "마이너스 위험 대비 수익률", f"샤프 비율 = {sharpe:.2f} (<0)", "포트폴리오 재검토 필요. 헤지 전략 고려."))
    elif sharpe < 1:
        insights.append(("🟡", "Medium", "위험 대비 수익률 개선 필요", f"샤프 비율 = {sharpe:.2f} (<1)", "분산투자 또는 저변동성 자산 편입 고려."))

    # MDD
    if mdd < -30:
        insights.append(("🔴", "High", "심각한 낙폭 기록", f"MDD = {mdd:.1f}% (기준: <-30%)", "리스크 관리 긴급 검토. 손절선 재설정 권장."))
    elif mdd < -20:
        insights.append(("🟡", "Medium", "주의 낙폭 기록", f"MDD = {mdd:.1f}% (기준: <-20%)", "포트폴리오 리밸런싱 검토 권장."))

    # S&P500 대비 성과
    if show_benchmark and not benchmark_data.empty:
        sp_cum = float(calc_cumulative_return(benchmark_data["Close"]).iloc[-1])
        diff = cum_return - sp_cum
        if diff > 10:
            insights.append(("🟢", "Medium", f"S&P500 대비 초과 수익 ({diff:+.1f}%p)", f"종목: {cum_return:+.1f}% vs S&P500: {sp_cum:+.1f}%", "시장 대비 우수한 성과. 전략 유지."))
        elif diff < -10:
            insights.append(("🟡", "Medium", f"S&P500 대비 저조한 성과 ({diff:+.1f}%p)", f"종목: {cum_return:+.1f}% vs S&P500: {sp_cum:+.1f}%", "인덱스 ETF 편입 비교 검토 권장."))

    # 우선순위 정렬 및 출력
    priority_order = {"High": 0, "Medium": 1, "Info": 2}
    insights.sort(key=lambda x: priority_order.get(x[1], 3))

    for emoji, priority, title, signal, action in insights:
        expanded = priority == "High"
        with st.expander(f"{emoji} **[{priority}]** {title}", expanded=expanded):
            col_s, col_a = st.columns(2)
            col_s.markdown(f"**📡 신호**  \n{signal}")
            col_a.markdown(f"**🎯 행동 제안**  \n{action}")

    # 종합 요약
    st.divider()
    high_count = sum(1 for _, p, *_ in insights if p == "High")
    medium_count = sum(1 for _, p, *_ in insights if p == "Medium")
    st.info(f"**분석 요약:** 총 {len(insights)}개 신호 감지 — 🔴 High: {high_count}개 / 🟡 Medium: {medium_count}개")

    # 자동 텍스트 리포트 (Skills/insight.md §4 리포트 흐름)
    st.divider()
    st.subheader("📄 자동 생성 투자 리포트")

    info_r = info_data.get(main_ticker, {})
    analysis_date = pd.Timestamp.now().strftime("%Y년 %m월 %d일")
    period_label = {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년", "2y": "2년", "5y": "5년"}.get(period, period)

    # 전반적 평가
    if high_count >= 2:
        overall = "⚠️ 주의 필요 — 복수의 High 신호 발생 중"
        overall_detail = "리스크 관리와 포지션 재검토가 권장됩니다."
    elif high_count == 1:
        overall = "🔶 모니터링 필요 — 1개의 High 신호 발생"
        overall_detail = "해당 신호를 중심으로 전략을 점검하세요."
    elif medium_count >= 2:
        overall = "🟡 일부 주의 — Medium 신호 다수"
        overall_detail = "단기 변동 가능성이 있습니다. 분산 관리 권장."
    else:
        overall = "✅ 안정적 — 특이 신호 없음"
        overall_detail = "현재 전략을 유지하되 정기적 모니터링을 권장합니다."

    sp_line = ""
    if show_benchmark and not benchmark_data.empty:
        sp_cum_r = float(calc_cumulative_return(benchmark_data["Close"]).iloc[-1])
        alpha = cum_return - sp_cum_r
        sp_line = f"- **벤치마크(S&P500) 대비 알파:** {alpha:+.1f}%p ({cum_return:+.1f}% vs {sp_cum_r:+.1f}%)"

    report_text = f"""**{info_r.get('name', main_ticker)} ({main_ticker}) 투자 분석 리포트**
분석 기준일: {analysis_date} | 분석 기간: {period_label}

---

**📌 종합 판단: {overall}**
{overall_detail}

---

**📊 핵심 지표 요약**
- **현재가:** {price_str} (전일 대비 {daily_change:+.2f}%)
- **기간 누적 수익률:** {cum_return:+.1f}% (연환산 {ann_return:+.1f}%)
- **연환산 변동성:** {volatility:.1f}%
- **샤프 비율:** {sharpe:.2f} ({'우수' if sharpe >= 2 else '양호' if sharpe >= 1 else '검토 필요'})
- **최대 낙폭(MDD):** {mdd:.1f}%
{sp_line}

---

**🔍 주요 기술적 신호**
{chr(10).join(f"- [{p}] {t}: {s}" for _, p, t, s, _ in insights if p in ("High", "Medium"))}

---

**🎯 핵심 행동 제안**
{chr(10).join(f"- {a}" for _, p, _, _, a in insights if p == "High") or "- 현재 High 등급 신호 없음"}

---
*본 리포트는 Skills/insight.md 규칙 기반으로 자동 생성되었습니다. 투자 판단은 본인 책임입니다.*
"""
    st.markdown(report_text)

    # 리포트 다운로드
    st.download_button(
        label="📥 리포트 다운로드 (.txt)",
        data=report_text.replace("**", "").replace("---", "─" * 40),
        file_name=f"{main_ticker}_report_{pd.Timestamp.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )
