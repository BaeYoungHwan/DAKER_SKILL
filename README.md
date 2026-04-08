# 금융 투자 대시보드

> yfinance 실시간 데이터 기반 금융 투자 분석 대시보드 — 해커톤 제출작

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

---

## 개요

투자 분석 규칙을 정의한 **Skills.md** 문서를 기반으로 바이브 코딩을 활용해 구현한 금융 투자 대시보드입니다.

API Key 없이 [yfinance](https://github.com/ranaroussi/yfinance)를 통해 실시간 주가 · ETF · 재무지표 데이터를 수집하고, Skills 문서에 정의된 분석 규칙에 따라 자동으로 시각화 및 인사이트를 생성합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 실시간 데이터 | yfinance 기반 주가 · ETF · 재무지표 조회 (API Key 불필요) |
| 기술적 지표 | 이동평균선, RSI, 볼린저 밴드, 변동성, 샤프 비율, MDD |
| 포트폴리오 분석 | 자산 배분, 상관관계 히트맵, 분산도 평가 |
| 자동 인사이트 | Skills.md 규칙 기반 매수/매도 신호 자동 생성 |
| 수익률 비교 | 다중 종목 누적 수익률 비교 차트 |

---

## Skills 문서

투자 분석 기준을 정의한 핵심 문서입니다.

| 문서 | 내용 |
|------|------|
| [`Skills/analysis.md`](Skills/analysis.md) | 투자 데이터 분석 기준 · 지표 계산 규칙 |
| [`Skills/visualization.md`](Skills/visualization.md) | 시각화 선택 기준 · 차트 구성 규칙 |
| [`Skills/insight.md`](Skills/insight.md) | 인사이트 생성 규칙 · 리포트 구성 흐름 |

---

## 기술 스택

- **언어:** Python 3.12
- **프레임워크:** Streamlit
- **데이터:** yfinance (Yahoo Finance)
- **시각화:** Plotly
- **배포:** Streamlit Cloud

---

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run src/app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 프로젝트 구조

```
├── Skills/                  # 투자 분석 규칙 문서 (핵심)
│   ├── analysis.md          # 분석 기준 & 지표 계산 규칙
│   ├── visualization.md     # 시각화 선택 기준
│   └── insight.md           # 인사이트 생성 규칙
├── src/
│   ├── app.py               # Streamlit 메인 앱
│   ├── data/fetcher.py      # yfinance 데이터 수집
│   ├── analysis/indicators.py  # 기술적 지표 계산
│   └── viz/charts.py        # Plotly 차트 컴포넌트
└── requirements.txt
```

---

## 데이터 출처

Yahoo Finance (via yfinance) — API Key 불필요, 외부 접속 가능
