---
inclusion: always
---
# 코드 구조 및 세션별 소유권
```
frontend/                      # S1 [FE] (계정 A)
  public/                      # manifest, PWA 아이콘
  src/api/ src/pages/ src/components/ src/types/
backend/
  requirements.txt             # S3 [API] (계정 B)
  app/main.py db.py            # S3 [API]
  app/api/ models/ schemas/    # S3 [API]
  app/collectors/             # S4 [AI] (계정 B)
  app/analysis/               # S4 [AI]
  app/documents/              # S2 [DOC] (계정 A)
  app/storage/                # Git에 업로드 금지
samples/                       # S2 [DOC], 가상 데이터만
docs/presentation/             # S2 [DOC]
docs/ api-contract.md requirements-mvp.md session-ownership.md # 공용, 일방 수정 금지
prompts/ .kiro/steering/       # 공용, 일방 수정 금지
```
- 4세션 유지, **동일 파일 동시 수정 금지**, 각 세션별 브랜치/별도 worktree 권장.
- S1 FE와 S2 DOC는 같은 1,000 크레딧 계정, S3 API와 S4 AI는 같은 2,000 크레딧 계정.
- DOC는 PDF bytes 함수를 제공, API가 라우트에 연결; AI는 수집/추출/판독 함수를 제공, API가 호출.
- 함수/응답 계약은 `docs/internal-interfaces.md`와 `docs/api-contract.md`를 우선한다.
