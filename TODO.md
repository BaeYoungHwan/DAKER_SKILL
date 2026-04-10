# TODO — 금융 투자 대시보드

## 진행 중

## 대기 중

### 🔴 High Impact (바로 추가 가능)
- [x] 종목 뉴스 피드 — yfinance `ticker.news` 기반 최신 뉴스 + 링크 (종목 분석 탭)
- [x] 드로다운 차트 — 시간별 낙폭 곡선 시각화 (MDD 수치 → 차트로 전환)
- [x] 스토캐스틱 지표 — %K, %D 라인 차트 + 과매수/과매도 영역

### 🟡 Medium Impact (yfinance 데이터 활용)
- [x] 실적 히스토리 차트 — EPS 예상치 vs 실제치 분기별 바 차트 + 어닝 서프라이즈
- [x] 롤링 샤프 비율 / 롤링 수익률 차트 — 시간에 따른 성과 추이 (포트폴리오 탭)
- [x] 섹터 히트맵 — SPY/XLK/XLF 등 섹터 ETF 기반 섹터별 성과 비교

### 🟢 Nice to Have
- [x] 공포/탐욕 지수 (Fear & Greed) — 시장 센티먼트 카드 (시장 지수 스트립 추가)
- [x] 워치리스트 즐겨찾기 — 새로고침 후에도 종목 유지 (로컬 JSON 저장)

### 📊 비교 분석 탭 보완
- [x] 상관관계 히트맵 — `correlation_heatmap()` 함수 있으나 탭에 미연결
- [x] 리스크-수익률 산점도 — 종목별 변동성(X) vs 수익률(Y) 버블 차트

### 🆕 추가 기능
- [x] 스크리너 — RSI<30/70, 골든크로스 등 조건 기반 종목 신호 탭
- [x] 재무제표 트렌드 — PER/PBR/ROE 분기별 추이 차트 (종목 분석 탭)
- [x] 배당 달력 — 배당락일 타임라인 + 배당수익률 히스토리 (종목 분석 탭)
- [x] 백테스트 — MA 크로스 / RSI 반전 전략 수익률 시뮬레이션 (탭4 상단)
- [x] 실적 캘린더 — 다음 실적 발표일 + EPS 서프라이즈 + 변동성 경고 (종목 분석 탭)
- [x] 기관 수급 현황 — major_holders / institutional_holders 표시 (종목 분석 탭)
- [x] 매크로 지표 — USD/KRW, 10년물 국채, 달러인덱스 변화율 차트 (탭4)
- [x] 스크리너 확장 — 52주 신고가, 거래량 N배 급증, 저PER+저RSI 복합조건 추가

### 🐛 버그 / 데이터 이슈
- [x] 005930.KS 수익률 이상 (+290.9%) — 누적수익률 >150% 시 auto_adjust 안내 경고 표시 처리
- [x] G2/B6 기간 버튼 x축 확장 — chart_df 범위로 MA/BB reindex 처리
- [x] B16 Date 컬럼 시간 표시 — strftime("%Y-%m-%d") 적용
- [x] B14 배당 횟수/성장률 오류 — 오늘 기준 12개월 카운트, 완전 연도끼리만 비교로 수정
- [x] QA 미확인 항목 코드 검증 — A8~A11 사이드바 위젯 정상 연결, C3/C7/C9~C11 포트폴리오 기능 모두 구현 확인

### 📈 Score 개선 (감점 사유 대응)
- [x] Rate Limit 핸들링 — fetch_price 재시도, fetch_multiple 요청 간 지연 추가
- [x] KR_NAME_MAP 확장 — 25개 → 70+개 (반도체·배터리·바이오·금융·통신 등 확장)
- [x] KR_TICKER_TO_NAME 중복 해소 — 공식명 우선(긴 이름) + 검색 결과 중복 제거

### 🚀 배포
- [x] requirements.txt 최신화 확인 (충분)
- [x] .env / watchlist.json gitignore 확인 (포함됨)
- [x] .streamlit/config.toml 커밋 (TradingView Dark 테마 설정 포함)
- [x] Streamlit Cloud 배포 (https://dakerskills.streamlit.app)
- [ ] 기획서 PDF 작성 (README 포함)

## 완료
- [x] 프로젝트 세팅 (CLAUDE.md, agents, 폴더 구조)
- [x] Skills/analysis.md 작성
- [x] Skills/visualization.md 작성
- [x] Skills/insight.md 작성
- [x] src/data/fetcher.py 구현
- [x] src/analysis/indicators.py 구현
- [x] src/viz/charts.py 구현
- [x] src/app.py Streamlit 메인 구현
- [x] UI/UX 기획서 작성 (docs/design-plan.md)
- [x] TradingView Dark 테마 CSS 전면 적용
