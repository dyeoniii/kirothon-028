# 악플가드 — 실행 가능한 초기 골격 + Kiro Crew 4세션 작업 패키지

> **이 패키지는 설정/스캐폴드가 준비된 시작점입니다. 핵심 앱 기능은 아직 미구현입니다.**
> 시작 화면과 `/api/health`만 작동하며 AI 판독/증거 관리/유튜브 조회/PDF는 각 Kiro 세션이 구현해야 합니다.

## 1. 누가 무엇을 하나요?
- **A (본인, 크레딧 1,000)**: S1 프론트(`feat/frontend`) + S2 PDF(`feat/docs-pdf`)
- **B (팀원, 크레딧 2,000)**: S3 API·DB(`feat/backend-api`) + S4 AI·URL 수집(`feat/analysis`)
- 크레딧은 **계정별 공유**이며 세션 개수만큼 늘지 않습니다.

## 2. GitHub 공동 저장소에 한 번만 올리기 (A 또는 B)
압축 해제 후 `potato/` 디렉터리를 프로젝트 루트로 사용합니다.
```bash
git init
git add .
git commit -m 'chore: bootstrap akpleguard Kiro Crew starter'
git branch -M main
# GitHub에 빈 private repository를 만든 뒤:
git remote add origin <REPOSITORY_URL>
git push -u origin main
```
**그 외 팀원은 저장소를 clone** 합니다. 저장소에 기존 코드가 있다면 `git init`을 반복하지 마세요.

## 3. 각자 2개 worktree 생성 (터미널, 1회)
두 사람은 **각자 clone한 디렉터리에서** 아래 중 자기 역할 명령어만 실행합니다.
```bash
# A 계정
bash scripts/setup-my-worktrees.sh A "$HOME/projects/potato-worktrees"
# B 계정 (B 컴퓨터 / B의 별도 clone)
bash scripts/setup-my-worktrees.sh B "$HOME/projects/potato-worktrees"
```
`~/projects/potato-worktrees`는 원하는 절대경로로 바꿀 수 있습니다.
생성된 폴더 네 개를 **각 세션에 해당하는 작업 디렉터리**로 열어야 합니다. Kiro Crew에서 세션을 만들 때 worktree를 별도 지정할 수 있다면 그 설정으로 연결하세요. 실제 Crew 버전 UI 명칭은 다를 수 있습니다.

## 4. Kiro Crew 세션 프롬프트
`prompts/02_session_prompts.md`에서 S1/S2/S3/S4 프롬프트를 각각 해당 세션에 복사하여 입력합니다.
- S1 (`potato-s1-fe`)와 S2 (`potato-s2-doc`)는 A가 실행
- S3 (`potato-s3-api`)와 S4 (`potato-s4-ai`)는 B가 실행
- **Quick Spec 생성은 선택**: 본 패키지에 계약과 작업 요구사항이 이미 있으므로 오늘은 별도 스펙 생성 없이 네 프롬프트로 바로 진행 가능합니다. 스펙을 만들기로 했다면 한 명이 한 번만 생성하고 커밋 후 공유하세요.
- 최초 세션 실행 전 Kiro 로그인/Agent Harness 인증을 확인하세요.

## 5. 로컬 실행 확인 (현재 골격)
백엔드:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# http://127.0.0.1:8000/api/health
```
프론트엔드 (새 터미널):
```bash
cd frontend
npm install
npm run dev
# http://127.0.0.1:5173
```
`backend/.env.example`은 실행 디렉터리가 `backend`인 경우 `.env`로 복사합니다. 실제 키는 **B 컴퓨터의 .env에만** 입력합니다. `frontend/.env.local`에는 `VITE_USE_MOCK=false` 등 공개 가능한 설정만 사용합니다. 비밀키 금지.

## 6. 병합 순서 (B 통합 리드)
1. S4(AI)를 S3(API)에 병합하고 실제 Gemini 판독 확인
2. S2(PDF)를 병합해 실제 사건 데이터로 PDF 생성 확인
3. S1(FE)를 병합하고 `/api` 연동 및 PWA를 확인
4. `docs/acceptance-tests.md`로 PASS/FAIL/SKIP 기록
5. 각 세션이 커밋하고 push 후, 사람이 PR을 검토하고 병합합니다. `main` 직접 작업 지양.

## 7. 필수 제약
- Web Share Target은 브라우저 지원 및 **PWA 설치**가 필요합니다. manifest만으로 모든 모바일 앱에 표시되지는 않습니다. S1이 설치 가능 조건(아이콘·서비스 워커·HTTPS 등)을 검증해야 합니다.
- YouTube 자동 댓글 조회 외의 SNS URL은 `url_only`로 저장하며 텍스트/이미지 입력을 안내합니다.
- 인증 없는 **로컬 데모 한정**: 실제 피해자 정보 사용하거나 공개 인터넷에 배포하지 마세요.
- 법적 판단 확정 금지. 분석 근거/원본/사용자 확인 내용을 구분하세요.

## 문서 색인
- `docs/requirements-mvp.md`: P0/P1/제외 범위
- `docs/api-contract.md`: API 계약 (API base `/api`)
- `docs/internal-interfaces.md`: S3↔S4 및 S3↔S2 함수 계약
- `docs/session-ownership.md`: 폴더 및 브랜치 소유
- `docs/acceptance-tests.md`: 시연 검증
- `prompts/02_session_prompts.md`: 세션별 복사용 프롬프트
