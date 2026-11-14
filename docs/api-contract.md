# REST API 계약 v2 — 프론트/백 공용 · 합의 후 변경

Base `/api`; 날짜는 ISO-8601 UTC `...Z`, 프론트에서 KST 렌더. JSON에 원문 미확인 필드를 임의로 채우지 말 것. 성공 시 표의 형식을 따르고, 실패는 `{"error":{"code":"VALIDATION_ERROR","message":"설명"}}` + 적절한 HTTP status.

## 공통
| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | `{ "status": "ok" }` |

## 1. 사건(증거함)
| Method | Path | 요청 / 응답 |
|---|---|---|
| POST | `/cases` | `{ "title": "...", "description": "..." }` → `{ "id": "case_1", "title": "...", "description": "...", "created_at": "...Z" }` |
| GET | `/cases` | `[{ "id":"case_1", "title":"...", "created_at":"...Z", "saved_count":2 }]` |
| GET | `/cases/{case_id}` | 사건 상세(아래 예시), 404 처리 |
| DELETE | `/cases/{case_id}` | 삭제 성공 시 204, 연관 소스·원본 파일까지 삭제 |

GET 상세 예시:
```json
{
 "id":"case_1", "title":"SNS 비방 댓글", "description":"시연용 가상 사건", "created_at":"2026-11-14T03:00:00Z",
 "sources":[{"id":"src_1","type":"text","url":null,"file_sha256":null,"collected_at":"2026-11-14T03:01:00Z","needs_manual_input":false,"message":null}],
 "comments":[{"id":"cmt_1","source_id":"src_1","author":null,"content":"그 사람은 사기꾼이다","posted_at":null,"comment_url":null,"platform":"text","like_count":null,"parent_id":null,"saved":true,"user_note":null,"user_confirmed":false,"analysis":{"level":"needs_context","level_label":"추가 맥락 확인 필요","issues":["명예훼손(사실 적시)"],"flagged_phrases":["사기꾼이다"],"reason":"실제 문맥과 사실관계 확인이 필요합니다.","check_points":["발언 대상이 특정되는지 확인"],"disclaimer":"AI 분석은 법률 자문이 아닙니다."}}],
 "answers":[]
}
```

## 2. 입력 → 댓글 추출
| Method | Path | 요청 / 설명 |
|---|---|---|
| POST | `/cases/{case_id}/inputs/url` | JSON `{ "url":"https://www.youtube.com/watch?v=..." }` → 영상 ID 추출, YouTube 공개 댓글 최대 200개. 그 외 URL은 출처만 기록. |
| POST | `/cases/{case_id}/inputs/text` | JSON `{ "text":"...", "source_url":null, "context":null }` → 댓글 단위 추출; 사용자가 확인/수정 가능한 리스트 |
| POST | `/cases/{case_id}/inputs/image` | `multipart/form-data`: `file`(필수), `source_url`(선택), `context`(선택); 파일 형식/10MB 제한 |

공통 응답 (각 입력별 조회 성공, 또는 수동 입력 필요):
```json
{
 "source":{"id":"src_2","type":"youtube","url":"https://www.youtube.com/watch?v=example","file_sha256":null,"collected_at":"2026-11-14T03:05:00Z","needs_manual_input":false,"message":null},
 "comments":[{"id":"cmt_2","source_id":"src_2","author":"예시계정","content":"시연용 가상 댓글","posted_at":null,"comment_url":null,"platform":"youtube","like_count":null,"parent_id":null,"saved":false,"user_note":null,"user_confirmed":false}]
}
```
- source.type: `youtube | text | image | url_only`; 댓글이 0개일 수도 있음.
- YouTube API 실패: `503` 등 적절한 오류 응답 + 수동입력 안내. 외부 URL은 **스크래핑 없이 출처 URL만 저장**해 `type=url_only`, `needs_manual_input=true` 반환.
- img에서 OCR로 찾지 못한 작성자/시각은 `null`, 없는 게시물 URL을 창작하지 말 것.

## 3. 판독 / 증거 저장
| Method | Path | 요청 / 응답 |
|---|---|---|
| POST | `/cases/{case_id}/analyze` | `{ "comment_ids":["cmt_1","cmt_2"] }` → results 배열; 한 번에 최대 20건 권장 |
| PATCH | `/comments/{comment_id}` | `{ "saved":true, "user_note":"...", "user_confirmed":true }` (필드 선택적) → 갱신된 댓글 객체 |

```json
{
 "results":[{"comment_id":"cmt_1","level":"legal_review","level_label":"법적 검토 필요","issues":["모욕"],"flagged_phrases":["문제 표현 원문 일부"],"reason":"문맥을 고려한 설명 2~3문장입니다.","check_points":["대상 특정 여부"],"disclaimer":"AI 분석은 법률 자문이 아닙니다."}]
}
```
- `legal_review | needs_context | low_risk` 중 하나; Gemini가 반환하더라도 서버에서 Pydantic 검증 및 재시도.
- 원본 댓글 content는 판독 후 변경 금지. 사용자 확인은 법적 사실 확정이 아닌 '내용 확인' 표시.

## 4. 증거 보완
| Method | Path | 설명 |
|---|---|---|
| POST | `/cases/{case_id}/agent/review` | 저장된 증거 확인 → checklist/questions (필요하면 템플릿 기반) |
| POST | `/cases/{case_id}/agent/answers` | `{ "answers":[{"question_id":"q1","answer":"가상 피해 경위"}] }` → 아래 리뷰와 같은 형태 |

```json
{"completeness":60,"checklist":[{"item":"원본 게시글 URL","status":"partial","detail":"3건 중 1건 누락"}],"questions":[{"id":"q1","question":"실제 어떤 피해가 있었나요?"}]}
```
- completeness: 누락 없이 기입한 서비스 체크 항목 비율, **소송 성공률/증거 법적 충분성 아님**.

## 5. PDF 문서
| Method | Path | 결과 |
|---|---|---|
| GET | `/cases/{case_id}/documents/statement.pdf` | 사건 경위서 PDF; `application/pdf`, `Content-Disposition: attachment` |
| GET | `/cases/{case_id}/documents/evidence-list.pdf` | 저장된 증거 목록 PDF; 증거 번호/댓글/작성자/시각/URL/수집 시각/SHA-256 |

- 사건 정보나 증거가 없는 경우 사용자에게 이해 가능한 오류 표시. AI 분석과 사용자 확인 사실을 구분하고 법률 고지 필수.

## 6. SNS 공유 수신 (프론트 라우트, API 아님)
- 설치형 PWA의 manifest `share_target: { "action":"/share-target", "method":"GET", "enctype":"application/x-www-form-urlencoded", "params":{"title":"title","text":"text","url":"url"} }`.
- FE `/share-target` 라우트에서 URL을 안전하게 추출하여 **URL 입력 탭만 프리필**. 자동 분석/수집은 사용자의 명시적 클릭 후 진행.
- 개발 서버/브라우저·설치 지원 여부에 따라 동작 제한. 지원되지 않는 경우 복사/붙여넣기 제공.
