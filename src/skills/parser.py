"""
Skills 마크다운 파일 런타임 파서

Skills/*.md 파일을 읽어 분석 임계치·색상·인사이트 규칙을 딕셔너리로 반환.
규칙(임계치·색상 코드 등)을 변경하려면 코드가 아닌 .md 파일만 수정하면 즉시 반영됩니다.

사용 예:
    from skills.parser import load_analysis_config, load_visualization_config

    cfg = load_analysis_config()
    print(cfg["rsi_overbought"])   # 70
    print(cfg["risk_free_rate"])   # 0.035
"""

import re
from functools import lru_cache
from pathlib import Path

# Skills/ 디렉토리: src/skills/parser.py → src/skills/ → src/ → 프로젝트 루트
_SKILLS_DIR = Path(__file__).parent.parent.parent / "Skills"


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _read(filename: str) -> str:
    """Skills 마크다운 파일 읽기 (없으면 빈 문자열 반환)"""
    path = _SKILLS_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _find_int(text: str, pattern: str, default: int) -> int:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else default


def _find_float(text: str, pattern: str, default: float) -> float:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else default


# ── 공개 API ─────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_analysis_config() -> dict:
    """Skills/analysis.md 에서 수치 임계치 파싱.

    반환 키:
        rsi_period, rsi_overbought, rsi_oversold,
        bb_period, bb_std,
        risk_free_rate, sharpe_good, sharpe_excellent,
        trading_days,
        asset_concentration_threshold, sector_concentration_threshold,
        correlation_threshold,
        min_data_days, cache_hours, outlier_pct_threshold,
        ma_periods
    """
    text = _read("analysis.md")

    # ── RSI
    rsi_overbought = _find_int(text, r'과매수.*?RSI\s*>\s*(\d+)', 70)
    rsi_oversold   = _find_int(text, r'과매도.*?RSI\s*<\s*(\d+)', 30)
    rsi_period     = _find_int(text, r'계산\s*기간.*?(\d+)일', 14)

    # ── 볼린저 밴드
    bb_period = _find_int(  text, r'중심선.*?(\d+)일\s*이동평균', 20)
    bb_std    = _find_float(text, r'상단\s*밴드.*?\+\s*([\d.]+)σ',  2.0)

    # ── 샤프 비율
    rf_raw          = _find_float(text, r'무위험\s*수익률\s*기본값.*?([\d.]+)%', 3.5)
    risk_free_rate  = rf_raw / 100
    sharpe_good      = _find_float(text, r'샤프\s*비율\s*>\s*([\d.]+)\s*:\s*양호', 1.0)
    sharpe_excellent = _find_float(text, r'>\s*([\d.]+)\s*:\s*우수', 2.0)

    # ── 변동성 연환산 거래일수
    trading_days = _find_int(text, r'√\s*(\d+)', 252)

    # ── 포트폴리오 임계치
    asset_thr  = _find_float(text, r'자산\s*집중도.*?단일\s*종목\s*비중\s*>\s*(\d+)%', 30.0)
    sector_thr = _find_float(text, r'섹터\s*집중도.*?단일\s*섹터\s*비중\s*>\s*(\d+)%', 40.0)
    corr_thr   = _find_float(text, r'상관관계\s*>\s*([\d.]+)인\s*자산', 0.8)

    # ── 데이터 품질
    min_data_days        = _find_int(  text, r'최소\s*(\d+)일치\s*데이터', 30)
    cache_hours          = _find_int(  text, r'(\d+)시간\s*캐시', 1)
    outlier_pct_threshold = _find_float(text, r'[±]\s*(\d+)%\s*초과\s*시\s*플래그', 15.0)

    # ── 이동평균 기간 목록
    ma_section = re.search(r'2\.2.*?2\.3', text, re.DOTALL)
    if ma_section:
        ma_nums = re.findall(r'(\d+)일', ma_section.group())
        ma_periods = sorted({int(n) for n in ma_nums if 2 <= int(n) <= 300})
    else:
        ma_periods = [5, 20, 60, 120, 200]

    return {
        "rsi_period": rsi_period,
        "rsi_overbought": rsi_overbought,
        "rsi_oversold": rsi_oversold,
        "bb_period": bb_period,
        "bb_std": bb_std,
        "risk_free_rate": risk_free_rate,
        "sharpe_good": sharpe_good,
        "sharpe_excellent": sharpe_excellent,
        "trading_days": trading_days,
        "asset_concentration_threshold": asset_thr,
        "sector_concentration_threshold": sector_thr,
        "correlation_threshold": corr_thr,
        "min_data_days": min_data_days,
        "cache_hours": cache_hours,
        "outlier_pct_threshold": outlier_pct_threshold,
        "ma_periods": ma_periods,
    }


