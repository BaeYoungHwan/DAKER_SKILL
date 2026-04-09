"""
Plotly 차트 컴포넌트 모듈
Skills/visualization.md 시각화 선택 기준 준수
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional


# 색상 규칙 (Skills/visualization.md §6 테마 토큰 기준)
COLOR_UP = "#26a69a"
COLOR_DOWN = "#ef5350"
COLOR_NEUTRAL = "#7B68EE"
COLOR_MA = {"MA5": "#FFD700", "MA20": "#FFA500", "MA60": "#4FC3F7", "MA120": "#CE93D8", "MA200": "#80CBC4"}
COLOR_BB = "rgba(123, 104, 238, 0.2)"

# 차트 다크 테마 상수
CHART_BGCOLOR = "#131722"
CHART_PAPER_BGCOLOR = "#1E222D"
CHART_FONT_COLOR = "#D1D4DC"
CHART_GRID_COLOR = "#2A2E39"
CHART_FONT_FAMILY = "Inter, -apple-system, sans-serif"


def candlestick_chart(
    df: pd.DataFrame,
    ticker: str,
    mas: Optional[dict[str, pd.Series]] = None,
    bb: Optional[dict[str, pd.Series]] = None,
) -> go.Figure:
    """캔들스틱 + 거래량 차트 (Skills/visualization.md §2.1)"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color=COLOR_UP,
            decreasing_line_color=COLOR_DOWN,
        ),
        row=1, col=1,
    )

    # 이동평균선 오버레이
    if mas:
        for ma_name, ma_values in mas.items():
            if ma_name in COLOR_MA:
                fig.add_trace(
                    go.Scatter(
                        x=ma_values.index,
                        y=ma_values,
                        name=ma_name,
                        line=dict(color=COLOR_MA[ma_name], width=1.2),
                        opacity=0.8,
                    ),
                    row=1, col=1,
                )

    # 볼린저 밴드
    if bb:
        fig.add_trace(
            go.Scatter(
                x=bb["upper"].index, y=bb["upper"],
                name="BB Upper", line=dict(color=COLOR_NEUTRAL, width=0.8, dash="dash"),
                showlegend=False,
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=bb["lower"].index, y=bb["lower"],
                name="BB Lower", line=dict(color=COLOR_NEUTRAL, width=0.8, dash="dash"),
                fill="tonexty", fillcolor=COLOR_BB,
                showlegend=False,
            ),
            row=1, col=1,
        )

    # 거래량 바 차트
    colors = [COLOR_UP if c >= o else COLOR_DOWN
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name="거래량", marker_color=colors, opacity=0.6),
        row=2, col=1,
    )

    fig.update_layout(
        title=f"{ticker} 주가 차트",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=550,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        xaxis2=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis2=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
    )
    return fig


def line_chart_multi(
    close_prices: pd.DataFrame,
    title: str = "수익률 비교",
    normalize: bool = True,
) -> go.Figure:
    """다중 종목 수익률 비교 라인 차트 (Skills/visualization.md §2.2)"""
    fig = go.Figure()

    for col in close_prices.columns:
        y = (close_prices[col] / close_prices[col].iloc[0] - 1) * 100 if normalize else close_prices[col]
        fig.add_trace(go.Scatter(x=close_prices.index, y=y, name=col, mode="lines"))

    fig.add_hline(y=0, line_dash="dash", line_color=CHART_GRID_COLOR, opacity=0.8)
    fig.update_layout(
        title=title,
        yaxis_title="누적 수익률 (%)" if normalize else "가격",
        template="plotly_dark",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
    )
    return fig


def portfolio_pie(weights: dict[str, float]) -> go.Figure:
    """포트폴리오 비중 파이 차트 (Skills/visualization.md §2.3)"""
    # 3% 미만은 기타로 묶음
    other = sum(v for v in weights.values() if v < 3)
    filtered = {k: v for k, v in weights.items() if v >= 3}
    if other > 0:
        filtered["기타"] = other

    if len(filtered) > 7:
        # 트리맵으로 전환
        return portfolio_treemap(weights)

    fig = go.Figure(go.Pie(
        labels=list(filtered.keys()),
        values=list(filtered.values()),
        hole=0.4,
        textinfo="label+percent",
    ))
    fig.update_layout(
        title="포트폴리오 자산 배분",
        template="plotly_dark",
        height=350,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
    )
    return fig


