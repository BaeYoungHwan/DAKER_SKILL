# 금융 투자 대시보드 — Claude Code 지침

## 개요
yfinance 실시간 데이터 기반 금융 투자 분석 대시보드 (해커톤 제출용)

## 환경
- Language: Python 3.12
- Framework: Streamlit + Plotly + yfinance + pandas
- OS: Windows 11
- Editor: VS Code + Claude Code
- 배포: Streamlit Cloud

## 코딩 규칙
- 변수명, 함수명, 코드: 영어
- 주석, 커밋 메시지, 소통: 한국어
- 민감정보(API 키 등)는 .env로 관리, 절대 커밋 금지

## 참조 문서 규칙
- CLAUDE.md는 항상 참조해야 하는 핵심 규칙만 유지 (간소화)
- 특정 상황에만 필요한 문서는 `docs/ref/`에 배치
- 에이전트가 필요할 때만 ref 파일을 참조
- TODO.md 작업 시 → `docs/ref/todo-workflow.md` 참조

## 모델 사용 규칙
- Plan 모드: Opus
- 개발(코딩, 디버깅 등): Sonnet

## 에이전트 사용 규칙
- `agents/` 폴더의 에이전트는 **병렬 처리 서브태스크** 전용
- Plan 모드로 설계 후, 독립적으로 분리 가능한 작업은 반드시 에이전트로 병렬 실행
- 새 프로젝트 시작 시 `agents/example-agent.md`를 복사해서 역할별 에이전트 생성
  - 예: `frontend.md`, `backend.md`, `db.md` 등 모듈 단위로 분리

## 알림
- 1차: PC 토스트 알림 (global-setup 설치 시 자동 동작)
- 2차: [추후 도입 예정]

## 프로젝트 구조
```
Daker_skills/
├── CLAUDE.md
├── TODO.md
├── requirements.txt
├── .claude/settings.json
├── .env                    # gitignore 대상
├── agents/                 # Claude Code 병렬 에이전트
│   ├── data.md             # yfinance 데이터 수집/처리
│   ├── viz.md              # Plotly 시각화 컴포넌트
│   └── skills_designer.md  # Skills.md 설계
├── Skills/                 # 해커톤 제출물 (투자 분석 규칙)
│   ├── analysis.md
│   ├── visualization.md
│   └── insight.md
├── src/
│   ├── app.py              # Streamlit 메인 진입점
│   ├── data/fetcher.py     # yfinance 래퍼
│   ├── analysis/indicators.py  # 기술적 지표 계산
│   └── viz/charts.py       # Plotly 차트 컴포넌트
├── docs/ref/               # 참조 문서
└── logs/                   # gitignore 대상
```