@lru_cache(maxsize=1)
def load_visualization_config() -> dict:
    """Skills/visualization.md 에서 색상 토큰 및 차트 상수 파싱.

    반환 키:
        token_bg, token_card, token_accent, token_up, token_down, ...
        COLOR_UP, COLOR_DOWN, COLOR_NEUTRAL,
        COLOR_MA  (dict: MA5, MA20, MA60, MA120, MA200 → hex)
        CHART_BGCOLOR, CHART_PAPER_BGCOLOR, CHART_FONT_COLOR, CHART_GRID_COLOR
    """
    text = _read("visualization.md")
    config: dict = {}

    # CSS 토큰 테이블: | `--bg` | `#131722` | ...
    for m in re.finditer(r'`(--[\w-]+)`\s*\|\s*`(#[0-9a-fA-F]{6})`', text):
        token = m.group(1).replace("--", "").replace("-", "_")
        config[f"token_{token}"] = m.group(2)

    # 차트 색상 상수: | `COLOR_UP` | `#26a69a` | ...
    for m in re.finditer(r'`(COLOR_(?!MA)\w+)`\s*\|\s*`(#[0-9a-fA-F]{6})`', text):
        config[m.group(1)] = m.group(2)

    # MA 색상: | `COLOR_MA["MA5"]` | `#FFD700` | ...
    ma_colors: dict[str, str] = {}
    for m in re.finditer(r'`COLOR_MA\["(MA\d+)"\]`\s*\|\s*`(#[0-9a-fA-F]{6})`', text):
        ma_colors[m.group(1)] = m.group(2)
    if ma_colors:
        config["COLOR_MA"] = ma_colors

    # 차트 테마 상수: | `CHART_BGCOLOR` | `#131722` | ...
    for m in re.finditer(r'`(CHART_\w+)`\s*\|\s*`(#[0-9a-fA-F]{6})`', text):
        config[m.group(1)] = m.group(2)

    return config


@lru_cache(maxsize=1)
def load_insight_rules() -> list[dict]:
    """Skills/insight.md 에서 기술적 신호 인사이트 규칙 파싱.

    반환:
        [{"condition_raw": "RSI > 70", "message": "...", "grade": "High"}, ...]
    """
    text = _read("insight.md")
    rules: list[dict] = []

    # 마크다운 테이블 행 파싱: | 조건 | 인사이트 | 등급 |
    pattern = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(High|Medium|Low|Info)\s*\|',
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        condition_raw = m.group(1).strip()
        message       = m.group(2).strip()
        grade         = m.group(3).strip()

        # 헤더·구분선 제외
        if condition_raw in ("조건", "---", "------|") or "---" in condition_raw:
            continue

        rules.append({
            "condition_raw": condition_raw,
            "message": message,
            "grade": grade,
        })

    return rules


def get_config() -> dict:
    """전체 Skills 설정 통합 반환 (analysis + visualization)"""
    return {
        "analysis": load_analysis_config(),
        "viz": load_visualization_config(),
    }


def clear_cache() -> None:
    """파서 캐시 초기화 — Skills 파일 수정 후 즉시 반영이 필요할 때 호출"""
    load_analysis_config.cache_clear()
    load_visualization_config.cache_clear()
    load_insight_rules.cache_clear()