def portfolio_treemap(weights: dict[str, float]) -> go.Figure:
    """포트폴리오 트리맵 (종목 수 > 7)"""
    fig = px.treemap(
        names=list(weights.keys()),
        values=list(weights.values()),
        title="포트폴리오 자산 배분",
    )
    fig.update_layout(
        template="plotly_dark",
        height=350,
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
    )
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame) -> go.Figure:
    """상관관계 히트맵 (Skills/visualization.md §2.4)"""
    fig = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale="RdBu",
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate="%{text}",
        colorbar=dict(title="상관계수"),
    ))
    fig.update_layout(
        title="자산 간 상관관계",
        template="plotly_dark",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
    )
    return fig


def rsi_gauge_chart(rsi_value: float, ticker: str) -> go.Figure:
    """RSI 게이지 차트 (반원 속도계 스타일)"""
    if rsi_value > 70:
        bar_color = COLOR_DOWN
        label = "과매수"
    elif rsi_value < 30:
        bar_color = COLOR_UP
        label = "과매도"
    else:
        bar_color = COLOR_NEUTRAL
        label = "중립"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi_value,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": f"RSI (14) — <b>{label}</b>", "font": {"size": 14, "color": CHART_FONT_COLOR}},
        number={"font": {"size": 36, "color": bar_color}, "valueformat": ".1f"},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#787B86",
                "tickvals": [0, 30, 50, 70, 100],
                "ticktext": ["0", "30", "50", "70", "100"],
                "tickfont": {"size": 11, "color": CHART_FONT_COLOR},
            },
            "bar": {"color": bar_color, "thickness": 0.3},
            "bgcolor": CHART_PAPER_BGCOLOR,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(38, 166, 154, 0.18)"},
                {"range": [30, 70], "color": "rgba(200, 200, 200, 0.12)"},
                {"range": [70, 100], "color": "rgba(239, 83, 80, 0.18)"},
            ],
            "threshold": {
                "line": {"color": bar_color, "width": 4},
                "thickness": 0.85,
                "value": rsi_value,
            },
        },
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=55, b=10),
        template="plotly_dark",
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        annotations=[
            dict(x=0.13, y=0.08, text="과매도<br>(30)", showarrow=False,
                 font=dict(size=10, color="#26a69a"), align="center"),
            dict(x=0.87, y=0.08, text="과매수<br>(70)", showarrow=False,
                 font=dict(size=10, color="#ef5350"), align="center"),
        ],
    )
    return fig


