# Design — Catch Trolls MVP

세부 계약: `docs/api-contract.md`, `docs/internal-interfaces.md`, `docs/session-ownership.md`.

## Architecture
```
React/Vite PWA (frontend/)  --/api-->  FastAPI (backend/app/main.py)
                                         |- api/        라우트 (S3)
                                         |- models/ schemas/ db.py  SQLAlchemy 2 + Pydantic v2, SQLite (S3)
                                         |- collectors/ YouTube 수집, URL 파싱 (S4)
                                         |- analysis/   llm.py 단일 호출 지점, 판독, 이미지 추출 (S4)
                                         |- documents/  PDF bytes 생성, DB 독립 (S2)
                                         |- storage/    업로드 원본 (Git 제외)
```
배포는 루트 `Dockerfile`: React 빌드를 `/app/static`에 복사하고 FastAPI가 `STATIC_DIR`로 서빙한다.

## 세션 경계
| 세션 | 소유 경로 |
|---|---|
| S1 FE | `frontend/**` |
| S2 DOC | `backend/app/documents/**`, `samples/**`, `docs/presentation/**` |
| S3 API | `backend/app/{main,db}.py`, `api/`, `models/`, `schemas/`, `requirements.txt` |
| S4 AI | `backend/app/analysis/**`, `backend/app/collectors/**` |

## 주요 컴포넌트
- **API**: `/api/cases`, `/cases/{id}/inputs/{url|text|image}`, `/cases/{id}/analyze`, `/comments/{id}`, `/cases/{id}/agent/{review|answers}`, `/cases/{id}/documents/{statement|evidence-list}.pdf`.
- **LLM**: `LLM_PROVIDER=gemini|mock`, `google-genai` SDK. `analysis/llm.py`만 모델을 호출한다. 응답은 Pydantic 검증, 실패 시 1회 재시도.
- **수집**: YouTube Data API v3 `commentThreads.list`/`comments.list`, 합산 최대 200. 다른 플랫폼은 크롤링하지 않는다.
- **PDF**: ReportLab 또는 WeasyPrint. 시작 시 한글 폰트(Nanum) 존재를 검사한다.
- **FE**: 페이지는 사건 목록, 사건 상세, 입력(텍스트/이미지/URL 탭), 분석 결과, 문서. `/share-target` 라우트는 URL 탭만 프리필한다. `VITE_USE_MOCK`으로 mock 전환.

## 데이터 모델 (요약)
- Case(id, title, description, created_at)
- Source(id, case_id, type[youtube|text|image|url_only], url, file_sha256, collected_at, needs_manual_input, message)
- Comment(id, source_id, author?, content, posted_at?, comment_url?, platform, like_count?, parent_id?, saved, user_note, user_confirmed)
- Analysis(comment_id, level, issues[], flagged_phrases[], reason, check_points[], disclaimer)
- Answer(case_id, question_id, answer)
시각은 UTC ISO-8601, 프론트에서 KST로 표시한다.

## 오류 처리
`{"error":{"code","message"}}` + 적절한 HTTP status. YouTube 실패는 503과 수동 입력 안내.

## 테스트 전략
최소 테스트: URL 파싱, JSON 검증, SHA-256, 사건 삭제 시 원본 삭제, PDF에 실제 필드 반영. 판독은 `mock` provider로 결정적 테스트.
