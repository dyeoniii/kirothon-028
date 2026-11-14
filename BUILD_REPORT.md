# BUILD REPORT — Catch Trolls

**프로젝트:** Catch Trolls
**Demo:** https://potato-kq1a.onrender.com/  
**개발 방식:** 2인 협업 + Kiro Crew의 기능별 세션 분리, Git 브랜치 기반 통합

이 문서는 Kiro가 개발 과정에 어떻게 사용됐는지 기록합니다. 아래 파일 경로는 작업 중 확인한 프로젝트 구조를 기준으로 하며, 최종 제출 저장소의 `.kiro/` 및 코드와 일치하는지 검토해야 합니다.

## Kiro 활용 내역

| 단계 | 사용한 Kiro 기능 | 무엇을 했는지 | 결과물 위치 |
|---|---|---|---|
| 기획 | Kiro 대화형 요구사항 구체화·지침 문서 | SNS 악성 댓글 수집 → AI 판독 → 증거 보완 → PDF 정리라는 MVP 범위를 정하고 기능별 책임과 검증 기준을 정리 | `docs/requirements-mvp.md`, `docs/acceptance-tests.md`, `AGENTS.md` |
| 설계 | 프로젝트 컨텍스트·Steering 성격의 지침, API 계약 정리 | React/FastAPI 분리, 데이터 흐름, 주요 API 및 AI·문서 모듈 사이 인터페이스 정의 | `docs/api-contract.md`, `docs/internal-interfaces.md`, `.kiro/`(실제 생성물 확인) |
| 구현 — 프론트엔드 | Kiro Crew S1, 코드 생성·리팩토링 | 대시보드, 사건 생성·상세, 입력·댓글·보완·문서 탭, 반응형 UI 및 API 클라이언트 구현. 레퍼런스 기반 Modern Legal Tech 레이아웃과 딥 플럼 디자인으로 개선 | `frontend/src/App.tsx`, `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/api/client.ts` |
| 구현 — 문서 | Kiro Crew S2 | 사건 데이터에서 사건 경위서와 증거자료 목록을 PDF로 출력하는 모듈 구성 | `backend/app/documents/` |
| 구현 — API | Kiro Crew S3 | SQLite 기반 사건·댓글 데이터 모델, CRUD·입력·분석·보완·문서 API 구성 | `backend/app/`, `backend/tests/` |
| 구현 — AI | Kiro Crew S4 | URL 유형 판별, YouTube 댓글 수집 연결, 이미지 추출, LLM 기반 분류·검토 및 보완 항목 처리 | `backend/app/collectors/`, `backend/app/analysis/` |
| 검증 | Kiro의 코드 수정 및 로컬 명령 기반 확인 | 프론트엔드 빌드, Python 테스트, API 응답·오류 처리 점검. 실제 브라우저 렌더링 오류를 반복 확인하고 수정 | `frontend/`, `backend/tests/`, 배포 환경 로그 |
| 배포 | Kiro 활용 배포 준비, Docker 기반 구성 | React 빌드 산출물과 FastAPI를 단일 Render Web Service에서 제공하는 배포 구조로 정리 | 루트 `Dockerfile`, Render 설정, https://potato-kq1a.onrender.com/ |
| 협업·기타 | Kiro Crew 세션 분리, Git worktree·브랜치 운영 | S1 `feat/frontend`, S2 `feat/docs-pdf`, S3 `feat/backend-api`, S4 `feat/analysis`로 병렬 진행하고 `integrate/mvp`에서 통합 후 `main` 배포 | `docs/session-ownership.md`, Git 커밋 기록 |

> **심사 제출 전 확인:** `.kiro/`의 실제 Spec·Steering·Hooks 파일을 열어 존재하는 항목만 표에 추가하고, 활용하지 않은 Kiro 기능을 사용했다고 기재하지 마세요. 현재 이 문서에서는 미확인 Spec/Hooks/MCP 사용을 단정하지 않았습니다.

## 개발 과정에서 바뀐 점

### 1. 분석 결과 표시에서 ‘증거 준비의 흐름’으로 확장

초기 아이디어를 단순한 악성 댓글 판독 화면으로 끝내지 않고, **사건 생성 → 댓글 가져오기 → AI 근거 확인 → 증거 보완 → PDF 생성**으로 연결했습니다. AI가 판단을 확정하기보다 상담 준비에 필요한 정리와 누락 확인을 보조하도록 역할을 명확히 했습니다.

### 2. 입력 경험의 우선순위 변경