def macd_chart(macd_data: dict, ticker: str) -> go.Figure:
    """MACD 차트 (히스토그램 + MACD 라인 + 시그널 라인)"""
    macd = macd_data["macd"]
    signal = macd_data["signal"]
    hist = macd_data["histogram"]

    hist_colors = [COLOR_UP if v >= 0 else COLOR_DOWN for v in hist.fillna(0)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=hist.index, y=hist,
        name="히스토그램",
        marker_color=hist_colors,
        opacity=0.65,
    ))
    fig.add_trace(go.Scatter(
        x=macd.index, y=macd,
        name="MACD",
        line=dict(color="#4FC3F7", width=1.8),
    ))
    fig.add_trace(go.Scatter(
        x=signal.index, y=signal,
        name="Signal",
        line=dict(color="#FF7043", width=1.8),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=CHART_GRID_COLOR, opacity=0.8)

    fig.update_layout(
        title=f"{ticker} MACD (12, 26, 9)",
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
    )
    return fig


def rsi_chart(rsi: pd.Series, ticker: str) -> go.Figure:
    """RSI 차트 (Skills/visualization.md §2.5)"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI", line=dict(color=COLOR_NEUTRAL, width=1.5)))
    fig.add_hline(y=70, line_dash="dash", line_color=COLOR_DOWN, annotation_text="과매수(70)")
    fig.add_hline(y=30, line_dash="dash", line_color=COLOR_UP, annotation_text="과매도(30)")
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.4)

    # 과매수/과매도 영역 색상
    fig.add_hrect(y0=70, y1=100, fillcolor=COLOR_DOWN, opacity=0.08, line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor=COLOR_UP, opacity=0.08, line_width=0)

    fig.update_layout(
        title=f"{ticker} RSI (14)",
        yaxis=dict(range=[0, 100], gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
    )
    return fig


def drawdown_chart(drawdown: pd.Series, ticker: str) -> go.Figure:
    """드로다운 시계열 차트 — 낙폭 영역 빨간 fill"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown,
        fill="tozeroy",
        fillcolor="rgba(239, 83, 80, 0.15)",
        line=dict(color=COLOR_DOWN, width=1.2),
        name="Drawdown",
    ))
    mdd = float(drawdown.min())
    mdd_date = drawdown.idxmin()
    fig.add_annotation(
        x=mdd_date, y=mdd,
        text=f"MDD {mdd:.1f}%",
        showarrow=True, arrowhead=2,
        font=dict(color=COLOR_DOWN, size=11),
        arrowcolor=COLOR_DOWN,
    )
    fig.update_layout(
        title=f"{ticker} 드로다운 (Drawdown)",
        yaxis_title="낙폭 (%)",
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
    )
    return fig


def risk_return_scatter(metrics: list) -> go.Figure:
    """리스크-수익률 산점도 — 변동성(X) vs 누적수익률(Y)"""
    fig = go.Figure()
    for m in metrics:
        color = COLOR_UP if m["return"] >= 0 else COLOR_DOWN
        fig.add_trace(go.Scatter(
            x=[m["volatility"]], y=[m["return"]],
            mode="markers+text",
            text=[m["ticker"]],
            textposition="top center",
            marker=dict(size=16, color=color, line=dict(color="white", width=1.5)),
            name=m["ticker"],
            showlegend=False,
        ))
    fig.add_hline(y=0, line_dash="dash", line_color=CHART_GRID_COLOR, opacity=0.8)
    fig.update_layout(
        title="리스크-수익률 산점도",
        xaxis_title="연환산 변동성 (%)",
        yaxis_title="누적 수익률 (%)",
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
    )
    return fig


