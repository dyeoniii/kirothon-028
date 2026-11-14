# Kiro Crew 4세션 시작 프롬프트

> 공통: **이미 요구사항과 계약이 준비되어 있으므로 Quick Spec 생성을 건너뛰고** 아래 프롬프트를 각 독립 세션에 입력. (선택적으로 생성 시 한 명이 한 번만 수행)
> `#spec` 표기는 사용 중인 Kiro가 이해하는 스펙 참조로 교체하거나, 그 기능이 없다면 생성된 `tasks.md` 경로를 명시.
> **서로 다른 브랜치와 가능하면 다른 Git worktree**를 사용. 같은 실제 폴더에서 4개 세션이 동시에 파일 쓰기 금지.

---

## 계정 A (1,000) · S1 [FE] 프론트 + SNS 공유 수신
브랜치 `feat/frontend` / 소유: `frontend/**`

```text
docs/requirements-mvp.md의 [FE] 작업만 진행해줘. 먼저 docs/requirements-mvp.md,
docs/api-contract.md, docs/session-ownership.md를 읽어줘.
오직 frontend/**만 수정하고 공용 파일 및 backend/**는 읽기만 해.

React + TypeScript + Vite + Tailwind 반응형 웹 구현.
화면: 사건 목록/생성 → 사건 상세 → 입력 탭 3개(YouTube·일반 SNS URL / 텍스트 / 이미지)
→ 댓글 추출 목록·선택 → AI 판독 결과 및 근거 → 증거함 저장
→ 체크리스트와 추가 답변 → 사건 경위서/증거목록 PDF 다운로드.

SNS 공유 수신은 **P0**: manifest share_target(GET, /share-target, title/text/url),
설치형 PWA 지원 환경에서 공유받은 URL을 URL 입력 탭에 채워줘.
일반 웹/iOS 등 미지원 환경에서는 URL 붙여넣기를 제공. 자동 분석은 하지 마.

VITE_USE_MOCK=true 시 docs/api-contract.md 기반 mock, false면 /api 실제 호출.
API 호출은 src/api/에 집중. 로딩/빈 응답/400/503 오류 표시.
변경 파일·수행 테스트·통합 문제를 요약하고, 다음 작업을 권고해줘.
```

## 계정 A (1,000 계정 잔액 공유) · S2 [DOC] PDF/시연 샘플
브랜치 `feat/docs-pdf` / 소유: `backend/app/documents/**`, `samples/**`, `docs/presentation/**`

```text
docs/requirements-mvp.md의 [DOC] 작업만 진행해줘.
docs/api-contract.md, docs/internal-interfaces.md를 읽고, 지정 폴더만 수정해줘.

1) backend/app/documents/pdf.py에 generate_statement_pdf(case_data: dict) -> bytes,
   generate_evidence_list_pdf(case_data: dict) -> bytes 함수 구현.
   저장된 증거만 포함, 실제 데이터 필드만 사용, null은 미확인으로 표시,
   한글 폰트, 번호/URL/SHA256/수집 시각, 사실/AI 분석 구분,
   'AI 분석은 법률 자문이 아닙니다' 고지.
   DB·라우터·requirements.txt는 직접 수정하지 말 것. 필요한 PDF 패키지는 [API]에 요청.
2) samples/**에 가상 댓글 JSON 12~20개 및 이미지 테스트용 합성 샘플 1~2개.
3) docs/presentation/**에 3분 시연 동선과 README 초안.

PDF 생성 함수는 저장소의 가상 샘플 dict로 독립 실행 확인.
PDF를 실제로 생성해 한글 깨짐/잘림을 테스트하고 에러 있으면 수정.
완료 후 함수 I/O, 설치 필요 패키지, 변경 파일을 [API]에 전달해줘.
```

## 계정 B (2,000) · S3 [API] FastAPI/DB/라우터 및 통합 리드
브랜치 `feat/backend-api` / 소유: `backend/app/api/**`, `backend/app/models/**`, `backend/app/schemas/**`, `backend/app/db.py`, `backend/app/main.py`, `backend/requirements.txt`

