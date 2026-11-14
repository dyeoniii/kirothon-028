# 세션 간 함수 계약 (import 충돌 방지)

상세 API 반환은 `docs/api-contract.md`가 최상위 기준. 내부 시그니처는 구현 상황에 따라 팀 합의 가능하지만, **4세션 시작 전에 고정**한다.

## AI 세션 → API 세션
- `backend/app/collectors/url_detect.py` → `detect_platform_and_id(url: str) -> dict` : `platform`, `video_id`(없으면 null), `normalized_url`; 허용 스킴 http/https만.
- `backend/app/collectors/youtube.py` → `fetch_youtube_comments(video_id: str, limit: int = 200) -> list[dict]`: content/author/posted_at/comment_url/parent_id/like_count. 최상위+답글 포함 총량 limit.
- `backend/app/analysis/extract_image.py` → `extract_comments_from_image(image_bytes: bytes, mime_type: str) -> list[dict]` : content 필수, author/posted_at는 불명일 때 null. 실제 원본 증거는 API에서 저장.
- `backend/app/analysis/classify.py` → `analyze_comments(comments: list[dict], context: str | None = None) -> list[dict]`: id 연결 가능한 `comment_id`, level, level_label, issues, flagged_phrases, reason, check_points, disclaimer.
- `backend/app/analysis/agent_review.py` → `review_evidence(evidence: list[dict], answers: list[dict]) -> dict`: completeness, checklist, questions. completeness는 법적 충분성이 아니라 서비스 기입률.
- `backend/app/analysis/llm.py` → Gemini/Mock 선택. 재시도 1회, 모델 JSON/검증 실패 예외를 API에서 명확한 오류 메시지로 매핑.

## DOC 세션 → API 세션
- `backend/app/documents/pdf.py` → `generate_statement_pdf(case_data: dict) -> bytes`, `generate_evidence_list_pdf(case_data: dict) -> bytes`
- `case_data`는 `GET /api/cases/{case_id}`의 JSON형 dict와, 존재하는 경우 사용자 답변 목록. 한글 PDF 생성은 **저장된 실제 필드만** 사용.
- 두 함수는 파일 저장/DB 처리 없이 PDF 바이트만 반환. API 세션이 `application/pdf` + 다운로드 헤더로 응답.

## API / FE 계약
- 서버 쪽 에러 응답 `{ "error": {"code": "...", "message": "..."} }`.
- `GET /api/health`로 정상 실행 확인.
- mock 전환은 FE 환경변수 `VITE_USE_MOCK=true|false`, 백엔드 AI 공급자 모드는 `LLM_PROVIDER=gemini|mock`.
- 브라우저 공유 수신은 FE 라우트 `/share-target`에서 query (`url`, `text`, `title`) 파싱 후 URL 입력 탭으로 넘김. **공유 수신은 서버가 댓글을 수집하는 기능이 아님**.
