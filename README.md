# DAKER — 금융 투자 분석 대시보드

> Skills.md로 규칙을 정의하고, 바이브 코딩으로 구현한 실시간 금융 투자 분석 대시보드

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/BaeYoungHwan/DAKER_SKILL)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![yfinance](https://img.shields.io/badge/yfinance-latest-green)

---

## 소개

API Key 없이 **Yahoo Finance(yfinance)** 를 통해 글로벌·한국 주식 실시간 데이터를 조회하고,  
**Skills.md** 에 정의된 분석 규칙을 바탕으로 차트·지표·인사이트를 자동 생성하는 투자 분석 도구입니다.

Skills 문서 → `src/skills/parser.py` → 코드 주입의 런타임 파이프라인으로,  
**파일 수정만으로 분석 임계치·색상·인사이트 규칙이 즉시 반영**됩니다.

---

## 주요 기능

### 종목 분석 탭
- 시장 지수 스트립 (S&P500 · NASDAQ · DOW · KOSPI · VIX) + 공포/탐욕 지수
- KPI 카드: 현재가 / 누적수익률 / 연환산변동성 / 샤프비율 / MDD
- 재무지표: PER / PBR / EPS / 배당수익률
- 캔들스틱 차트 + MA(5/20/60/120/200) + 볼린저밴드 + 거래량
- MACD · RSI · 스토캐스틱 · 드로다운 차트
- 분기별 실적 (EPS 어닝서프라이즈) · 배당 히스토리 · 최신 뉴스

### 포트폴리오 탭
- 종목별 비중·수익률·샤프·MDD·베타 성과 테이블
- KRW/USD 혼합 포트폴리오 실시간 환율 자동 적용
- 매입가·수량 입력 → 평가손익 자동 계산
- 가중 누적수익률 차트 (vs 벤치마크) · 롤링 샤프비율 차트

### 비교 분석 탭
- 다중 종목 누적수익률 멀티라인 비교
- 상관관계 히트맵 · 리스크-수익률 산점도
- 섹터 히트맵 (11개 섹터 ETF 기간별 성과)

### 투자 인사이트 탭
- 종목 스크리너: RSI·골든크로스 조건 기반 신호 테이블
- 인사이트 카드: High/Medium/Info 등급별 (신호→해석→행동 3단계)
- 자동 투자 리포트 생성 및 .txt 다운로드

---

## Skills 문서 (바이브코딩 기반)

투자 분석 기준을 먼저 문서로 정의하고, AI가 코드를 생성하는 방식으로 개발되었습니다.

| 문서 | 내용 |
|------|------|
| [`Skills/analysis.md`](Skills/analysis.md) | 투자 지표 계산 규칙 · 포트폴리오 분산 기준 · 공매도/레버리지 예외 처리 |
| [`Skills/visualization.md`](Skills/visualization.md) | 차트 선택 기준 · CSS 테마 토큰 · 레이아웃 비율 시스템 |
| [`Skills/insight.md`](Skills/insight.md) | 인사이트 등급·형식·우선순위 규칙 |
| [`Skills/interaction.md`](Skills/interaction.md) | Session State 초기화 · 워치리스트 영속성 · URL 파라미터 규칙 |
| [`Skills/symbols.json`](Skills/symbols.json) | 한국어 종목명 → 티커 변환 맵 (외부 파일 관리) |

### Skills 런타임 파이프라인

```
Skills/*.md  →  src/skills/parser.py  →  indicators.py / charts.py / app.py
                    (lru_cache)              임계치·색상·인사이트 규칙 주입
```

Skills 파일만 수정하면 코드 변경 없이 분석 규칙이 즉시 반영됩니다.

---

## 한국 주식 지원

한국어 종목명으로 검색 → 자동 티커 변환 (70개+ 종목, `Skills/symbols.json` 관리)

```
삼성전자 → 005930.KS
SK하이닉스 → 000660.KS
카카오 → 035720.KS
```

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| UI | Streamlit |
| 데이터 | yfinance |
| 시각화 | Plotly |
| 배포 | Streamlit Cloud |

---

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

`http://localhost:8501` 접속

---

## 프로젝트 구조

```
├── Skills/                      # 투자 분석 규칙 문서 (바이브코딩 기반)
│   ├── analysis.md              # 지표 계산 · 포트폴리오 분석 규칙
│   ├── visualization.md         # 차트 기준 · 테마 토큰 · 레이아웃 비율
│   ├── insight.md               # 인사이트 등급·형식 규칙
│   ├── interaction.md           # UI 상태 관리 · 워치리스트 규칙
│   └── symbols.json             # 한국어 종목명 티커 맵
├── src/
│   ├── app.py                   # Streamlit 메인 앱
│   ├── skills/parser.py         # Skills.md 런타임 파서 (lru_cache)
│   ├── data/
│   │   ├── base.py              # DataProvider ABC (데이터 소스 추상화)
│   │   ├── yfinance_provider.py # YFinanceProvider 구현체
│   │   └── fetcher.py           # 3회 지수 백오프 재시도 · Rate Limit 방어
│   ├── analysis/indicators.py   # 기술적 지표 계산 (Skills 임계치 주입)
│   └── viz/charts.py            # Plotly 차트 컴포넌트 (Skills 색상 토큰 주입)
├── docs/
│   └── 기획서.md
├── agents/                      # Claude Code 병렬 에이전트 정의
└── requirements.txt
```

---

## 데이터 출처

Yahoo Finance (via yfinance) — API Key 불필요