댓글 입력 방식은 텍스트·스크린샷·SNS URL 순서에서, 사용자의 시작점을 고려한 **SNS URL → 텍스트 → 스크린샷** 순서로 조정하도록 설계했습니다. 입력 화면을 다시 방문할 때 SNS URL을 먼저 보여주는 사용자 흐름도 요구사항으로 반영했습니다. 해당 동작이 최종 코드에 반영됐는지는 출시 전 확인이 필요합니다.

### 3. 감성적 카드 UI에서 정보 중심 Legal Tech 레이아웃으로 개편

단순 연보라 배경·흰색 카드 중심의 디자인을 시도했지만, 텍스트와 버튼의 색상 대비 문제 및 과도한 카드 여백이 발견됐습니다. 이후 **사이드바·상단 툴바·KPI·표형 사건 목록·요약 패널**을 갖춘 문서 관리형 SaaS 구조를 목표로 재설계하고, 파란색 대신 딥 퍼플/플럼을 포인트 컬러로 선택했습니다.

### 4. 로컬 개발에서 통합 배포 방식으로 전환

초기에는 프론트엔드 단독 배포를 시도했지만, 실제 사건 API와 AI 분석을 이용하려면 백엔드까지 필요하다는 점을 확인했습니다. Netlify 배포 과정의 설정 문제를 겪은 뒤, **React 정적 파일 + FastAPI를 Docker 이미지 하나로 제공하는 Render 배포**로 방향을 조정했습니다.

## 어려웠던 점과 해결 방법

| 문제 | 원인·진단 과정 | 대응 및 배운 점 |
|---|---|---|
| 화면의 버튼·글자가 보이지 않음 | CTA와 입력 폼, 사이드바에서 배경과 글자 대비 또는 공통 CSS 적용 문제 발견 | 개별 색상 변경에 그치지 않고 공통 컴포넌트, 디자인 토큰, 레이아웃을 함께 점검하도록 Kiro 작업 지시를 구체화 |
| API가 JSON 대신 HTML을 반환함 | 백엔드 `/api/health`, Vite 프록시의 `/api/health`, `/api/cases`를 각각 호출해 서버와 프록시 정상 여부 확인 | `frontend/src/api/client.ts`의 요청 기본 경로와 콘텐츠 타입 검사 등을 확인하고, 서버 실행·프록시·실제 브라우저 요청을 분리하여 진단 |
| 로컬 8000 포트 충돌 및 개발 서버 재시작 | 기존 Python 프로세스가 8000번 포트를 점유하고 `--reload`가 `venv/` 변경까지 감시 | `lsof`, `ps`, `curl`로 실제 서버를 확인하고 `--reload-dir backend`로 감시 범위를 제한 |
| 통합 브랜치 병합·Push 충돌 | 여러 기능 브랜치와 팀원 작업이 병렬로 진행되어 로컬·원격 이력이 분기 | `git status`, `git fetch`, `git log --left-right`, `git merge`로 변경 이력을 확인한 뒤 안전하게 병합; 강제 Push를 피함 |
| 프론트만 배포하면 실제 기능을 사용할 수 없음 | Vite 로컬 프록시는 배포 환경에 자동으로 제공되지 않음 | Docker 멀티스테이지 빌드 기반 단일 Render 서비스로 전환하여 같은 도메인 아래 React와 FastAPI를 배치 |
| SQLite의 영구성 한계 | 무료 컨테이너 로컬 파일은 재시작·재배포 시 데이터 유실 위험 | 시연용과 실제 운영 환경을 구분하고 PostgreSQL·영구 파일 저장소 전환을 후속 과제로 정리 |

## Kiro 협업 방식 및 결과

- **역할 단위 분리:** UI, PDF, API, AI를 각각 다른 세션과 브랜치에 맡겨 수정 범위 충돌을 줄였습니다.
- **문서 기준 작업:** 요구사항과 API 계약을 공통 기준으로 사용해 기능 간 연동을 추진했습니다.
- **피드백 기반 반복:** 브라우저 스크린샷과 실제 오류 메시지를 바탕으로 Kiro의 수정 지시를 구체화했습니다.
- **통합 후 재검증:** 세션별 완료 보고와 별개로, 통합 브랜치의 API·브라우저 동작을 다시 확인했습니다.

### 제출 전 추가할 검증 근거

- [ ] 실제 `npm run build` 최신 성공 로그와 날짜
- [ ] 최신 `python -m pytest backend/tests -q` 결과(통과/실패 건수)
- [ ] Render `/api/health` 및 핵심 사용자 시나리오의 최종 확인 결과
- [ ] `.kiro/` 내부 실제 파일 경로와 Kiro 기능 사용 내역 일치 여부
- [ ] 최종 디자인 스크린샷 또는 시연 링크

> 수상·성능 향상률·절약 시간·테스트 건수처럼 근거가 필요한 정량 수치는 확인 전에는 작성하지 않았습니다.