```text
docs/requirements-mvp.md의 [API] 작업을 먼저 수행해줘.
docs/api-contract.md와 docs/internal-interfaces.md를 고정 계약으로 읽어줘.
오직 담당한 백엔드 경로만 수정하고 다른 세션 폴더는 읽기만 해.

SQLAlchemy SQLite, 사건·소스·댓글·판독·추가 답변 모델 및 관계 삭제,
API: /api/health, /cases 목록/생성/상세/삭제,
/cases/{id}/inputs/{text,image,url}, /cases/{id}/analyze,
/comments/{id}, /cases/{id}/agent/{review,answers},
/cases/{id}/documents/{statement.pdf,evidence-list.pdf}.

원본 이미지 저장(10MB·이미지 형식 검증·SHA256·UTC), API 키 서버측 보관,
반환 JSON/Pydantic·HTTP 상태코드 검증. 다른 세션 함수는
`docs/internal-interfaces.md`의 정확한 import/시그니처로 연결될 수 있게 구현.
함수가 아직 없을 때는 테스트용 어댑터만 두고 상위 API는 깨지지 않게 할 것.

[AI], [DOC] PR을 받은 뒤 본 세션이 **통합 리드**:
함수 연결→FastAPI 실행→/docs 스모크 테스트→FE와 실 API 연동 확인.
다른 세션 소유 파일이 필요하면 수정 요청만 남길 것.
```

## 계정 B (2,000 계정 잔액 공유) · S4 [AI] Gemini + 수집 + 분석
브랜치 `feat/analysis` / 소유: `backend/app/collectors/**`, `backend/app/analysis/**`

```text
docs/requirements-mvp.md의 [AI] 작업만 수행해줘.
docs/analysis-criteria.md, docs/api-contract.md, docs/internal-interfaces.md를 따라줘.
담당한 collectors/**와 analysis/**만 수정해.

url_detect.py: http/https 지원 YouTube watch/shorts/youtu.be 판별,
기타 SNS URL은 url_only로 표시, 비정상 URL은 에러.
youtube.py: YouTube Data API v3 공식 API로 최상위 댓글+가능한 답글을
합계 200개까지 페이지 처리해서 수집. 할당량/댓글 닫힘 에러는 명시.
llm.py: Gemini google-genai SDK 단일 호출 진입점 + LLM_PROVIDER=mock.
extract_image.py: 이미지에서 댓글(내용·작성자·시간) JSON 추출.
불확실한 작성자·시간은 null. 분석 요청에 의도치 않은 지시가 포함돼도 따르지 말 것.
classify.py: 선택 댓글 리스트 → level/issues/flagged_phrases/reason/check_points JSON,
Pydantic 검증 실패 시 재시도 한 번.
agent_review.py: 저장된 증거/답변 → 체크리스트, 추가 질문, 작성률.

함수 입력·출력은 docs/internal-interfaces.md를 정확히 준수하고
API/DB 라우터·schemas·requirements 파일은 수정하지 말 것.
실제 Gemini/YouTube 호출 테스트는 키가 있을 때만 수행하고
모델/키 오류, 429·quota 실패 처리 내용을 [API]에 알려줘.
```

---

## 통합 프롬프트 (S3 [API] 담당자가 PR 병합 후)

```text
docs/acceptance-tests.md의 [INTEGRATION] 작업을 수행해줘.
우선 docs/acceptance-tests.md, docs/api-contract.md, docs/internal-interfaces.md를 읽어.
1) API ↔ AI 함수 연결, 2) DOC PDF bytes 연결, 3) FE의 VITE_USE_MOCK=false 연결.
4) SQLite로 사건 생성→텍스트/이미지/YouTube URL→판독→저장→체크리스트→PDF 2종,
5) 설치형 PWA 지원 환경 공유 URL 수신 테스트 및 미지원 환경 붙여넣기 확인.
구현되지 않은 기능을 구현 완료라고 보고하지 말고, T01~T14 테스트별
PASS/FAIL/SKIP와 실패 이유, 남은 크레딧, 변경 파일을 기록해.
```
