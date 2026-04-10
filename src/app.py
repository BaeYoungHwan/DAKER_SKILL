"""
금융 투자 대시보드 — Streamlit 메인 앱
Skills/analysis.md + Skills/visualization.md + Skills/insight.md 기준 준수
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import streamlit as st
import pandas as pd

WATCHLIST_PATH = Path(__file__).parent.parent / "watchlist.json"


def _load_watchlist() -> list[str]:
    try:
        if WATCHLIST_PATH.exists():
            return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_watchlist(tickers: list[str]) -> None:
    try:
        WATCHLIST_PATH.write_text(json.dumps(tickers, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

from data.fetcher import (
    fetch_price, fetch_info, fetch_multiple, get_close_prices,
    fetch_exchange_rate_series, search_ticker, VALID_PERIODS,
    fetch_market_overview, fetch_news, fetch_earnings, fetch_fear_greed,
    fetch_financials, fetch_dividends, classify_position,
)
try:
    from data.fetcher import fetch_next_earnings, fetch_institutional_holders, fetch_macro_data
    _HAS_EXTENDED_FETCHER = True
except Exception as _e:
    import streamlit as _st_err
    _st_err.error(f"Extended fetcher import error: {_e}")
    _HAS_EXTENDED_FETCHER = False
    def fetch_next_earnings(ticker: str) -> dict: return {}
    def fetch_institutional_holders(ticker: str) -> dict: return {}
    def fetch_macro_data(period: str = "1y") -> dict: return {}
from analysis.indicators import (
    calc_returns, calc_cumulative_return, calc_annualized_return,
    calc_moving_averages, calc_rsi, calc_bollinger_bands,
    calc_volatility, calc_sharpe_ratio, calc_max_drawdown,
    calc_drawdown_series, calc_correlation_matrix, get_rsi_signal,
    detect_golden_cross, calc_52week_range, calc_macd, calc_beta, calc_momentum,
    calc_stochastic, calc_rolling_sharpe, run_backtest,
)
from viz.charts import (
    candlestick_chart, line_chart_multi,
    portfolio_pie, correlation_heatmap, rsi_chart,
    rsi_gauge_chart, macd_chart, drawdown_chart, risk_return_scatter,
    stochastic_chart, earnings_chart, rolling_sharpe_chart, sector_heatmap,
    financials_chart, dividend_chart, backtest_chart, macro_chart,
)
from skills.parser import load_analysis_config, load_insight_rules

# Skills/analysis.md 에서 임계치 로드 — 파일 수정 시 앱 재시작으로 자동 반영
_ACFG = load_analysis_config()

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="금융 투자 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 커스텀 CSS (TradingView Dark 테마) ─────────────────────
# 색상·폰트·컴포넌트 스타일 규칙: Skills/visualization.md §6 테마 토큰 기준
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── CSS 변수 */
:root {
    --bg:          #131722;
    --card:        #1E222D;
    --sidebar:     #1C1F2D;
    --border:      #2A2E39;
    --input-bg:    #2A2E39;
    --text:        #D1D4DC;
    --text-sub:    #787B86;
    --text-bright: #FFFFFF;
    --accent:      #2962FF;
    --up:          #26A69A;
    --down:        #EF5350;
    --neutral:     #7B68EE;
}

/* ── 글로벌 */
.stApp {
    background-color: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
}
.stApp p, .stApp li, .stApp div { color: var(--text); }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--text-bright); font-family: 'Inter', sans-serif; }

/* ── 스크롤바 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-sub); }

/* ── 사이드바 */
section[data-testid="stSidebar"] > div:first-child {
    background-color: var(--sidebar);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span { color: var(--text) !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: var(--text-bright) !important; }

/* ── 메트릭 카드 */
[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.2rem !important;
    box-shadow: 0 4px 12px rgba(0,0,0,.3);
    transition: transform .2s, box-shadow .2s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,.5);
}
[data-testid="stMetricLabel"] { font-size: 11px !important; color: var(--text-sub) !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: .5px; }
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800 !important; color: var(--text-bright) !important; font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stMetricDelta"] svg { display: none; }

/* ── 탭 바 */
[data-testid="stTabBar"] {
    background: var(--card);
    border-radius: 10px;
    padding: 4px;
    border: 1px solid var(--border);
}
[data-testid="stTab"] { color: var(--text-sub) !important; font-weight: 600; }
[data-testid="stTab"][aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent); }

/* ── 대시보드 헤더 배너 */
.dash-header {
    background: var(--card);
    border-left: 4px solid var(--accent);
    border-radius: 0 14px 14px 0;
    padding: 20px 28px;
    color: var(--text-bright);
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0,0,0,.4);
    border-top: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
}
.dash-header-left h2 { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -.4px; color: var(--text-bright); }
.dash-header-left .dh-sub { margin: 5px 0 0; font-size: 13px; color: var(--text-sub); }
.dash-header-right { text-align: right; }
.dash-header-right .dh-price { font-size: 28px; font-weight: 900; font-family: 'JetBrains Mono', monospace; color: var(--text-bright); }
.dash-header-right .dh-chg-pos { color: var(--up); font-size: 15px; font-weight: 700; }
.dash-header-right .dh-chg-neg { color: var(--down); font-size: 15px; font-weight: 700; }
.live-dot {
    display: inline-block; width: 8px; height: 8px;
    background: var(--up); border-radius: 50%;
    margin-right: 6px; animation: blink 1.5s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.25} }

/* ── 시장 지수 스트립 */
.mkt-strip { display: flex; gap: 8px; margin-bottom: 18px; }
.mkt-card {
    flex: 1; background: var(--card); border-radius: 10px;
    padding: 12px 14px; border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(0,0,0,.2);
    text-align: center; position: relative; overflow: hidden;
    transition: transform .2s;
}
.mkt-card:hover { transform: translateY(-1px); }
.mkt-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px; background: var(--top-color, var(--border));
}
.mkt-card .mk-label { font-size: 10px; color: var(--text-sub); font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }
.mkt-card .mk-price { font-size: 15px; font-weight: 800; color: var(--text-bright); margin: 4px 0 3px; font-family: 'JetBrains Mono', monospace; }
.mkt-card .mk-chg-pos { font-size: 12px; color: var(--up); font-weight: 700; }
.mkt-card .mk-chg-neg { font-size: 12px; color: var(--down); font-weight: 700; }

/* ── 모멘텀 배지 */
.momentum-row { display: flex; gap: 8px; margin: 10px 0 16px; flex-wrap: wrap; }
.mbadge {
    padding: 5px 14px; border-radius: 6px;
    font-size: 13px; font-weight: 700;
    display: inline-flex; align-items: center; gap: 5px;
    font-family: 'JetBrains Mono', monospace;
}
.mbadge.pos { background: rgba(38,166,154,.15); color: var(--up); border: 1px solid rgba(38,166,154,.3); }
.mbadge.neg { background: rgba(239,83,80,.15); color: var(--down); border: 1px solid rgba(239,83,80,.3); }
.mbadge.neu { background: rgba(123,104,238,.15); color: var(--neutral); border: 1px solid rgba(123,104,238,.3); }

/* ── 52주 범위 바 */
.range-wrap {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px 20px; margin: 14px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,.2);
}
.range-title { font-size: 11px; color: var(--text-sub); font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 10px; }
.range-nums { display: flex; justify-content: space-between; margin-bottom: 8px; }
.range-low { font-size: 12px; color: var(--down); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.range-curr { font-size: 13px; font-weight: 800; color: var(--text-bright); font-family: 'JetBrains Mono', monospace; }
.range-high { font-size: 12px; color: var(--up); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.range-track {
    background: linear-gradient(90deg, var(--down) 0%, #FFA726 50%, var(--up) 100%);
    border-radius: 4px; height: 6px; position: relative; margin: 6px 0;
}
.range-dot {
    width: 14px; height: 14px; background: var(--accent);
    border: 2px solid var(--bg); border-radius: 50%;
    position: absolute; top: -4px; transform: translateX(-50%);
    box-shadow: 0 0 8px rgba(41,98,255,.6);
}

/* ── 포트폴리오 KPI 스트립 */
.port-kpi-strip { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 20px; }
.port-kpi-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,.3); text-align: center;
    transition: transform .2s;
}
.port-kpi-card:hover { transform: translateY(-2px); }
.pk-label { font-size: 10px; color: var(--text-sub); font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
.pk-value { font-size: 24px; font-weight: 900; font-family: 'JetBrains Mono', monospace; }
.pk-value.pos { color: var(--up); }
.pk-value.neg { color: var(--down); }
.pk-value.neu { color: var(--text-bright); }
.pk-sub { font-size: 11px; color: var(--text-sub); margin-top: 3px; }

/* ── 인사이트 카드 */
.ins-high {
    background: #2D1B1B; border: 1px solid rgba(239,83,80,.25);
    border-left: 4px solid var(--down); border-radius: 10px;
    padding: 16px 20px; margin-bottom: 12px;
}
.ins-medium {
    background: #2D2617; border: 1px solid rgba(255,167,38,.25);
    border-left: 4px solid #FFA726; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 12px;
}
.ins-info {
    background: #1A2635; border: 1px solid rgba(41,98,255,.25);
    border-left: 4px solid var(--accent); border-radius: 10px;
    padding: 16px 20px; margin-bottom: 12px;
}
.ins-title { font-size: 15px; font-weight: 800; color: var(--text-bright); margin-bottom: 12px; }
.ins-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.ins-box { background: rgba(255,255,255,.05); border-radius: 7px; padding: 10px 14px; border: 1px solid var(--border); }
.ins-box-label { font-size: 10px; color: var(--text-sub); font-weight: 700; text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }
.ins-box-val { font-size: 13px; color: var(--text); font-weight: 500; font-family: 'JetBrains Mono', monospace; }

/* ── 섹션 헤더 라인 */
.sec-header {
    display: flex; align-items: center; gap: 8px;
    margin: 20px 0 12px; padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
.sec-header span { font-size: 16px; font-weight: 800; color: var(--text-bright); }

/* ── 테이블 내 색상 */
.ret-pos { color: var(--up) !important; font-weight: 700; }
.ret-neg { color: var(--down) !important; font-weight: 700; }

/* ── Divider */
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<h2 style="color:#e6edf3;margin:0">📈 투자 대시보드</h2>', unsafe_allow_html=True)
    st.divider()

    st.subheader("종목 설정")

    # ── Session state 초기화 (watchlist 자동 불러오기)
    if "selected_tickers" not in st.session_state:
        saved = _load_watchlist()
        st.session_state.selected_tickers = saved if saved else ["AAPL", "MSFT", "GOOGL"]
    if "ticker_names" not in st.session_state:
        st.session_state.ticker_names = {}
    if "search_counter" not in st.session_state:
        st.session_state.search_counter = 0
    if "holdings" not in st.session_state:
        # {ticker: {"avg_cost": float, "quantity": float}} — 매입가/수량 (선택 입력)
        st.session_state.holdings = {}

    # ── URL 파라미터로 초기 종목 설정 (예: ?tickers=005930.KS,000660.KS)
    if "tickers" in st.query_params and not st.session_state.get("_params_loaded"):
        raw = st.query_params["tickers"]
        for t in [x.strip().upper() for x in raw.split(",") if x.strip()]:
            if t not in st.session_state.selected_tickers:
                st.session_state.selected_tickers.append(t)
        st.session_state["_params_loaded"] = True

    # ── 종목 검색 (카운터 키로 추가 후 입력창 자동 초기화)
    search_q = st.text_input(
        "🔍 종목 검색", placeholder="예: 삼성전자, TSLA, Apple",
        key=f"search_q_{st.session_state.search_counter}"
    )
    if search_q:
        results = search_ticker(search_q)
        if results:
            opts = {f"{r.get('shortname', r['symbol'])} [{r['symbol']}]": r for r in results}
            chosen_label = st.selectbox("검색 결과", list(opts.keys()), label_visibility="collapsed")
            if st.button("+ 추가", use_container_width=True):
                r = opts[chosen_label]
                t = r["symbol"]
                if t not in st.session_state.selected_tickers:
                    st.session_state.selected_tickers.append(t)
                    st.session_state.ticker_names[t] = r.get("shortname", t)
                    _save_watchlist(st.session_state.selected_tickers)
                st.session_state.search_counter += 1  # 키 변경으로 입력창 초기화
                st.rerun()
        else:
            st.caption("검색 결과 없음")

    # ── 직접 티커 입력
    with st.expander("직접 티커 입력"):
        manual = st.text_input("티커 (쉼표 구분)", placeholder="005930.KS, AAPL", key="manual_input")
        if st.button("추가", key="manual_add", use_container_width=True):
            added = False
            for t in [x.strip().upper() for x in manual.split(",") if x.strip()]:
                if t not in st.session_state.selected_tickers:
                    st.session_state.selected_tickers.append(t)
                    added = True
            if added:
                _save_watchlist(st.session_state.selected_tickers)
            st.rerun()

    # ── 선택된 종목 목록
    if st.session_state.selected_tickers:
        st.caption(f"종목 {len(st.session_state.selected_tickers)}개 선택됨")
        to_remove = []
        for t in list(st.session_state.selected_tickers):
            col1, col2 = st.columns([5, 1])
            label = st.session_state.ticker_names.get(t, "")
            col1.markdown(f"**{t}** <span style='color:#787B86;font-size:11px'>{label}</span>", unsafe_allow_html=True)
            if col2.button("×", key=f"rm_{t}", help=f"{t} 제거"):
                to_remove.append(t)
        for t in to_remove:
            st.session_state.selected_tickers.remove(t)
            st.session_state.ticker_names.pop(t, None)
        if to_remove:
            _save_watchlist(st.session_state.selected_tickers)
            st.rerun()

    tickers = st.session_state.selected_tickers

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
    show_macd = st.checkbox("MACD 차트", value=True)

    BENCHMARK_OPTIONS = {
        "S&P500": "^GSPC",
        "KOSPI": "^KS11",
        "NASDAQ": "^IXIC",
        "DOW JONES": "^DJI",
        "없음": None,
    }
    benchmark_name = st.selectbox("벤치마크 선택", options=list(BENCHMARK_OPTIONS.keys()), index=0)
    benchmark_ticker = BENCHMARK_OPTIONS[benchmark_name]
    show_benchmark = benchmark_ticker is not None

    st.divider()
    st.caption("데이터: Yahoo Finance (yfinance) — API Key 불필요")

# ── 메인 ────────────────────────────────────────────────────
if not tickers:
    st.warning("사이드바에서 종목을 입력해주세요.")
    st.stop()

with st.spinner("데이터 로딩 중..."):
    all_data = fetch_multiple(tickers, period)
    info_data = {t: fetch_info(t) for t in tickers}
    benchmark_data = fetch_price(benchmark_ticker, period) if show_benchmark else pd.DataFrame()
    market_overview = fetch_market_overview()

if not all_data:
    st.error("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")
    st.stop()

# ── 데이터 품질 검증 (analysis.md §4)
_data_warnings = []
_outlier_threshold = _ACFG["outlier_pct_threshold"]  # Skills/analysis.md §4 — 기본 15%
for _t, _df in all_data.items():
    # 최소 데이터 요건 (Skills/analysis.md §4 — min_data_days)
    if len(_df) < _ACFG["min_data_days"]:
        _data_warnings.append(f"⚠️ **{_t}**: 데이터 {len(_df)}일치 — 지표 계산에 최소 {_ACFG['min_data_days']}일 필요.")
    # 이상치 감지: 일별 수익률 ±outlier_pct_threshold% 초과 (Skills/analysis.md §4)
    _ret = _df["Close"].pct_change() * 100
    _outliers = _ret[_ret.abs() > _outlier_threshold].dropna()
    if not _outliers.empty:
        _shown = list(_outliers.items())[:3]  # 종목당 최대 3건만 표시
        for _date, _val in _shown:
            _data_warnings.append(f"🚨 **{_t}** 이상치 감지 — {_date.strftime('%Y-%m-%d')}: 일별 수익률 {_val:+.1f}% (±{_outlier_threshold:.0f}% 초과)")
        _remaining = len(_outliers) - len(_shown)
        if _remaining > 0:
            _data_warnings.append(f"ℹ️ **{_t}** 이상치 외 {_remaining}건 더 있음 (yfinance 데이터 자동 보정 적용 중)")

if _data_warnings:
    with st.expander(f"⚠️ 데이터 품질 알림 {len(_data_warnings)}건", expanded=False):
        for _w in _data_warnings:
            st.warning(_w)

if main_ticker not in all_data:
    main_ticker = next(iter(all_data))

main_df = all_data[main_ticker]
close = main_df["Close"]

# 한국 주식(.KS/.KQ)은 yfinance currency 반환이 불안정하므로 티커 접미사로 보완
def _detect_currency(ticker: str, info: dict) -> str:
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return "KRW"
    return info.get("currency", "USD")

currency = _detect_currency(main_ticker, info_data.get(main_ticker, {}))
currency_sym = "₩" if currency == "KRW" else ("¥" if currency == "JPY" else "$")

# ── KPI 계산 ─────────────────────────────────────────────────
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

# ── 시장 지수 스트립 (상단 전체) ──────────────────────────────
if market_overview:
    mkt_html = '<div class="mkt-strip">'
    for name, data in market_overview.items():
        chg = data["change"]
        top_color = "#26a69a" if chg >= 0 else "#ef5350"
        arrow = "▲" if chg >= 0 else "▼"
        chg_class = "mk-chg-pos" if chg >= 0 else "mk-chg-neg"
        price = data["price"]
        price_fmt = f"{price:,.2f}" if price < 10000 else f"{price:,.0f}"
        mkt_html += f"""
        <div class="mkt-card" style="--top-color:{top_color}">
            <div class="mk-label">{name}</div>
            <div class="mk-price">{price_fmt}</div>
            <div class="{chg_class}">{arrow} {abs(chg):.2f}%</div>
        </div>"""
    mkt_html += '</div>'
    st.markdown(mkt_html, unsafe_allow_html=True)

# ── 공포/탐욕 지수 카드 ───────────────────────────────────────
fg = fetch_fear_greed()
fg_score = fg["score"]
if fg_score >= 75:
    fg_color = "#26a69a"
    fg_bg = "rgba(38,166,154,0.1)"
elif fg_score >= 55:
    fg_color = "#80cbc4"
    fg_bg = "rgba(128,203,196,0.08)"
elif fg_score >= 45:
    fg_color = "#787B86"
    fg_bg = "rgba(120,123,134,0.08)"
elif fg_score >= 25:
    fg_color = "#ef9a9a"
    fg_bg = "rgba(239,154,154,0.1)"
else:
    fg_color = "#ef5350"
    fg_bg = "rgba(239,83,80,0.12)"

st.markdown(f"""
<div style="display:flex; align-items:center; gap:16px; padding:10px 16px; margin-bottom:8px;
            background:{fg_bg}; border-radius:8px; border:1px solid {fg_color}33;">
    <div style="font-size:13px; color:#787B86; white-space:nowrap;">공포/탐욕 지수</div>
    <div style="flex:1; height:8px; background:#2A2E39; border-radius:4px; overflow:hidden;">
        <div style="height:100%; width:{fg_score}%; background:linear-gradient(90deg,#ef5350,#787B86,#26a69a); border-radius:4px;"></div>
    </div>
    <div style="font-size:20px; font-weight:700; color:{fg_color}; font-family:'JetBrains Mono',monospace; white-space:nowrap;">
        {fg_score:.0f} <span style="font-size:13px; font-weight:400;">{fg["label"]}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 탭 구조 ──────────────────────────────────────────────────
