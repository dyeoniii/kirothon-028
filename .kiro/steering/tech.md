---
inclusion: always
---
# 기술 스택 및 제한
- **FE**: React + TypeScript + Vite + Tailwind, 모바일 우선, Vite `/api` 프록시, `VITE_USE_MOCK` 토글.
- **PWA 공유수신**: manifest `share_target` + `/share-target` 라우트. 지원되는 **설치형** PWA에서 GET URL/text/title 전달받아 URL 탭 프리필. HTTPS/브라우저 조건 확인. 미지원 환경은 붙여넣기.
- **BE**: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, SQLite + DATABASE_URL.
- **PDF**: ReportLab 또는 WeasyPrint 중 쉬운 것; 배포/실행 시 한글 폰트 존재 여부 검사. PDF 함수는 DB 독립적.
- **URL**: YouTube Data API v3 공식 API, 댓글과 답글 합산 최대 200. 유튜브 외 플랫폼 크롤링 금지.
- **AI**: `google-genai` SDK의 사용 가능한 Gemini 멀티모달 모델, `LLM_PROVIDER=gemini|mock` (Bedrock은 P1). model 미지정 시 지원되는 설정값 선택/문서화. `backend/app/analysis/llm.py` 단일 호출 지점.
- **이미지**: Gemini 비전으로 댓글 추출, 없거나 불확실한 메타데이터는 null.
- **안전**: JSON/Pydantic 검증, 실패 시 한 번만 재시도, 원본 SHA-256/UTC 저장, 10MB 이미지 제한, 민감정보 최소 전송.
- 실행: `cd backend && uvicorn app.main:app --reload --port 8000` / `cd frontend && npm run dev`.
- 세션/함수 경계: `docs/session-ownership.md`, `docs/internal-interfaces.md`, `docs/api-contract.md`.
