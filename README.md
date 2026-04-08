# Claude Code Dev Template

새 프로젝트를 시작할 때 이 레포를 템플릿으로 사용하면 Claude Code 개발 환경이 즉시 구성됩니다.

## 포함 내용

| 파일 | 설명 |
|------|------|
| `CLAUDE.md` | 프로젝트 지침 템플릿 (모델 규칙, 코딩 규칙, 에이전트 규칙) |
| `.gitignore` | Python/Node 범용 |
| `.claude/settings.json` | 프로젝트 레벨 권한 설정 (bypassPermissions) |
| `agents/example-agent.md` | 병렬 에이전트 템플릿 — 복사해서 역할별로 생성 |
| `global-setup/settings.json` | 전역 설정 (context-bar, Stop 알림 훅) |
| `global-setup/scripts/context-bar.sh` | 상태바 — 모델/브랜치/컨텍스트 사용량 표시 |
| `global-setup/scripts/notify.ps1` | Claude 응답 완료 시 Windows 토스트 알림 |

## 설치 방법

### 1단계 — 이 레포를 템플릿으로 새 레포 생성

GitHub에서 **"Use this template"** 버튼 클릭 → 새 레포 생성

또는 gh CLI:
```bash
gh repo create my-project --template <owner>/claude-code-template --private --clone
cd my-project
```

### 2단계 — 전역 설정 설치 (최초 1회만)

```bash
# 스크립트 폴더 생성
mkdir -p ~/.claude/scripts

# 파일 복사
cp global-setup/settings.json ~/.claude/settings.json
cp global-setup/scripts/context-bar.sh ~/.claude/scripts/
cp global-setup/scripts/notify.ps1 ~/.claude/scripts/

# 실행 권한 부여 (Mac/Linux)
chmod +x ~/.claude/scripts/context-bar.sh
```

> **주의:** `~/.claude/settings.json`이 이미 있다면 기존 내용을 백업 후 병합하세요.

### 3단계 — 프로젝트 커스터마이징

1. `CLAUDE.md` 에서 `[프로젝트명]`, `[Language]` 등 플레이스홀더 수정
2. `agents/example-agent.md`를 복사해서 역할별 에이전트 생성 (아래 참고)
3. `docs/ref/todo-workflow.md` 작성 (TODO 워크플로우 규칙)

## 기능 설명

### context-bar (상태바)
Claude Code 하단에 현재 모델 / 폴더 / Git 브랜치 / 컨텍스트 사용량을 표시합니다.

```
claude-sonnet-4-6 | 📁 my-project | 🔀 main (0 files uncommitted, synced 2m ago) | ████░░░░░░ ~12% of 200k tokens
💬 마지막 메시지 내용...
```

색상 변경: `context-bar.sh` 상단의 `COLOR` 값 수정
`orange | blue | teal | green | lavender | rose | gold | slate | cyan`

### PC 토스트 알림 (Windows)
Claude Code 응답 완료 시 Windows 알림 + 효과음("띠링") 발생. 알림 클릭 시 Claude Code 창으로 자동 포커스 이동.

세션이 **3분 이상** 진행된 경우에만 알림을 발생시켜 짧은 작업에서의 노이즈를 방지합니다.

> Mac/Linux 사용자는 `global-setup/settings.json`의 `Stop` 훅 커맨드를 OS에 맞게 수정하세요.

### bypassPermissions 모드
`.claude/settings.json`에 설정된 위험 명령어(rm -rf, force push 등)를 제외한 모든 작업을 자동 승인합니다.

### 에이전트 병렬 처리
`agents/` 폴더에 역할별 에이전트 마크다운 파일을 추가하면, Plan 모드에서 설계 후 독립적인 작업을 병렬로 실행할 수 있습니다.

**에이전트 셋팅 방법:**

```bash
# example-agent.md를 복사해서 역할별로 생성
cp agents/example-agent.md agents/frontend.md
cp agents/example-agent.md agents/backend.md
cp agents/example-agent.md agents/db.md
```

각 파일에서 `name`, `description`, 담당 영역을 프로젝트에 맞게 수정합니다.

`description`은 Claude가 "어떤 작업을 이 에이전트에 맡길지" 판단하는 기준이 되므로 구체적으로 작성하는 것이 중요합니다.

```markdown
---
name: backend
description: API 서버 병렬 서브태스크 에이전트. src/api/ 하위 라우터/컨트롤러/미들웨어 작업을 독립적으로 처리.
model: sonnet
---
```

## 요구사항

- [Claude Code](https://claude.ai/code) 설치
- [jq](https://jqlang.github.io/jq/) 설치 (context-bar 정상 동작에 필요)
- Windows: PowerShell 5.1+
