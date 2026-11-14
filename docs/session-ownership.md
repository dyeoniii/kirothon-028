# 2명 × 4세션 병렬 개발 운영 규칙

## 담당 구조
| 계정 | 보유 크레딧 | 세션 / 작업 | 브랜치 | **수정 가능 파일** |
|---|---:|---|---|---|
| A | 1,000 | S1 [FE] UI·PWA·API 호출 | `feat/frontend` | `frontend/**` |
| A | 1,000(같은 계정 잔액 공유) | S2 [DOC] PDF·샘플 | `feat/docs-pdf` | `backend/app/documents/**`, `samples/**`, `docs/presentation/**` |
| B | 2,000 | S3 [API] 서버·DB·연동 | `feat/backend-api` | `backend/app/api/**`, `backend/app/models/**`, `backend/app/schemas/**`, `backend/app/db.py`, `backend/app/main.py`, `backend/requirements.txt` |
| B | 2,000(같은 계정 잔액 공유) | S4 [AI] 수집·분석 | `feat/analysis` | `backend/app/collectors/**`, `backend/app/analysis/**` |

- 실제 사람 이름과 계정 소유자를 매핑하지 않았음: A=1,000크레딧 담당자, B=2,000크레딧 담당자.
- A의 두 세션은 **합산 1,000**을, B의 두 세션은 **합산 2,000**을 공유한다. 각 세션에 별도의 1,000/2,000이 생기는 것이 아님.
- 가능하면 한 세션마다 별도 git worktree/작업 폴더를 사용한다. **같은 작업 폴더에서 동시에 같은 Git 브랜치/파일 수정 금지**.
- 각 세션이 공통 계약/steering 파일을 자의로 고치지 않는다. 변경은 팀 합의 후 공용 담당 1명이 별도 PR로 수정.

## 인터페이스 주의사항
- [DOC] PDF 모듈은 받은 `dict`/Pydantic 객체를 **읽기만** 하며 DB 쿼리나 API 라우터를 수정하지 않는다.
- [AI]는 비동기 여부·시그니처를 `docs/internal-interfaces.md`에 맞춘다. 다른 세션의 모델 파일을 직접 수정하지 않는다.
- [API]는 `docs/api-contract.md` 스키마를 구현하고 라우터와 DB에서 [DOC]/[AI] 함수 호출을 연결한다.
- [FE]는 미리 정한 API 응답의 mock으로 화면을 만들고 통합 시 실제 API로 전환한다.
- 파일명만 같은 가짜 stub을 새로 여러 군데 만들지 말고 `docs/internal-interfaces.md`의 함수명과 import 경로를 고정한다.

## 병렬→통합 운영
1. 공통 스펙/타입을 먼저 고정: API 계약, 내부 함수 I/O, 오류 규격.
2. 4세션 병렬: 네 그룹별 파일만 수정. 각자 **빌드/단위 테스트 통과** 후 PR.
3. [API]와 [AI] 먼저 통합 → 서버 실행과 실제 판독 확인.
4. [DOC] 병합 → 저장 데이터로 PDF 생성 확인.
5. [FE] 병합 → 프론트 Mock 해제 후 End-to-end 테스트.
6. **충돌 또는 API 변경은 통합 담당 [API]가 조정**하되 프론트 소유 파일은 FE 세션에 수정 요청.
7. 매 세션 작업 종료 시: 변경 파일 목록/구현 여부/검증 결과/남은 문제/크레딧 사용량 요약.

## 신속한 크레딧 관리 (강제 한도가 아닌 운영 예산)
| 계정 | 핵심 구현 | 연결·버그 | 남겨둘 예비 | 총합 |
|---|---:|---:|---:|---:|
| A: FE+DOC | 700 | 200 | 100 | 1,000 |
| B: API+AI | 1,450 | 350 | 200 | 2,000 |

수치는 **소모량 예측이 아닌 내부 사용 상한**. 세션 수 자체로 크레딧이 증가하지 않으며, 호출 모델/태스크 복잡도에 따라 달라짐.
