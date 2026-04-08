"""
Plotly 차트 컴포넌트 모듈
Skills/visualization.md 시각화 선택 기준 준수
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional


# 색상 규칙 (Skills/visualization.md §3.3)
COLOR_UP = "#26a69a"
COLOR_DOWN = "#ef5350"
COLOR_NEUTRAL = "#5c6bc0"
COLOR_MA = {"MA5": "#FFD700", "MA20": "#FFA500", "MA60": "#4FC3F7", "MA120": "#CE93D8", "MA200": "#80CBC4"}
COLOR_BB = "rgba(92, 107, 192, 0.2)"


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

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title=title,
        yaxis_title="누적 수익률 (%)" if normalize else "가격",
        template="plotly_dark",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
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
    )
    return fig


def portfolio_treemap(weights: dict[str, float]) -> go.Figure:
    """포트폴리오 트리맵 (종목 수 > 7)"""
    fig = px.treemap(
        names=list(weights.keys()),
        values=list(weights.values()),
        title="포트폴리오 자산 배분",
    )
    fig.update_layout(template="plotly_dark", height=350)
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
        yaxis=dict(range=[0, 100]),
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig
