# Tasks — Catch Trolls MVP

순서: P0 구현 → 실제 end-to-end 시연 → P1. 각 세션은 자기 폴더만 수정한다.

## S3 API
- [ ] 1. `db.py`와 SQLAlchemy 모델(Case, Source, Comment, Analysis, Answer) 작성 (R-01, R-07)
- [ ] 2. 사건 CRUD 라우트, 삭제 시 원본 파일까지 제거 (R-01)
- [ ] 3. 입력 라우트 `inputs/text|image|url`, 이미지 형식·10MB 검증, SHA-256과 UTC 저장 (R-02, R-03, R-04)
- [ ] 4. `analyze`, `PATCH /comments/{id}`, `agent/review|answers` 라우트 (R-06, R-07, R-08)
- [ ] 5. PDF 라우트 연결 (R-09)
- [ ] 6. 공통 오류 형식과 최소 테스트 (R-10)

## S4 AI
- [ ] 7. YouTube URL 파서와 댓글 수집(합산 200), 실패 시 수동 입력 안내 (R-04)
- [ ] 8. `analysis/llm.py` Gemini/mock provider, Pydantic 검증과 1회 재시도 (R-06)
- [ ] 9. 댓글 판독 프롬프트(인젝션 방어, 법률 자문 아님) (R-06)
- [ ] 10. 이미지 댓글 추출, 불확실한 필드는 null (R-03)

## S2 DOC
- [ ] 11. 사건 경위서 PDF bytes 함수, 한글 폰트 검사 (R-09)
- [ ] 12. 증거 목록 PDF bytes 함수 (R-09)
- [ ] 13. 가상 샘플 데이터 `samples/`와 발표 자료 `docs/presentation/`

## S1 FE
- [ ] 14. 라우팅과 사건 목록·상세 페이지, `api/` 클라이언트, `VITE_USE_MOCK` (R-01)
- [ ] 15. 입력 화면(텍스트/이미지/URL 탭), 추출 댓글 검토 (R-02, R-03, R-04)
- [ ] 16. `/share-target` 라우트와 manifest `share_target`, PWA 아이콘 (R-05)
- [ ] 17. 분석 결과, 증거 저장, 체크리스트·답변 UI, PDF 다운로드 (R-06, R-07, R-08, R-09)
- [ ] 18. 모든 분석 화면에 "AI 분석은 법률 자문이 아닙니다" 고지 (R-06)

## 통합
- [ ] 19. `docs/acceptance-tests.md` 시나리오 6개를 실제로 시연
- [ ] 20. Docker 빌드 확인 후 Render 배포
