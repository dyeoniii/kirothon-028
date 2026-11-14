---
inclusion: fileMatch
fileMatchPattern: "{Dockerfile,backend/app/main.py,frontend/vite.config.ts,backend/requirements.txt}"
---
# 배포 가이드 (Docker / Render)
- 루트 `Dockerfile` 하나로 배포한다. 1단계는 Node에서 `VITE_USE_MOCK=false`로 React를 빌드하고, 2단계는 Python 3.13 이미지에서 FastAPI를 실행한다.
- 프론트 빌드 결과는 `/app/static`에 복사된다. `backend/app/main.py`는 `STATIC_DIR` 환경변수로 이 폴더를 서빙하고, `/api/*` 외 경로는 `index.html`로 보낸다. `/api` 라우트보다 뒤에 등록해야 한다.
- 컨테이너는 `PORT`(기본 10000)에서 `uvicorn app.main:app`을 실행한다.
- 한글 PDF를 위해 이미지에 `fonts-nanum`을 설치한다. 폰트를 바꾸면 PDF 모듈의 폰트 검사도 맞춘다.
- 데이터는 `/data`(`DATABASE_URL`, `STORAGE_DIR`)에 둔다. Render 무료 플랜은 디스크가 휘발성이므로 시연용으로만 쓴다.
- 비밀값(`GEMINI_API_KEY`, `YOUTUBE_API_KEY`)은 Render Environment에만 등록하고 코드, 이미지, 저장소에 넣지 않는다.
- `main` 배포 전 `cd backend && python -m pytest -q`와 `cd frontend && npx tsc --noEmit && npm run build`를 실행한다.