def stochastic_chart(stoch: dict, ticker: str) -> go.Figure:
    """스토캐스틱 %K / %D 차트"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=stoch["k"].index, y=stoch["k"],
        name="%K", line=dict(color="#4FC3F7", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=stoch["d"].index, y=stoch["d"],
        name="%D", line=dict(color="#FF7043", width=1.5, dash="dash"),
    ))
    fig.add_hline(y=80, line_dash="dash", line_color=COLOR_DOWN, opacity=0.6, annotation_text="과매수(80)")
    fig.add_hline(y=20, line_dash="dash", line_color=COLOR_UP, opacity=0.6, annotation_text="과매도(20)")
    fig.add_hrect(y0=80, y1=100, fillcolor=COLOR_DOWN, opacity=0.06, line_width=0)
    fig.add_hrect(y0=0, y1=20, fillcolor=COLOR_UP, opacity=0.06, line_width=0)
    fig.update_layout(
        title=f"{ticker} 스토캐스틱 (14, 3)",
        yaxis=dict(range=[0, 100], gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
    )
    return fig


def rolling_sharpe_chart(close_prices: pd.DataFrame, window: int = 60) -> go.Figure:
    """종목별 롤링 샤프 비율 차트"""
    from analysis.indicators import calc_rolling_sharpe

    COLORS = [COLOR_UP, COLOR_NEUTRAL, "#F7DC6F", "#BB8FCE", "#85C1E9", "#F1948A"]
    fig = go.Figure()
    for i, ticker in enumerate(close_prices.columns):
        rs = calc_rolling_sharpe(close_prices[ticker], window=window)
        fig.add_trace(go.Scatter(
            x=rs.index, y=rs,
            name=ticker,
            line=dict(color=COLORS[i % len(COLORS)], width=1.5),
        ))
    fig.add_hline(y=1, line_dash="dash", line_color=COLOR_UP, opacity=0.6,
                  annotation_text="Sharpe=1", annotation_font_color=COLOR_UP)
    fig.add_hline(y=0, line_dash="dot", line_color=CHART_GRID_COLOR, opacity=0.8)
    fig.update_layout(
        title=f"롤링 샤프 비율 ({window}일 기준)",
        yaxis_title="샤프 비율",
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def earnings_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """분기별 EPS 예상 vs 실제 바 차트"""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index, y=df["EPS Estimate"],
        name="EPS 예상", marker_color="#787B86", opacity=0.7,
    ))
    colors = [COLOR_UP if v >= 0 else COLOR_DOWN for v in df["Reported EPS"]]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Reported EPS"],
        name="EPS 실제", marker_color=colors, opacity=0.9,
    ))
    for idx, row in df.iterrows():
        surprise = row.get("Surprise %", 0)
        if pd.notna(surprise):
            color = COLOR_UP if surprise >= 0 else COLOR_DOWN
            fig.add_annotation(
                x=idx, y=row["Reported EPS"],
                text=f"{surprise:+.1f}%",
                showarrow=False, yshift=12,
                font=dict(size=10, color=color),
            )
    fig.update_layout(
        title=f"{ticker} 분기별 EPS (예상 vs 실제)",
        barmode="overlay",
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR, title="EPS ($)"),
    )
    return fig


def sector_heatmap(sector_returns: pd.DataFrame) -> go.Figure:
    """섹터별 기간 수익률 히트맵 (행=섹터, 열=기간)"""
    z = sector_returns.values.tolist()
    text = [[f"{v:+.1f}%" if v is not None and not (isinstance(v, float) and pd.isna(v)) else "N/A"
              for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z,
        x=sector_returns.columns.tolist(),
        y=sector_returns.index.tolist(),
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11, family=CHART_FONT_FAMILY),
        colorscale=[[0, COLOR_DOWN], [0.5, "#2A2E39"], [1, COLOR_UP]],
        zmid=0,
        showscale=True,
        colorbar=dict(
            title="수익률(%)",
            tickfont=dict(color=CHART_FONT_COLOR),
        ),
    ))
    fig.update_layout(
        title="섹터별 성과 히트맵",
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(side="top", gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
    )
    return fig


def financials_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """분기별 매출/순이익 바 차트"""
    fig = go.Figure()
    col_colors = {"매출": COLOR_NEUTRAL, "순이익": COLOR_UP, "매출총이익": "#F7DC6F"}
    for col in df.columns:
        color = col_colors.get(col, COLOR_NEUTRAL)
        fig.add_trace(go.Bar(
            x=df.index.tolist(),
            y=df[col].tolist(),
            name=col,
            marker_color=color,
            opacity=0.85,
        ))
    fig.update_layout(
        title=f"{ticker} 분기별 재무 현황 (십억 $)",
        barmode="group",
        template="plotly_dark",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR, title="십억 ($B)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def dividend_chart(dividends: "pd.Series", ticker: str) -> go.Figure:
    """배당금 히스토리 바 차트 (최근 4년)"""
    import pandas as pd
    recent = dividends.tail(16)  # 최근 16분기
    colors = [COLOR_UP] * len(recent)
    fig = go.Figure(go.Bar(
        x=recent.index.strftime("%Y-%m").tolist(),
        y=recent.values.tolist(),
        marker_color=colors,
        name="배당금",
    ))
    fig.update_layout(
        title=f"{ticker} 배당금 히스토리",
        template="plotly_dark",
        height=250,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=CHART_PAPER_BGCOLOR,
        plot_bgcolor=CHART_BGCOLOR,
        font=dict(color=CHART_FONT_COLOR, family=CHART_FONT_FAMILY),
        xaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR),
        yaxis=dict(gridcolor=CHART_GRID_COLOR, linecolor=CHART_GRID_COLOR, title="배당금 ($)"),
    )
    return fig