tab_main, tab_portfolio, tab_compare, tab_insight = st.tabs([
    "📊 종목 분석", "💼 포트폴리오", "📈 비교 분석", "💡 투자 인사이트"
])

# ══════════════════════════════════════════════════════════════
# 탭 1: 종목 분석
# ══════════════════════════════════════════════════════════════
with tab_main:
    info = info_data.get(main_ticker, {})
    name = info.get("name", main_ticker)
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")

    # ── 대시보드 헤더 배너
    chg_class = "dh-chg-pos" if daily_change >= 0 else "dh-chg-neg"
    chg_arrow = "▲" if daily_change >= 0 else "▼"
    analysis_date = pd.Timestamp.now().strftime("%Y.%m.%d %H:%M")
    st.markdown(f"""
    <div class="dash-header">
        <div class="dash-header-left">
            <h2><span class="live-dot"></span>{name} <span style="opacity:.6;font-size:18px">({main_ticker})</span></h2>
            <div class="dh-sub">{sector} · {industry} · 분석 기준: {analysis_date}</div>
        </div>
        <div class="dash-header-right">
            <div class="dh-price">{price_str}</div>
            <div class="{chg_class}">{chg_arrow} {abs(daily_change):.2f}% 전일 대비</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI 카드 행
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("현재가", price_str, f"{daily_change:+.2f}%")
    col2.metric("누적 수익률", f"{cum_return:+.1f}%", help=f"연환산: {ann_return:+.1f}%")
    col3.metric("연환산 변동성", f"{volatility:.1f}%")
    col4.metric("샤프 비율", f"{sharpe:.2f}", help=f"≥{_ACFG['sharpe_excellent']}: 우수 / ≥{_ACFG['sharpe_good']}: 양호 / <{_ACFG['sharpe_good']}: 검토")
    col5.metric("최대 낙폭(MDD)", f"{mdd:.1f}%")

    # ── 재무 지표 보조 행
    fin_cols = st.columns(4)
    if info.get("pe_ratio"):
        fin_cols[0].metric("PER", f"{info['pe_ratio']:.1f}x")
    if info.get("pb_ratio"):
        fin_cols[1].metric("PBR", f"{info['pb_ratio']:.2f}x")
    if info.get("eps"):
        fin_cols[2].metric("EPS", f"{info['eps']:.2f}")
    if info.get("dividend_yield"):
        fin_cols[3].metric("배당수익률", f"{info['dividend_yield']:.2f}%")

    # ── 실적 히스토리 차트
    earnings_df = fetch_earnings(main_ticker)
    if not earnings_df.empty:
        st.markdown('<div class="sec-header"><span>📊 분기별 실적 (EPS)</span></div>', unsafe_allow_html=True)
        st.plotly_chart(earnings_chart(earnings_df, main_ticker), use_container_width=True)

    # ── 모멘텀 배지
    momentum = calc_momentum(close)
    mom_html = '<div class="momentum-row">'
    mom_labels = {"1W": "1주", "1M": "1개월", "3M": "3개월"}
    for key, label in mom_labels.items():
        val = momentum.get(key)
        if val is not None:
            css = "pos" if val >= 0 else "neg"
            arrow = "▲" if val >= 0 else "▼"
            mom_html += f'<span class="mbadge {css}">{arrow} {label} {val:+.2f}%</span>'
    mom_html += '</div>'
    st.markdown(mom_html, unsafe_allow_html=True)

    # ── 52주 고가/저가 범위 바
    range_data = calc_52week_range(close)
    pct = range_data["position_pct"]
    low_52 = range_data["low_52"]
    high_52 = range_data["high_52"]
    fmt_price = (lambda v: f"{currency_sym}{v:,.0f}") if (currency == "KRW" or current_price >= 1000) else (lambda v: f"{currency_sym}{v:.2f}")
    st.markdown(f"""
    <div class="range-wrap">
        <div class="range-title">📏 52주 고가/저가 범위</div>
        <div class="range-nums">
            <span class="range-low">저가 {fmt_price(low_52)}</span>
            <span class="range-curr">현재 {fmt_price(range_data['current'])} · {pct:.0f}% 위치</span>
            <span class="range-high">고가 {fmt_price(high_52)}</span>
        </div>
        <div class="range-track">
            <div class="range-dot" style="left:{pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── 기간 선택 버튼 (Skills/visualization.md §4 — 1M/3M/6M/1Y/2Y/5Y 버튼)
    CHART_PERIOD_LABELS = {"1mo": "1M", "3mo": "3M", "6mo": "6M", "1y": "1Y", "2y": "2Y", "5y": "5Y"}
    _default_idx = list(CHART_PERIOD_LABELS.keys()).index(period) if period in CHART_PERIOD_LABELS else 3
    chart_period = st.radio(
        "차트 기간",
        options=list(CHART_PERIOD_LABELS.keys()),
        format_func=lambda x: CHART_PERIOD_LABELS[x],
        index=_default_idx,
        horizontal=True,
        key="chart_period_btn",
        label_visibility="collapsed",
    )
    _chart_days_map = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260}
    _n_days = _chart_days_map.get(chart_period, 252)
    chart_df = main_df.iloc[-_n_days:] if len(main_df) >= _n_days else main_df

    # ── 2/3:1/3 그리드 레이아웃 (Skills/visualization.md §3.1)
    col_chart, col_port = st.columns([2, 1])
    with col_chart:
        st.markdown('<div class="sec-header"><span>📊 주가 차트</span></div>', unsafe_allow_html=True)
        mas = calc_moving_averages(close)
        # chart_df 범위로 MA/BB 슬라이싱 → x축 확장 방지 (G2 버그 수정)
        _chart_idx = chart_df.index
        selected_mas = {k: v.reindex(_chart_idx) for k, v in mas.items() if k in show_ma}
        bb = calc_bollinger_bands(close) if show_bb else None
        if bb is not None:
            bb = {k: v.reindex(_chart_idx) for k, v in bb.items()}
        st.plotly_chart(
            candlestick_chart(chart_df, main_ticker, selected_mas, bb),
            use_container_width=True,
        )
    with col_port:
        st.markdown('<div class="sec-header"><span>💼 포트폴리오 비중</span></div>', unsafe_allow_html=True)
        _port_weights_main = {t: 100 / len(all_data) for t in all_data}
        st.plotly_chart(portfolio_pie(_port_weights_main), use_container_width=True, key="pie_main")
        st.caption("균등 비중 기준 · 포트폴리오 탭에서 조정 가능")

    # ── MACD 차트
    if show_macd:
        st.markdown('<div class="sec-header"><span>📉 MACD</span></div>', unsafe_allow_html=True)
        macd_data = calc_macd(close)
        st.plotly_chart(macd_chart(macd_data, main_ticker), use_container_width=True)

    # ── RSI (게이지 + 라인 차트 2열)
    st.markdown('<div class="sec-header"><span>⚡ RSI (상대강도지수)</span></div>', unsafe_allow_html=True)
    rsi_values = calc_rsi(close)
    latest_rsi = float(rsi_values.dropna().iloc[-1])
    col_gauge, col_rsi = st.columns([1, 2])
    with col_gauge:
        st.plotly_chart(rsi_gauge_chart(latest_rsi, main_ticker), use_container_width=True)
    with col_rsi:
        st.plotly_chart(rsi_chart(rsi_values, main_ticker), use_container_width=True)

    # ── 스토캐스틱
    st.markdown('<div class="sec-header"><span>🎯 스토캐스틱 (Stochastic)</span></div>', unsafe_allow_html=True)
    stoch = calc_stochastic(main_df)
    st.plotly_chart(stochastic_chart(stoch, main_ticker), use_container_width=True)

    # ── 드로다운 차트
    st.markdown('<div class="sec-header"><span>📉 드로다운 (Drawdown)</span></div>', unsafe_allow_html=True)
    drawdown = calc_drawdown_series(close)
    st.plotly_chart(drawdown_chart(drawdown, main_ticker), use_container_width=True)

    # ── 재무제표 트렌드
    fin_df = fetch_financials(main_ticker)
    if not fin_df.empty:
        st.markdown('<div class="sec-header"><span>📊 분기별 재무 현황</span></div>', unsafe_allow_html=True)
        st.plotly_chart(financials_chart(fin_df, main_ticker), use_container_width=True)

    # ── 배당 달력
    div_series = fetch_dividends(main_ticker)
    if not div_series.empty:
        st.markdown('<div class="sec-header"><span>💰 배당금 히스토리</span></div>', unsafe_allow_html=True)
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.plotly_chart(dividend_chart(div_series, main_ticker), use_container_width=True)
        with col_d2:
            annual_div = div_series.resample("YE").sum()
            # 현재 연도(부분 기간) 제외한 완전한 연도만 사용
            _cur_year = pd.Timestamp.now().year
            _annual_complete = annual_div[annual_div.index.year < _cur_year]
            # 최근 연간 배당금: 마지막 완전 연도 기준
            _last_full_annual = float(_annual_complete.iloc[-1]) if not _annual_complete.empty else None
            st.metric("최근 연간 배당금", f"${_last_full_annual:.2f}" if _last_full_annual is not None else "N/A")
            # 배당 횟수: 오늘 기준 최근 12개월 배당 건수
            _today = pd.Timestamp.now().normalize()
            _last_12m = div_series[div_series.index >= (_today - pd.DateOffset(years=1))]
            st.metric("배당 횟수", f"{len(_last_12m)}회/년")
            # 배당 성장률: 완전한 연도끼리만 비교 (±50% 초과는 데이터 오류로 간주)
            if len(_annual_complete) >= 2:
                _prev_y = float(_annual_complete.iloc[-2])
                _curr_y = float(_annual_complete.iloc[-1])
                if _prev_y > 0:
                    div_growth = (_curr_y / _prev_y - 1) * 100
                    if abs(div_growth) <= 50:
                        st.metric("배당 성장률", f"{div_growth:+.1f}%")

    # ── 실적 캘린더
    st.markdown('<div class="sec-header"><span>📅 실적 캘린더</span></div>', unsafe_allow_html=True)
    next_earn = fetch_next_earnings(main_ticker)
    if next_earn:
        ec1, ec2, ec3 = st.columns(3)
        if "next_date" in next_earn:
            days_u = next_earn["days_until"]
            with ec1:
                delta_str = f"{days_u}일 후" if days_u >= 0 else f"{-days_u}일 전"
                st.metric("다음 실적 발표일", next_earn["next_date"], delta_str)
            if days_u <= 14:
                st.warning(f"⚠️ {days_u}일 후 실적 발표 예정 — 발표 전 변동성 확대 가능성")
        if "last_date" in next_earn:
            with ec2:
                st.metric("직전 실적 발표일", next_earn["last_date"])
        if next_earn.get("last_eps_estimate") and next_earn.get("last_eps_actual"):
            surprise_pct = (next_earn["last_eps_actual"] - next_earn["last_eps_estimate"]) / abs(next_earn["last_eps_estimate"]) * 100
            surprise_color = "normal" if surprise_pct >= 0 else "inverse"
            with ec3:
                st.metric("EPS 서프라이즈", f"{surprise_pct:+.1f}%",
                          f"예상 {next_earn['last_eps_estimate']:.2f} → 실제 {next_earn['last_eps_actual']:.2f}",
                          delta_color=surprise_color)
    else:
        st.caption("실적 일정을 불러올 수 없습니다.")

    # ── 수급 데이터
    st.markdown('<div class="sec-header"><span>🏦 기관 수급 현황</span></div>', unsafe_allow_html=True)
    holders_data = fetch_institutional_holders(main_ticker)
    if holders_data:
        hc1, hc2 = st.columns([1, 2])
        with hc1:
            if "major" in holders_data:
                st.caption("**주요 보유 비중**")
                for label, val in holders_data["major"].items():
                    if val is not None and label:
                        try:
                            v = float(str(val).replace("%", ""))
                            st.markdown(f"<span style='color:#787B86;font-size:12px'>{label}</span> "
                                        f"<span style='font-weight:700;color:#D1D4DC'>{v:.1f}%</span>",
                                        unsafe_allow_html=True)
                        except Exception:
                            pass
        with hc2:
            if "institutional" in holders_data and holders_data["institutional"]:
                inst_df = pd.DataFrame(holders_data["institutional"])
                if "Holder" in inst_df.columns and "% Out" in inst_df.columns:
                    inst_df = inst_df[["Holder", "% Out", "Shares"]].head(8)
                    inst_df.columns = ["기관명", "보유비중(%)", "보유주식수"]
                    st.caption("**상위 기관 보유 현황**")
                    st.dataframe(inst_df, use_container_width=True, hide_index=True)
    else:
        st.caption("수급 데이터를 불러올 수 없습니다.")

    # ── 뉴스 피드
    st.markdown('<div class="sec-header"><span>📰 최신 뉴스</span></div>', unsafe_allow_html=True)
    news_items = fetch_news(main_ticker)
    if news_items:
        for item in news_items:
            pub = f" · {item['publisher']}" if item['publisher'] else ""
            date = f" · {item['pub_time']}" if item['pub_time'] else ""
            st.markdown(
                f"• [{item['title']}]({item['url']})"
                f"<span style='font-size:11px;color:#787B86'>{pub}{date}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("뉴스를 불러올 수 없습니다.")

    # ── 원시 데이터
    with st.expander("📋 최근 30일 데이터"):
        _recent = main_df.tail(30).sort_index(ascending=False).copy()
        _recent.index = _recent.index.strftime("%Y-%m-%d")
        st.dataframe(_recent.style.format("{:.2f}"), use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 탭 2: 포트폴리오
# ══════════════════════════════════════════════════════════════
with tab_portfolio:
    st.subheader("포트폴리오 분석")

    # ── 레버리지·인버스 ETF 경고 (종목 추가 시 자동 감지)
    _lev_warnings = []
    for _t in tickers:
        if _t not in all_data:
            continue
        _info_name = st.session_state.ticker_names.get(_t, "")
        _cls = classify_position(_t, _info_name)
        if _cls["warning"]:
            _lev_warnings.append(_cls["warning"])
    if _lev_warnings:
        with st.expander("⚠️ 특수 포지션 유의 사항", expanded=True):
            for _w in _lev_warnings:
                st.warning(_w)

    # ── 비중 설정 (인라인)
    with st.expander("⚖️ 포트폴리오 비중 설정", expanded=False):
        weights_input = {}
        equal_w = round(100 / len(tickers), 1)
        cols = st.columns(min(len(tickers), 4))
        for i, t in enumerate(tickers):
            with cols[i % len(cols)]:
                weights_input[t] = st.number_input(
                    t, min_value=0.0, max_value=100.0, value=equal_w, step=0.5, key=f"w_{t}"
                )
        total_w = sum(weights_input.values())
        if abs(total_w - 100) > 1.0:
            st.warning(f"비중 합계: {total_w:.1f}% (100%로 맞춰주세요)")
        else:
            st.caption(f"✅ 합계: {total_w:.1f}%")

    # C3: expander 외부에도 비중 합계 경고 표시
    if abs(total_w - 100) > 1.0:
        st.warning(f"⚖️ 비중 합계 **{total_w:.1f}%** — 위 '비중 설정'에서 100%로 맞춰주세요.")

    valid_weights = {t: w for t, w in weights_input.items() if t in all_data and w > 0}
    if not valid_weights:
        valid_weights = {t: 100 / len(all_data) for t in all_data}
    total_w_sum = sum(valid_weights.values())

    # ── 매입가/수량 입력 (선택사항 — 평가손익 계산용)
    with st.expander("💰 매입가/수량 입력 (평가손익 계산)", expanded=False):
        st.caption(
            "입력하지 않으면 수익률 기반 분석만 표시됩니다. "
            "**공매도(숏)**는 수량을 음수로 입력하세요 (예: -100)."
        )
        _h_cols = st.columns(min(len(tickers), 3))
        for _i, _t in enumerate(tickers):
            if _t not in all_data:
                continue
            with _h_cols[_i % len(_h_cols)]:
                _cls_pos = classify_position(_t, st.session_state.ticker_names.get(_t, ""))
                _label = f"**{_t}**"
                if _cls_pos["inverse"]:
                    _label += " ↓ 인버스"
                elif _cls_pos["leveraged"]:
                    _label += " ⚡ 레버리지"
                st.markdown(_label)
                _prev_h = st.session_state.holdings.get(_t, {})
                _avg = st.number_input(
                    "평균 매입가", min_value=0.0, value=float(_prev_h.get("avg_cost", 0.0)),
                    step=0.01, key=f"cost_{_t}", format="%.2f"
                )
                # 공매도 지원: min_value 제거 → 음수 수량 허용
                _qty = st.number_input(
                    "보유 수량 (음수=공매도)", value=float(_prev_h.get("quantity", 0.0)),
                    step=1.0, key=f"qty_{_t}", format="%.4f"
                )
                if _qty != 0:
                    st.session_state.holdings[_t] = {"avg_cost": _avg, "quantity": _qty}
                elif _t in st.session_state.holdings:
                    del st.session_state.holdings[_t]

    # 매입가/수량 기반 손익 계산 (공매도 포함)
    holdings_pnl: dict[str, dict] = {}
    for _t, _h in st.session_state.holdings.items():
        if _t not in all_data or _h.get("avg_cost", 0) <= 0 or _h.get("quantity", 0) == 0:
            continue
        _curr = float(all_data[_t]["Close"].iloc[-1])
        _cost = float(_h["avg_cost"])
        _qty = float(_h["quantity"])
        _is_short = _qty < 0  # 공매도 포지션
        # 공매도 P&L: 매입가에서 현재가로 하락할수록 이익
        # pnl = (매입가 - 현재가) × |수량| (숏) or (현재가 - 매입가) × 수량 (롱)
        _pnl = (_cost - _curr) * abs(_qty) if _is_short else (_curr - _cost) * _qty
        _pnl_pct = (_cost / _curr - 1) * 100 if _is_short else (_curr / _cost - 1) * 100
        holdings_pnl[_t] = {
            "current_price": _curr,
            "avg_cost": _cost,
            "quantity": _qty,
            "is_short": _is_short,
            "eval_amount": _curr * abs(_qty),
            "cost_amount": _cost * abs(_qty),
            "pnl": _pnl,
            "pnl_pct": _pnl_pct,
        }
    total_pnl = sum(v["pnl"] for v in holdings_pnl.values()) if holdings_pnl else None
    total_eval = sum(v["eval_amount"] for v in holdings_pnl.values()) if holdings_pnl else None
    total_cost = sum(v["cost_amount"] for v in holdings_pnl.values()) if holdings_pnl else None

    # ── 포트폴리오 KPI 요약 스트립
    port_returns = {}
    for t in all_data:
        c = all_data[t]["Close"]
        port_returns[t] = float(calc_cumulative_return(c).iloc[-1])

    if total_w_sum > 0:
        weighted_total = sum(port_returns[t] * (valid_weights.get(t, 0) / total_w_sum)
                             for t in all_data if t in valid_weights)
    else:
        weighted_total = 0.0

    best_ticker = max(port_returns, key=port_returns.get)
    worst_ticker = min(port_returns, key=port_returns.get)
    best_val = port_returns[best_ticker]
    worst_val = port_returns[worst_ticker]

    # 포트폴리오 샤프 비율 (단순 평균)
    port_sharpes = [calc_sharpe_ratio(all_data[t]["Close"]) for t in all_data]
    avg_sharpe = sum(port_sharpes) / len(port_sharpes) if port_sharpes else 0.0

    wt_cls = "pos" if weighted_total >= 0 else "neg"
    bs_cls = "pos" if best_val >= 0 else "neg"
    ws_cls = "pos" if worst_val >= 0 else "neg"
    sp_cls = "pos" if avg_sharpe >= _ACFG["sharpe_good"] else ("neg" if avg_sharpe < 0 else "neu")

    st.markdown(f"""
    <div class="port-kpi-strip">
        <div class="port-kpi-card">
            <div class="pk-label">포트폴리오 수익률</div>
            <div class="pk-value {wt_cls}">{weighted_total:+.1f}%</div>
            <div class="pk-sub">가중 누적 수익률</div>
        </div>
        <div class="port-kpi-card">
            <div class="pk-label">최고 수익 종목</div>
            <div class="pk-value {bs_cls}">{best_val:+.1f}%</div>
            <div class="pk-sub">{best_ticker}</div>
        </div>
        <div class="port-kpi-card">
            <div class="pk-label">최저 수익 종목</div>
            <div class="pk-value {ws_cls}">{worst_val:+.1f}%</div>
            <div class="pk-sub">{worst_ticker}</div>
        </div>
        <div class="port-kpi-card">
            <div class="pk-label">평균 샤프 비율</div>
            <div class="pk-value {sp_cls}">{avg_sharpe:.2f}</div>
            <div class="pk-sub">{'우수' if avg_sharpe >= _ACFG["sharpe_excellent"] else '양호' if avg_sharpe >= _ACFG["sharpe_good"] else '검토 필요'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 총 평가손익 카드 (매입가/수량 입력 시 표시)
    if total_pnl is not None:
        _pnl_color = "var(--up)" if total_pnl >= 0 else "var(--down)"
        _pnl_bg = "rgba(38,166,154,0.07)" if total_pnl >= 0 else "rgba(239,83,80,0.07)"
        _total_pnl_pct = (total_eval / total_cost - 1) * 100 if total_cost and total_cost > 0 else 0
        _arrow = "▲" if total_pnl >= 0 else "▼"
        st.markdown(f"""
        <div style="background:{_pnl_bg}; border:1px solid {_pnl_color}44; border-left:4px solid {_pnl_color};
                    border-radius:12px; padding:16px 20px; margin-bottom:16px; display:flex; gap:24px; align-items:center;">
            <div>
                <div style="font-size:10px;color:var(--text-sub);font-weight:700;text-transform:uppercase;letter-spacing:.5px;">총 평가손익</div>
                <div style="font-size:26px;font-weight:900;color:{_pnl_color};font-family:'JetBrains Mono',monospace;">
                    {_arrow} {abs(total_pnl):,.0f}
                    <span style="font-size:14px;font-weight:500;">({_total_pnl_pct:+.2f}%)</span>
                </div>
            </div>
            <div style="border-left:1px solid var(--border);padding-left:24px;">
                <div style="font-size:10px;color:var(--text-sub);font-weight:700;text-transform:uppercase;letter-spacing:.5px;">평가금액</div>
                <div style="font-size:18px;font-weight:700;color:var(--text-bright);font-family:'JetBrains Mono',monospace;">{total_eval:,.0f}</div>
            </div>
            <div style="border-left:1px solid var(--border);padding-left:24px;">
                <div style="font-size:10px;color:var(--text-sub);font-weight:700;text-transform:uppercase;letter-spacing:.5px;">매입금액</div>
                <div style="font-size:18px;font-weight:700;color:var(--text-bright);font-family:'JetBrains Mono',monospace;">{total_cost:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── 포트폴리오 리스크 경고 (analysis.md §3.2, §3.3)
    port_warnings = []

    # 자산 집중도 경고 (Skills/analysis.md §3.3 — asset_concentration_threshold)
    _asset_thr = _ACFG["asset_concentration_threshold"]
    for t, w in valid_weights.items():
        w_pct = w / total_w_sum * 100
        if w_pct > _asset_thr:
            port_warnings.append(("down", f"⚠️ 자산 집중 위험 — **{t}** 비중 {w_pct:.1f}% (기준: >{_asset_thr:.0f}%). 분산 투자를 권장합니다."))

    # 섹터 집중도 경고 (Skills/analysis.md §3.3 — sector_concentration_threshold)
    # N/A·미분류 섹터는 집중도 계산에서 제외 (한국 주식은 yfinance 섹터 미지원)
    _sector_thr = _ACFG["sector_concentration_threshold"]
    sector_weights: dict[str, float] = {}
    _invalid_sectors = {"N/A", "n/a", "", None, "기타"}
    for t, w in valid_weights.items():
        sector = info_data.get(t, {}).get("sector", None)
        if not sector or sector in _invalid_sectors:
            continue
        sector_weights[sector] = sector_weights.get(sector, 0) + w
    if sector_weights:
        _known_w_sum = sum(sector_weights.values())
        for sector, sw in sector_weights.items():
            sw_pct = sw / _known_w_sum * 100
            if sw_pct > _sector_thr:
                port_warnings.append(("down", f"⚠️ 섹터 집중 위험 — **{sector}** 섹터 비중 {sw_pct:.1f}% (기준: >{_sector_thr:.0f}%)."))

    # 고상관 자산 경고 (Skills/analysis.md §3.2 — correlation_threshold)
    _corr_thr = _ACFG["correlation_threshold"]
    if len(all_data) >= 2:
        close_prices = get_close_prices(all_data)
        corr_matrix = calc_correlation_matrix(close_prices)
        tickers_list = list(all_data.keys())
        for i in range(len(tickers_list)):
            for j in range(i + 1, len(tickers_list)):
                t1, t2 = tickers_list[i], tickers_list[j]
                if t1 in corr_matrix.index and t2 in corr_matrix.columns:
                    corr_val = corr_matrix.loc[t1, t2]
                    if corr_val > _corr_thr:
                        port_warnings.append(("warn", f"🔗 고상관 자산 쌍 — **{t1} & {t2}** 상관계수 {corr_val:.2f} (기준: >{_corr_thr}). 실질 분산 효과 낮음."))

    # 리밸런싱 신호: 균등 비중 대비 현재 설정 비중 ±5% 초과
    n = len(valid_weights)
    if n > 0:
        equal_target = 100 / n
        for t, w in valid_weights.items():
            w_pct = w / total_w_sum * 100
            deviation = abs(w_pct - equal_target)
            if deviation > 5:
                direction = "초과" if w_pct > equal_target else "부족"
                port_warnings.append(("info", f"⚖️ 리밸런싱 검토 — **{t}** 균등 비중 대비 {deviation:.1f}%p {direction} ({w_pct:.1f}% vs 균등 {equal_target:.1f}%)."))

    if port_warnings:
        st.markdown('<div class="sec-header"><span>⚠️ 포트폴리오 리스크 진단</span></div>', unsafe_allow_html=True)
        for warn_type, msg in port_warnings:
            if warn_type == "down":
                st.error(msg)
            elif warn_type == "warn":
                st.warning(msg)
            else:
                st.info(msg)
    else:
        st.success("✅ 자산 집중도 및 분산도 양호 — 특이 리스크 신호 없음.")

    # 혼합 통화 감지 (한국 주식 티커 접미사로 보완)
    currencies = {t: _detect_currency(t, info_data.get(t, {})) for t in all_data}
    has_krw = any(c == "KRW" for c in currencies.values())
    has_usd = any(c == "USD" for c in currencies.values())
    is_mixed = has_krw and has_usd

    use_fx = False
    fx_series = pd.Series(dtype=float)
    if is_mixed:
        st.info("🌐 **혼합 통화 포트폴리오** 감지 (KRW + USD). 원화 환산 시 USDKRW 환율을 자동 적용합니다.")
        use_fx = st.checkbox("원화 환산 통합 보기 (USDKRW 환율 적용)", value=False)
        if use_fx:
            with st.spinner("환율 데이터 로딩 중..."):
                fx_series = fetch_exchange_rate_series("USD", "KRW", period)
            if not fx_series.empty:
                current_rate = float(fx_series.iloc[-1])
                st.caption(f"현재 환율: 1 USD = ₩{current_rate:,.0f} (출처: Yahoo Finance USDKRW=X)")
            else:
                st.warning("환율 데이터를 불러오지 못했습니다.")
                use_fx = False

    col_pie, col_stats = st.columns([1, 1])

    with col_pie:
        st.plotly_chart(portfolio_pie(valid_weights), use_container_width=True)

    with col_stats:
        st.subheader("종목별 성과")
        rows = []
        for t in all_data:
            c = all_data[t]["Close"]
            beta_val = calc_beta(c, benchmark_data["Close"]) if show_benchmark and not benchmark_data.empty else None
            _t_currency = _detect_currency(t, info_data.get(t, {}))
            _price_val = float(c.iloc[-1])
            _price_fmt = f"₩{_price_val:,.0f}" if _t_currency == "KRW" else (f"${_price_val:,.0f}" if _price_val >= 1000 else f"${_price_val:.2f}")
            row = {
                "종목": t,
                "현재가": _price_fmt,
                "누적수익률(%)": f"{float(calc_cumulative_return(c).iloc[-1]):+.1f}",
                "변동성(%)": f"{calc_volatility(c)['annual_volatility']:.1f}",
                "샤프": f"{calc_sharpe_ratio(c):.2f}",
                "MDD(%)": f"{calc_max_drawdown(c):.1f}",
                "비중(%)": f"{valid_weights.get(t, 0):.1f}",
            }
            if beta_val is not None:
                row["베타"] = f"{beta_val:.2f}"
            # 매입가/수량 기반 손익 컬럼 추가
            if t in holdings_pnl:
                _h = holdings_pnl[t]
                row["포지션"] = "숏(공매도)" if _h.get("is_short") else "롱"
                row["매입가"] = f"{_h['avg_cost']:.2f}"
                row["수량"] = f"{_h['quantity']:.4f}"
                row["평가손익"] = f"{_h['pnl']:+,.0f}"
                row["손익률(%)"] = f"{_h['pnl_pct']:+.2f}%"
            rows.append(row)
        st.dataframe(pd.DataFrame(rows).set_index("종목"), use_container_width=True)

    # 포트폴리오 가중 수익률
    if len(all_data) >= 2:
        st.divider()
        close_prices = get_close_prices(all_data)
        if total_w_sum > 0:
            # C9: KR/US 혼합 시 거래일 불일치로 NaN 전파 방지 — ffill 적용
            close_prices_filled = close_prices.ffill()
            if use_fx and not fx_series.empty:
                close_for_port = close_prices_filled.copy()
                for t in close_for_port.columns:
                    if currencies.get(t, "USD") == "USD":
                        fx_aligned = fx_series.reindex(close_for_port.index, method="ffill")
                        close_for_port[t] = close_for_port[t] * fx_aligned
                chart_suffix = " (원화 환산)"
            else:
                close_for_port = close_prices_filled
                chart_suffix = ""

            port_return = sum(
                calc_cumulative_return(close_for_port[t]) * (valid_weights.get(t, 0) / total_w_sum)
                for t in close_for_port.columns if t in valid_weights
            )
            st.subheader(f"포트폴리오 가중 누적 수익률{chart_suffix}")
            port_df = pd.DataFrame({"포트폴리오": port_return})
            if not benchmark_data.empty:
                port_df[benchmark_name] = calc_cumulative_return(benchmark_data["Close"])
            st.plotly_chart(
                line_chart_multi(port_df, f"포트폴리오 vs {benchmark_name}{chart_suffix}", normalize=False),
                use_container_width=True,
            )

        # ── 롤링 샤프 비율 차트
        st.markdown('<div class="sec-header"><span>📐 롤링 샤프 비율 (60일)</span></div>', unsafe_allow_html=True)
        st.plotly_chart(rolling_sharpe_chart(close_prices), use_container_width=True)

        if len(all_data) >= 2:
            corr = calc_correlation_matrix(close_prices)
            st.plotly_chart(correlation_heatmap(corr), use_container_width=True, key="corr_portfolio")

# ══════════════════════════════════════════════════════════════
# 탭 3: 비교 분석
# ══════════════════════════════════════════════════════════════
with tab_compare:
    st.subheader("종목 수익률 비교")

    close_prices = get_close_prices(all_data)
    compare_df = close_prices.copy()
    if show_benchmark and not benchmark_data.empty:
        compare_df[benchmark_name] = benchmark_data["Close"]

    st.plotly_chart(
        line_chart_multi(compare_df, "누적 수익률 비교 (기간 시작점 = 0%)"),
        use_container_width=True,
    )

    # ── 색상 코딩 기간별 수익률 테이블
    st.subheader("기간별 수익률 (%)")
    period_returns = []
    compare_tickers = list(all_data.keys())
    if show_benchmark and not benchmark_data.empty:
        compare_tickers.append(benchmark_name)

    for t in compare_tickers:
        if t == benchmark_name and t not in all_data:
            c = benchmark_data["Close"] if not benchmark_data.empty else None
        else:
            c = all_data[t]["Close"] if t in all_data else None
        if c is None or c.empty:
            continue
        row = {"종목": t}
        for label, days in [("1개월", 21), ("3개월", 63), ("6개월", 126), ("1년", 252)]:
            if len(c) >= days:
                ret = (float(c.iloc[-1]) / float(c.iloc[-days]) - 1) * 100
                row[label] = round(ret, 2)
            else:
                row[label] = None
        row["기간 전체"] = round(float(calc_cumulative_return(c).iloc[-1]), 2)
        period_returns.append(row)

    if period_returns:
        ret_df = pd.DataFrame(period_returns).set_index("종목")
        ret_cols = [c for c in ret_df.columns]

        def _color_ret(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ""
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color: #26a69a; font-weight: bold"
                elif val < 0:
                    return "color: #ef5350; font-weight: bold"
            return ""

        def _fmt_ret(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return "N/A"
            return f"{val:+.1f}%"

        styled = (
            ret_df.style
            .map(_color_ret, subset=ret_cols)
            .format(_fmt_ret, subset=ret_cols)
        )
        st.dataframe(styled, use_container_width=True)

    st.divider()

    # ── 상관관계 히트맵
    st.markdown('<div class="sec-header"><span>🔗 자산 간 상관관계</span></div>', unsafe_allow_html=True)
    if len(all_data) >= 2:
        corr = calc_correlation_matrix(close_prices)
        st.plotly_chart(correlation_heatmap(corr), use_container_width=True, key="corr_compare")
    else:
        st.info("상관관계 분석은 종목 2개 이상 필요합니다.")

    st.divider()

    # ── 리스크-수익률 산점도
    st.markdown('<div class="sec-header"><span>🎯 리스크-수익률 분석</span></div>', unsafe_allow_html=True)
    scatter_metrics = []
    for t in all_data:
        c = all_data[t]["Close"]
        scatter_metrics.append({
            "ticker": t,
            "volatility": calc_volatility(c)["annual_volatility"],
            "return": float(calc_cumulative_return(c).iloc[-1]),
        })
    st.plotly_chart(risk_return_scatter(scatter_metrics), use_container_width=True)

    st.divider()

    # ── 섹터 히트맵
    st.markdown('<div class="sec-header"><span>🗺️ 섹터별 성과 히트맵</span></div>', unsafe_allow_html=True)
    SECTOR_ETFS = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financials": "XLF",
        "Consumer Disc.": "XLY",
        "Industrials": "XLI",
        "Energy": "XLE",
        "Utilities": "XLU",
        "Materials": "XLB",
        "Real Estate": "XLRE",
        "Consumer Staples": "XLP",
        "Communication": "XLC",
    }
    with st.spinner("섹터 데이터 로딩 중..."):
        sector_data = fetch_multiple(list(SECTOR_ETFS.values()), period)

    sector_rows = []
    period_labels = [("1개월", 21), ("3개월", 63), ("6개월", 126), ("기간 전체", None)]
    for sector_name, etf_ticker in SECTOR_ETFS.items():
        if etf_ticker not in sector_data:
            continue
        c = sector_data[etf_ticker]["Close"]
        row = {"섹터": sector_name}
        for label, days in period_labels:
            if days is None:
                row[label] = round(float(calc_cumulative_return(c).iloc[-1]), 2)
            elif len(c) >= days:
                row[label] = round((float(c.iloc[-1]) / float(c.iloc[-days]) - 1) * 100, 2)
            else:
                row[label] = None
        sector_rows.append(row)

    if sector_rows:
        sector_df = pd.DataFrame(sector_rows).set_index("섹터")
        st.plotly_chart(sector_heatmap(sector_df), use_container_width=True)
    else:
        st.info("섹터 데이터를 불러오지 못했습니다.")

# ══════════════════════════════════════════════════════════════
# 탭 4: 투자 인사이트
# ══════════════════════════════════════════════════════════════
with tab_insight:
    # ── 백테스트
    st.markdown('<div class="sec-header"><span>🔬 전략 백테스트</span></div>', unsafe_allow_html=True)
    st.caption("과거 데이터 기반 전략 수익률 시뮬레이션 — yfinance 히스토리 활용")

    bt_col1, bt_col2 = st.columns([1, 3])
    with bt_col1:
        bt_strategy = st.selectbox(
            "전략 선택",
            ["ma_cross", "rsi_reversal"],
            format_func=lambda x: "MA 크로스 (MA20/MA60)" if x == "ma_cross" else "RSI 반전 (30/70)",
        )
        bt_capital = st.number_input("초기 자본 (만원)", value=1000, min_value=100, step=100) * 10000

    bt_result = run_backtest(close, strategy=bt_strategy, initial_capital=bt_capital)

    if bt_result:
        with bt_col1:
            st.divider()
            st.caption("**백테스트 성과**")
            metrics_bt = bt_result["metrics"]
            for k, v in metrics_bt.items():
                color = "#26a69a" if isinstance(v, (int, float)) and v > 0 else "#ef5350" if isinstance(v, (int, float)) and v < 0 else "#D1D4DC"
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:2px 0'>"
                    f"<span style='color:#787B86;font-size:12px'>{k}</span>"
                    f"<span style='color:{color};font-weight:700;font-size:13px'>{v}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with bt_col2:
            strategy_name = "MA 크로스" if bt_strategy == "ma_cross" else "RSI 반전"
            st.plotly_chart(
                backtest_chart(bt_result["portfolio"], bt_result["benchmark"], strategy_name),
                use_container_width=True,
            )
            if bt_result["trades"]:
                with st.expander(f"📋 거래 내역 ({len(bt_result['trades'])}건)"):
                    trades_df = pd.DataFrame(bt_result["trades"])
                    st.dataframe(trades_df, use_container_width=True, hide_index=True)
    else:
        st.info("데이터가 부족합니다 (최소 70거래일 필요). 분석 기간을 늘려주세요.")

    st.divider()

    # ── 매크로 지표
    st.markdown('<div class="sec-header"><span>🌐 매크로 지표</span></div>', unsafe_allow_html=True)
    st.caption("USD/KRW 환율, 미국 10년물 국채, 달러인덱스 추이")
    with st.spinner("매크로 데이터 로딩 중..."):
        macro_period_map = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
        macro_d = fetch_macro_data(macro_period_map.get(period, "1y"))
    if macro_d:
        st.plotly_chart(macro_chart(macro_d), use_container_width=True)
    else:
        st.caption("매크로 데이터를 불러올 수 없습니다.")

    st.divider()

    # ── 종목 스크리너
    st.markdown('<div class="sec-header"><span>📡 종목 스크리너</span></div>', unsafe_allow_html=True)
    st.caption("선택된 모든 종목의 기술적 신호를 한눈에 스캔")

    screener_rows = []
    for t in all_data:
        df_t = all_data[t]
        c_t = df_t["Close"]
        rsi_t = float(calc_rsi(c_t).dropna().iloc[-1])
        mas_t = calc_moving_averages(c_t)
        gc_t = detect_golden_cross(mas_t["MA20"], mas_t["MA60"])
        dc_t = detect_golden_cross(mas_t["MA60"], mas_t["MA20"])
        bb_t = calc_bollinger_bands(c_t)
        macd_t = calc_macd(c_t)
        hist_t = macd_t["histogram"].dropna()

        signals = []
        _ob = _ACFG["rsi_overbought"]
        _os = _ACFG["rsi_oversold"]
        if rsi_t < _os:
            signals.append("🟢 RSI 과매도")
        elif rsi_t > _ob:
            signals.append("🔴 RSI 과매수")

        if gc_t and (c_t.index[-1] - gc_t).days <= 30:
            signals.append("🟢 골든크로스")
        if dc_t and (c_t.index[-1] - dc_t).days <= 30:
            signals.append("🔴 데드크로스")

        upper_bb_t = bb_t["upper"].dropna()
        lower_bb_t = bb_t["lower"].dropna()
        last_p_t = float(c_t.iloc[-1])
        if not upper_bb_t.empty and last_p_t > float(upper_bb_t.iloc[-1]):
            signals.append("🟡 BB 상단")
        elif not lower_bb_t.empty and last_p_t < float(lower_bb_t.iloc[-1]):
            signals.append("🟢 BB 하단")

        if len(hist_t) >= 2:
            if float(hist_t.iloc[-1]) > 0 and float(hist_t.iloc[-2]) <= 0:
                signals.append("🟢 MACD↑")
            elif float(hist_t.iloc[-1]) < 0 and float(hist_t.iloc[-2]) >= 0:
                signals.append("🔴 MACD↓")

        # 52주 신고가 돌파
        _52w = calc_52week_range(c_t)
        if last_p_t >= _52w["high_52"] * 0.99:
            signals.append("🚀 52주 신고가")

        # 거래량 급증 (오늘 거래량 vs 20일 평균)
        if "Volume" in df_t.columns:
            vol_t = df_t["Volume"].dropna()
            if len(vol_t) >= 21:
                avg_vol = float(vol_t.iloc[-21:-1].mean())
                cur_vol = float(vol_t.iloc[-1])
                if avg_vol > 0 and cur_vol >= avg_vol * 2:
                    vol_ratio = cur_vol / avg_vol
                    signals.append(f"📈 거래량 {vol_ratio:.1f}배↑")

        # PER 저평가 + RSI 과매도 복합 신호
        per_t = info_data.get(t, {}).get("pe_ratio")
        if per_t and 0 < float(per_t) < 15 and rsi_t < 40:
            signals.append(f"💎 저PER({per_t:.0f})+저RSI")

        screener_rows.append({
            "종목": t,
            "RSI": round(rsi_t, 1),
            "누적수익률(%)": round(float(calc_cumulative_return(c_t).iloc[-1]), 1),
            "변동성(%)": round(calc_volatility(c_t)["annual_volatility"], 1),
            "샤프": calc_sharpe_ratio(c_t),
            "신호": " / ".join(signals) if signals else "—",
        })

    if screener_rows:
        sc_df = pd.DataFrame(screener_rows).set_index("종목")

        def _color_signal(val):
            if "🟢" in str(val): return "color: #26a69a"
            if "🔴" in str(val): return "color: #ef5350"
            if "🟡" in str(val): return "color: #f7dc6f"
            return ""

        styled_sc = sc_df.style.map(_color_signal, subset=["신호"])
        st.dataframe(styled_sc, use_container_width=True)

    st.divider()
    st.subheader("💡 자동 생성 투자 인사이트")
    st.caption("Skills/insight.md 규칙 기반 자동 분석")

    rsi_values = calc_rsi(close)
    insights = []

    # RSI 신호
    latest_rsi = float(rsi_values.dropna().iloc[-1])
    rsi_signal = get_rsi_signal(latest_rsi)
    _rsi_ob = _ACFG["rsi_overbought"]
    _rsi_os = _ACFG["rsi_oversold"]
    # 인사이트 메시지는 Skills/insight.md 에서 로드 (규칙 변경 시 .md만 수정)
    _insight_rules = {r["condition_raw"]: r for r in load_insight_rules()}
    if rsi_signal == "과매수":
        _rule = _insight_rules.get(f"RSI > {_rsi_ob}", {})
        insights.append(("high", "🔴", "High", "과매수 구간 진입 (RSI)", f"RSI = {latest_rsi:.1f} (기준: >{_rsi_ob})", "단기간 급등으로 매수 세력 과열 상태. 평균 회귀 가능성 증가.", "단기 차익실현 고려. 포지션 축소 검토."))
    elif rsi_signal == "과매도":
        insights.append(("high", "🟢", "High", "과매도 구간 진입 (RSI)", f"RSI = {latest_rsi:.1f} (기준: <{_rsi_os})", "과도한 매도 압력으로 저평가 구간 진입. 반등 가능성 있음.", "저점 매수 기회 탐색. 분할 매수 고려."))
    else:
        insights.append(("info", "🔵", "Info", "RSI 중립 구간", f"RSI = {latest_rsi:.1f} ({_rsi_os}~{_rsi_ob})", "매수/매도 세력 균형 상태. 뚜렷한 방향성 없음.", "특이 신호 없음. 추세 방향 확인 권장."))

    # 골든크로스 / 데드크로스
    mas_all = calc_moving_averages(close)
    gc = detect_golden_cross(mas_all["MA20"], mas_all["MA60"])
    if gc is not None:
        days_ago = (close.index[-1] - gc).days
        if days_ago <= 30:
            insights.append(("medium", "🟢", "Medium", f"골든크로스 발생 ({days_ago}일 전)", "MA20이 MA60 상향 돌파", "단기 추세가 중기 추세를 상회하며 상승 전환 확인.", "중기 상승 추세 진입 신호. 추세 추종 전략 고려."))
        elif days_ago <= 90:
            insights.append(("info", "🔵", "Info", f"골든크로스 유지 중 ({days_ago}일 전 발생)", "MA20 > MA60 상태 유지", "상승 추세가 유지되며 시장 참여자의 매수 심리 지속.", "중기 강세 추세 지속. 모니터링 권장."))

    dc = detect_golden_cross(mas_all["MA60"], mas_all["MA20"])
    if dc is not None:
        days_ago_dc = (close.index[-1] - dc).days
        if days_ago_dc <= 30:
            insights.append(("high", "🔴", "High", f"데드크로스 발생 ({days_ago_dc}일 전)", "MA20이 MA60 하향 돌파", "단기 추세가 중기 추세를 하향 이탈하며 약세 전환 신호.", "중기 약세 추세 진입. 손절선 재검토 권장."))

    # 볼린저 밴드
    bb_data = calc_bollinger_bands(close)
    last_price = float(close.iloc[-1])
    upper = float(bb_data["upper"].iloc[-1]) if not pd.isna(bb_data["upper"].iloc[-1]) else None
    lower = float(bb_data["lower"].iloc[-1]) if not pd.isna(bb_data["lower"].iloc[-1]) else None
    if upper and last_price > upper:
        insights.append(("medium", "🟡", "Medium", "볼린저 밴드 상단 돌파", f"현재가 {last_price:.2f} > 상단 {upper:.2f}", "통계적 정상 범위를 벗어난 과열 구간. 평균 회귀 압력 존재.", "과열 신호. 단기 조정 가능성 모니터링."))
    elif lower and last_price < lower:
        insights.append(("medium", "🟡", "Medium", "볼린저 밴드 하단 이탈", f"현재가 {last_price:.2f} < 하단 {lower:.2f}", "통계적 과매도 구간 진입. 단기 반등 가능성 높음.", "과매도 영역. 반등 탐색 구간."))

    # 샤프 비율
    if sharpe >= 2:
        insights.append(("medium", "🟢", "Medium", "우수한 위험 대비 수익률", f"샤프 비율 = {sharpe:.2f} (≥2)", "감수한 위험 대비 수익률이 시장 기준 이상. 전략 효율성 매우 높음.", "현재 전략 유지. 비중 확대 고려."))
    elif sharpe < 0:
        insights.append(("high", "🔴", "High", "마이너스 위험 대비 수익률", f"샤프 비율 = {sharpe:.2f} (<0)", "무위험 자산보다 낮은 실질 수익. 리스크를 보상받지 못하는 상태.", "포트폴리오 재검토 필요. 헤지 전략 고려."))
    elif sharpe < 1:
        insights.append(("medium", "🟡", "Medium", "위험 대비 수익률 개선 필요", f"샤프 비율 = {sharpe:.2f} (<1)", "감수한 변동성 대비 수익이 기준치에 미달. 효율적 배분 재검토 필요.", "분산투자 또는 저변동성 자산 편입 고려."))

    # MDD
    if mdd < -30:
        insights.append(("high", "🔴", "High", "심각한 낙폭 기록", f"MDD = {mdd:.1f}% (기준: <-30%)", "고점 대비 30% 이상 하락한 이력 있음. 자본 회복에 긴 시간이 필요할 수 있음.", "리스크 관리 긴급 검토. 손절선 재설정 권장."))
    elif mdd < -20:
        insights.append(("medium", "🟡", "Medium", "주의 낙폭 기록", f"MDD = {mdd:.1f}% (기준: <-20%)", "고점 대비 20~30% 하락 이력. 변동성이 큰 자산으로 관리 필요.", "포트폴리오 리밸런싱 검토 권장."))

    # 벤치마크 대비 성과
    if show_benchmark and not benchmark_data.empty:
        sp_cum = float(calc_cumulative_return(benchmark_data["Close"]).iloc[-1])
        diff = cum_return - sp_cum
        if diff > 10:
            insights.append(("medium", "🟢", "Medium", f"{benchmark_name} 대비 초과 수익 ({diff:+.1f}%p)", f"종목: {cum_return:+.1f}% vs {benchmark_name}: {sp_cum:+.1f}%", "시장 평균을 10%p 이상 상회하는 알파 창출 중.", "시장 대비 우수한 성과. 전략 유지."))
        elif diff < -10:
            insights.append(("medium", "🟡", "Medium", f"{benchmark_name} 대비 저조한 성과 ({diff:+.1f}%p)", f"종목: {cum_return:+.1f}% vs {benchmark_name}: {sp_cum:+.1f}%", "시장 평균을 10%p 이상 하회. 액티브 전략의 실효성 점검 필요.", "인덱스 ETF 편입 비교 검토 권장."))

    # MACD 신호 추가
    macd_result = calc_macd(close)
    macd_last = float(macd_result["macd"].dropna().iloc[-1])
    signal_last = float(macd_result["signal"].dropna().iloc[-1])
    hist_last = float(macd_result["histogram"].dropna().iloc[-1])
    hist_prev = float(macd_result["histogram"].dropna().iloc[-2]) if len(macd_result["histogram"].dropna()) >= 2 else 0
    if hist_last > 0 and hist_prev <= 0:
        insights.append(("medium", "🟢", "Medium", "MACD 골든크로스 발생", f"MACD({macd_last:.3f}) > Signal({signal_last:.3f})", "단기 지수이평이 시그널선을 상향 돌파. 모멘텀 상승 전환 신호.", "단기 상승 모멘텀 전환. 매수 타이밍 탐색."))
    elif hist_last < 0 and hist_prev >= 0:
        insights.append(("medium", "🔴", "Medium", "MACD 데드크로스 발생", f"MACD({macd_last:.3f}) < Signal({signal_last:.3f})", "단기 지수이평이 시그널선을 하향 이탈. 모멘텀 하락 전환 신호.", "단기 하락 모멘텀 전환. 포지션 점검 권장."))

    # 우선순위 정렬
    priority_order = {"High": 0, "Medium": 1, "Info": 2}
    insights.sort(key=lambda x: priority_order.get(x[2], 3))

    # ── HTML 인사이트 카드 렌더링 (신호 → 해석 → 행동 제안 3단계)
    for card_type, emoji, priority, title, signal, interpretation, action in insights:
        css_class = f"ins-{card_type}"
        st.markdown(f"""
        <div class="{css_class}">
            <div class="ins-title">{emoji} [{priority}] {title}</div>
            <div class="ins-grid">
                <div class="ins-box">
                    <div class="ins-box-label">📡 신호</div>
                    <div class="ins-box-val">{signal}</div>
                </div>
                <div class="ins-box">
                    <div class="ins-box-label">🔍 해석</div>
                    <div class="ins-box-val">{interpretation}</div>
                </div>
                <div class="ins-box">
                    <div class="ins-box-label">🎯 행동 제안</div>
                    <div class="ins-box-val">{action}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 종합 요약
    st.divider()
    high_count = sum(1 for x in insights if x[2] == "High")
    medium_count = sum(1 for x in insights if x[2] == "Medium")
    st.info(f"**분석 요약:** 총 {len(insights)}개 신호 감지 — 🔴 High: {high_count}개 / 🟡 Medium: {medium_count}개")

    # ── 자동 텍스트 리포트
    st.divider()
    st.subheader("📄 자동 생성 투자 리포트")

    info_r = info_data.get(main_ticker, {})
    analysis_date = pd.Timestamp.now().strftime("%Y년 %m월 %d일")
    period_label = {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년", "2y": "2년", "5y": "5년"}.get(period, period)

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
        sp_line = f"- **벤치마크({benchmark_name}) 대비 알파:** {alpha:+.1f}%p ({cum_return:+.1f}% vs {sp_cum_r:+.1f}%)"

    mom_line = " / ".join(
        f"{k}: {v:+.1f}%" for k, v in momentum.items() if v is not None
    )

    report_text = f"""**{info_r.get('name', main_ticker)} ({main_ticker}) 투자 분석 리포트**
분석 기준일: {analysis_date} | 분석 기간: {period_label}

---

**📌 종합 판단: {overall}**
{overall_detail}

---

**📊 핵심 지표 요약**
- **현재가:** {price_str} (전일 대비 {daily_change:+.2f}%)
- **기간 누적 수익률:** {cum_return:+.1f}% (연환산 {ann_return:+.1f}%)
- **모멘텀:** {mom_line}
- **연환산 변동성:** {volatility:.1f}%
- **샤프 비율:** {sharpe:.2f} ({'우수' if sharpe >= 2 else '양호' if sharpe >= 1 else '검토 필요'})
- **최대 낙폭(MDD):** {mdd:.1f}%
- **52주 범위 위치:** {pct:.0f}% (저가 {fmt_price(low_52)} ~ 고가 {fmt_price(high_52)})
{sp_line}

---

**🔍 주요 기술적 신호**
{chr(10).join(f"- [{p}] {t}: {s}" for _, _, p, t, s, _, _ in insights if p in ("High", "Medium"))}

---

**🎯 핵심 행동 제안**
{chr(10).join(f"- {a}" for _, _, p, _, _, _, a in insights if p == "High") or "- 현재 High 등급 신호 없음"}

---
*본 리포트는 Skills/insight.md 규칙 기반으로 자동 생성되었습니다. 투자 판단은 본인 책임입니다.*
"""
    st.markdown(report_text)

    st.download_button(
        label="📥 리포트 다운로드 (.txt)",
        data=report_text.replace("**", "").replace("---", "─" * 40),
        file_name=f"{main_ticker}_report_{pd.Timestamp.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )
