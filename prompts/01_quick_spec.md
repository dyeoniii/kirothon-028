# Kiro Quick Spec — 한 번만 생성

이 파일 내용을 Kiro Spec/Quick Spec 기능에 붙여 넣는다. Kiro Crew 대화 세션과 Spec 생성 인터페이스는 설치 버전에 따라 차이가 있으므로 **사용 중인 UI**에서 Spec 생성 위치를 확인한다.

---

`docs/requirements-mvp.md`, `docs/api-contract.md`, `docs/internal-interfaces.md`, `docs/session-ownership.md`, `docs/analysis-criteria.md`, `.kiro/steering/*.md`의 내용을 읽고 하루 해커톤용 **구현 가능한 Quick Spec**을 만들어줘.

## 반드시 지킬 범위
- PC/모바일 반응형 React + FastAPI 악플 판독 및 증거관리 웹앱.
- **입력 4개**: 텍스트, 스크린샷(Gemini 비전), 직접 URL(YouTube 댓글 자동 조회 + 그 외 URL 출처 저장), SNS 공유 URL 수신(설치형 지원 PWA).
- 위 URL 입력과 SNS 공유 수신은 **오늘 P0 필수**. SNS 공유는 앱 설치/브라우저 제약을 반영하고 미지원 대체 경로(복사·붙여넣기)를 제공.
- 사건 생성/목록/상세, 댓글 선택→AI 3단계 판독·근거→증거함 saved→체크리스트/질문과 답변→사건 경위서·증거 목록 PDF 2종.
- YouTube 공식 API만 연동, 댓글+답글 최대 200개 합계, 불가 시 명확한 실패/대체 입력.
- 이미지 해시/수집 시각·파일 검증 및 삭제, 불명 메타데이터는 null. 한글 PDF. 외부 API 키 서버 전용.
- `LLM_PROVIDER=mock`은 개발용/비상용이며 최종 데모에는 실제 Gemini 사용이 기본.
- 사용자 사실과 AI 추정을 구분, 범죄 성립/고소 성공 보장 금지.

## 요구사항 경계
- P0 우선, 고소장 참고 초안/변호사 매칭/다중 SNS 자동 수집/로그인/멀티테넌시/LangGraph/Embedding은 제외.
- 지정되지 않은 관리자 페이지·결제·알림·프로덕션 서비스는 생성하지 말 것.
- API는 `docs/api-contract.md`, 내부 함수는 `docs/internal-interfaces.md`를 따른다. **계약 변경은 코드 생성 전 협의 사항으로 기록.**

## tasks.md를 반드시 다음 그룹으로 나눠줘
- `[FE] S1` `frontend/**` (계정 A, 1,000 계정 잔액 공유)
- `[DOC] S2` `backend/app/documents/**`, `samples/**`, `docs/presentation/**` (계정 A)
- `[API] S3` `backend/app/api/**`, `models/**`, `schemas/**`, `db.py`, `main.py`, `backend/requirements.txt` (계정 B, 2,000 계정 잔액 공유)
- `[AI] S4` `backend/app/collectors/**`, `backend/app/analysis/**` (계정 B)
- `[INTEGRATION]` 계약 검증 → API/AI 병합 → DOC/PDF 병합 → FE/UI 병합 → 실사용 E2E. 통합은 [API] 세션이 조정하되 타 세션의 파일 소유권은 존중.
- 분리된 폴더만 수정하게 하고, 타 그룹 코드가 없을 때는 **계약에 맞는 mock/adapter**로 개발. 한 세션이 남의 폴더를 수정하지 않게.
- 먼저 T01/T02/T09/T11 핵심 흐름, 이후 이미지·YouTube·PWA를 통합해 T01~T14 전체 검사.

스펙 산출물에 각 작업의 완료 기준, 수정 파일, 의존성, 예상 위험, API 연동 지점을 기재해줘. 스펙을 생성한 다음 **바로 전체 코드 생성하지 말고**, 담당자들이 확인할 수 있게 tasks 목록부터 보여줘.
