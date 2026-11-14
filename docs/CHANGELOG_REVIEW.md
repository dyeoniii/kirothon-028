# 원본 `kiro-handoff.zip` 검토 및 수정 내역 (2026-11-14)

## 원본 패키지에서 확인된 사항
- 11개 설정·명세·프롬프트 파일만 존재, 실행 가능한 frontend/backend 코드 없음.
- Kiro Crew 세션 4개([FE]/[DOC]/[API]/[AI])로 분리한 의도는 타당하여 유지.
- **기존 요구사항 충돌**: `tech.md`의 'PWA는 오늘 범위 아님', `01_quick_spec.md`의 'PWA·공유 수신 제외', `README`의 'PWA는 로드맵'을 수정.
- **미정의 인터페이스**: DOC/AI 함수 시그니처 및 사건 상세 JSON 누락 → `internal-interfaces.md`, `api-contract.md` 보완.
- **업무 충돌 우려**: 한 세션의 docs 수정과 다른 세션의 docs 수정, 라이브러리 수정 소유자 미정 → 세션별 파일 소유권·통합 책임 명시.
- **유튜브 답글 수집의 오해**: commentThreads.list만으로 모든 답글 조회 보장 안 됨 → `comments.list`를 통해 추가 조회 가능하도록 정의.
- **불완전한 법률 지침 TODO**: 원본에는 기존 법률 지침 내용이 실제 첨부되지 않음 → 미확인이라고 명기, 기본 위험 신호 규칙 제공.
- **개인정보/증거 보존**: 업로드 제한·사건 삭제·원본/추론 구분 추가.

## 변경된 주요 파일
- 수정: `README_START_HERE.md`, `.kiro/steering/*.md`, `.env.example`, `.gitignore`, `docs/api-contract.md`, `docs/analysis-criteria.md`, `prompts/*.md`
- 추가: `docs/requirements-mvp.md`, `docs/session-ownership.md`, `docs/internal-interfaces.md`, `docs/acceptance-tests.md`, `docs/CHANGELOG_REVIEW.md`

## 설계상의 결정
1. **네 세션 유지**, 계정 A(1,000)의 [FE]+[DOC] 및 계정 B(2,000)의 [API]+[AI].
2. SNS 공유 URL 수신 + 직접 URL 입력은 **둘 다 P0**. PWA 수신 불가 환경은 붙여넣기 기본 제공.
3. PDF 2종 필수, 고소장 참고 초안/변호사 요약서는 P0 제외.
4. YouTube 공식 API만 자동 댓글 수집, 기타 SNS는 URL 저장 및 수동 입력.
5. Gemini 기반 실제 판독 원칙, mock은 개발/장애 대비만.
6. 계정별 크레딧은 별도 공유될 수 없으며, 네 세션 사용량은 각 계정 소진분으로 취급.

## 미확정 사항 (실구현 전 확인)
- 개발에 사용할 실제 Gemini 모델 ID, YouTube API 키/쿼터, 한글 PDF 폰트의 로컬 경로.
- PWA 실제 지원 기기/브라우저 (특히 iOS는 share_target 수신 지원을 가정하지 않음).
- 사용자가 말한 '기존 법률 검토 기준'은 원본 zip에 없어서 가져오지 않음.
