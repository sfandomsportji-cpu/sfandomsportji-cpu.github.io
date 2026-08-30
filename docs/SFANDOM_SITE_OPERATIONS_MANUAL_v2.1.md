# SFANDOM 사이트 운영·개발 관리자 표준 매뉴얼
## SFANDOM SITE OPERATIONS & CHANGE CONTROL SOP

**문서 버전:** 2.1  
**시행일:** 2026-08-31 KST  
**문서 상태:** 3주년 리뉴얼 전 운영 기준(Source of Truth)  
**적용 대상:** 대표 관리자, 콘텐츠 관리자, 시스템 관리자, 외부 개발자, 자동화 작업, AI 작업  
**최우선 원칙:** 안정성 > 콘텐츠 정확성 > 속도 > 신규 기능

---

# 0. 문서 목적과 사용 방법

이 문서는 SFANDOM을 처음 인수받은 신규 관리자도 별도의 구두 설명 없이 사이트를 안전하게 운영할 수 있도록 만든 실무 SOP다.

관리자는 작업을 시작하기 전에 반드시 다음 순서로 이 문서를 사용한다.

1. 작업이 CORE / CONTENT / MODULE 중 어디에 해당하는지 분류한다.
2. 해당 작업의 허용 권한과 수정 가능 파일을 확인한다.
3. 작업 전 변경 예정 파일을 기록한다.
4. 작업 Branch를 만든다.
5. 본 문서의 실행 절차에 따라 변경한다.
6. PC 1440px / Mobile 390px 검수한다.
7. PR에서 예상하지 않은 변경 파일이 없는지 확인한다.
8. Merge 후 이상 발생 시 Hotfix를 덧붙이기 전에 Rollback을 검토한다.

이 문서에 없는 작업은 원칙적으로 **승인 필요 작업**으로 간주한다.

---

# 1. SFANDOM 운영 구조

SFANDOM은 정적 사이트 기반으로 운영한다. 따라서 서버 애플리케이션처럼 기능을 한 파일에 계속 누적하지 않는다.

## 1.1 CORE

CORE는 사이트의 고정 기반이다.

- Header
- Navigation
- Footer
- 메인 Layout
- 공통 CSS
- 공통 JavaScript
- 기본 반응형 구조
- 브랜드 Logo
- 기본 Font/Color 체계
- URL 구조

**3주년 리뉴얼 전까지 CORE는 원칙적으로 동결한다.**

## 1.2 CONTENT

CONTENT는 일상적으로 교체되는 영역이다.

- DAILY NEWS
- KAIRO FEATURE
- NEXT MATCH
- SFANDOM PICK
- 경기 분석
- 경기 결과
- 기사 링크
- 선수 이미지
- Archive 콘텐츠

## 1.3 MODULE

MODULE은 사이트 본체와 분리하여 관리한다.

- LIVE CHAT
- Visitor Counter
- Analytics
- Cloudflare Worker
- CDN/Traffic Protection
- 향후 외부 API

**MODULE이 장애가 나도 CORE와 CONTENT는 정상 작동해야 한다.**

---

# 2. 관리자 권한

## LEVEL 1 — 콘텐츠 관리자

가능:
- 뉴스/분석/PICK/NEXT MATCH 교체
- 이미지 교체
- 날짜/시간/기록/링크 수정
- Archive 작성

금지:
- 공통 CSS/JS
- Header/Footer/Navigation
- Chat Worker
- Counter Backend
- DNS/Cloudflare/GitHub Pages 설정

## LEVEL 2 — 사이트 관리자

LEVEL 1 포함. 추가 가능:
- 이미지 최적화
- Archive 구조 정리
- 제한적인 반응형 오류 수정
- Broken Link 수정
- Cache Version 변경

공통 CSS/JS, Worker, DNS/CDN 변경은 상위 승인 필요.

## LEVEL 3 — 시스템 관리자

가능:
- GitHub Branch/PR/Release 관리
- Cloudflare/Worker/CDN
- Counter/Chat Backend
- 장애 Rollback

CORE 구조 변경은 대표 관리자 승인 필요.

## LEVEL 4 — 대표 관리자

다음 항목 최종 승인:
- 전체 구조/디자인 변경
- 메뉴/URL 구조 변경
- 회원/결제/개인정보 기능
- 신규 추적 시스템
- 도메인/Hosting 변경
- 대규모 리뉴얼

---

# 3. SFANDOM MASTER RULE

모든 관리자와 자동화 시스템은 다음 10개 규칙을 따른다.

1. 기존 정상 구조를 보존한다.
2. 콘텐츠는 교체한다.
3. 과거 콘텐츠는 Archive로 이동한다.
4. 과거 코드를 화면에 숨겨 보존하지 않는다.
5. 과거 코드는 Git History에서 복원한다.
6. 기능은 MODULE로 분리한다.
7. MODULE 장애가 CORE 장애로 이어지지 않게 한다.
8. MAIN 전체 덮어쓰기를 금지한다.
9. 변경 파일을 최소화한다.
10. 문제가 생기면 수정 전에 Rollback을 검토한다.

---

# 4. RULE 1 — 기존 정상 구조를 보존한다

## 4.1 의미

“보존”은 복사본을 여러 개 만들어 남긴다는 뜻이 아니다.

**현재 정상 작동하는 부분을 수정하지 않는 것**을 뜻한다.

금지 예:
- `index-old.html`
- `backup-index.html`
- `styles-final2.css`
- 정상 Navigation을 콘텐츠 업데이트 때문에 다시 작성
- 뉴스 업데이트하면서 Chat JS까지 함께 수정

버전 보존은 Git이 담당한다.

## 4.2 작업 시작 전 범위 선언

모든 작업은 시작 전에 아래 형식으로 기록한다.

작업명: `2026-08-31 DAILY NEWS 교체`

수정 예정:
- `index.html`
- `assets/morning-20260831/...`
- `archive/...`

수정 금지:
- `styles.css`
- `home.css`
- `live-chat.js`
- `live-dock.js`
- `cloudflare-chat-worker/`

## 4.3 Branch

콘텐츠: `content/YYYYMMDD`  
버그: `fix/문제명`  
모듈: `module/기능명`  
문서: `docs/문서명`

`main` 직접 수정은 긴급 복구 외에는 사용하지 않는다.

## 4.4 작업 종료 시 비교

예상 변경 파일과 실제 변경 파일을 비교한다.

예상에 없던 `live-chat.js`가 변경되었다면 Merge 금지. 이유를 설명할 수 없으면 변경을 제거한다.

## 4.5 PASS 조건

- Header 동일
- Navigation 동일
- Footer 동일
- 공통 CSS/JS 불필요한 변경 없음
- 기존 MODULE 정상
- PC 1440px PASS
- Mobile 390px PASS
- 예상한 파일만 변경

---

# 5. RULE 2 — 콘텐츠는 교체한다

## 5.1 의미

메인 화면의 하나의 콘텐츠 슬롯에는 **현재 콘텐츠 하나만** 존재해야 한다.

잘못된 방법:
- 어제 뉴스 아래 오늘 뉴스 추가
- 어제 뉴스에 `display:none`
- 과거 HTML을 주석으로 남김
- `daily-news-slot2`, `slot-new`, `slot-final` 생성

올바른 방법:
- 기존 콘텐츠 Archive 저장 확인
- 기존 슬롯 내부 내용 제거
- 같은 슬롯 ID 유지
- 새 콘텐츠 삽입

## 5.2 주요 슬롯

- DAILY NEWS: `id="daily-news-slot"`
- KAIRO FEATURE: `id="kairo-feature-slot"`
- NEXT MATCH: `id="next-match-slot"`
- PICK: 현재 PICK 전용 슬롯

페이지 전체를 다시 작성하지 않고 슬롯 내부만 교체한다.

## 5.3 DAILY NEWS 실제 절차

1. `index.html`에서 `daily-news-slot` 검색.
2. `<section>` 시작/끝 확인.
3. 기존 콘텐츠 날짜/본문/이미지/출처 확인.
4. RULE 3 방식으로 Archive 저장.
5. Archive에서 텍스트와 이미지가 정상인지 확인.
6. 현재 슬롯 내부 이전 콘텐츠 제거.
7. 동일 슬롯에 신규 콘텐츠 삽입.
8. 이전 날짜, 제목, 이미지 파일명을 검색.
9. 현재 슬롯에 이전 콘텐츠 잔존이 0인지 확인.
10. PC/Mobile 검수.

## 5.4 이미지 교체

새 콘텐츠 이미지는 날짜 기반 폴더 사용을 권장한다.

예:
`assets/morning-20260831/player-name.webp`

Archive에서 기존 이미지를 참조 중이면 삭제하지 않는다.

## 5.5 PASS 조건

- 기존 콘텐츠 Archive 완료
- 현재 슬롯에는 신규 콘텐츠만 존재
- `display:none` 보존 없음
- HTML 주석 보존 없음
- 중복 Section 없음
- 이미지/링크 정상
- PC/Mobile PASS

---

# 6. RULE 3 — 과거 콘텐츠는 Archive로 이동한다

## 6.1 Archive 목적

Archive는 “숨겨진 백업 코드”가 아니라 사용자가 과거 기록을 다시 볼 수 있는 **콘텐츠 기록 시스템**이다.

## 6.2 Archive 대상

- DAILY NEWS
- KAIRO FEATURE
- PICK
- 경기 분석/결과
- 주요 기사/미디어

Archive 대상이 아닌 것:
- 과거 CSS
- 폐기 JS
- 음악 코드
- 과거 Navigation
- Hotfix
- 이전 Counter/Chat 코드

이런 코드는 Git History에만 남긴다.

## 6.3 저장 위치

메인 일일 스냅샷:
`archive/snapshots/`

PICK:
`archive/picks/`

기사/미디어:
`archive/media/`

## 6.4 파일명

날짜와 종류를 식별할 수 있어야 한다.

좋은 예:
- `2026-08-31-main-fragment.html`
- `2026-08-31-picks.html`
- `2026-08-31-feature.html`

금지:
- `old.html`
- `backup.html`
- `final-old.html`
- `news2.html`

## 6.5 Archive 절차

1. 현재 콘텐츠 확인.
2. 날짜/제목/이미지/링크 확인.
3. 저장 위치 결정.
4. Archive 작성.
5. Archive 페이지 직접 확인.
6. 이미지/링크 확인.
7. 확인 완료 후 현재 슬롯에서 이전 콘텐츠 제거.

**Archive 저장 확인 전에 원본부터 삭제하지 않는다.**

## 6.6 Asset 삭제

Asset 삭제 전 Repository 전체에서 파일명을 검색한다.

Archive 참조가 있으면 삭제 금지.

검색 결과가 0일 때만 삭제 후보로 간주하며, 시스템 관리자 검토 후 삭제한다.

---

# 7. RULE 4 — 과거 코드를 화면에 숨겨 보존하지 않는다

## 7.1 콘텐츠와 코드의 차이

콘텐츠의 과거 기록 → Archive  
코드의 과거 버전 → Git History

## 7.2 금지

HTML:
`<div hidden>...</div>`

CSS:
`.old-feature { display:none; }`

JavaScript:
`// 예전 코드 혹시 필요할까봐 남김`

HTML 주석:
`<!-- old feature -->`

보존을 이유로 이런 코드를 최신 배포본에 남기지 않는다.

## 7.3 기능 삭제 SOP

예: 음악 기능 제거

1. Repository 전체 검색:
   - `audio`
   - `music`
   - `autoplay`
   - `play(`
   - `pause(`
   - 관련 ID/Class/파일명
2. HTML `<audio>`, 버튼, Player UI 제거.
3. JS Audio 객체/Event Listener/상태 저장 제거.
4. CSS Player/Button/Volume 관련 규칙 제거.
5. `<script>`, `<link>`, import, asset URL 참조 제거.
6. Asset 이름 전체 검색.
7. 사용처 0인 Asset만 삭제.
8. 동일 키워드로 재검색.
9. Console Error 확인.
10. Commit.

Commit 예:
`Remove legacy music feature completely`

`old-music.js`, `music-backup.js` 같은 백업 파일을 만들지 않는다.

## 7.4 PASS 조건

- HTML 참조 0
- CSS 관련 코드 0
- JS 관련 코드 0
- Event Listener 0
- Import/Reference 0
- 불필요 Asset 0
- Console Error 0
- 본체 정상

---

# 8. RULE 5 — 과거 코드는 Git History에서 복원한다

## 8.1 목적

현재 사이트를 깨끗하게 유지하면서 과거 코드를 필요할 때 복구할 수 있도록 한다.

## 8.2 복원 전 확인

- 어떤 기능인가
- 마지막 정상 Commit은 무엇인가
- 당시 변경 파일은 무엇인가
- 현재 구조와 충돌하는가
- 전체 롤백인가 부분 복원인가

## 8.3 GitHub 확인 방법

방법 A — 파일 기준:
1. Repository 접속
2. 파일 선택
3. `History`
4. Commit 선택
5. 당시 파일/변경 내용 확인

방법 B — Commit 기준:
1. Commit History 열기
2. 정상 날짜 찾기
3. Commit 열기
4. Changed Files 확인
5. 필요한 코드 확인

## 8.4 전체 파일 덮어쓰기 금지

과거 기능 하나가 필요하다고 과거 `index.html` 전체를 최신 `index.html`에 덮어쓰지 않는다.

그렇게 하면 최신:
- 콘텐츠
- 모바일 수정
- 로고
- LIVE 연결
- Archive 연결
- Counter 연결
등이 사라질 수 있다.

## 8.5 부분 복원 SOP

1. 정상 Commit 찾기.
2. 필요한 HTML/CSS/JS 범위 파악.
3. 현재 코드와 Diff 비교.
4. 별도 Branch 생성.
5. 필요한 부분만 현재 구조에 적용.
6. PC/Mobile 검수.
7. 관련 기능 회귀 테스트.
8. PR 검수.
9. Merge.

## 8.6 전체 Rollback

다음 상황에서만 우선 검토한다.

- Merge 직후 메인 전체 장애
- Navigation 파손
- 대규모 CSS 오류
- JS로 사이트 주요 기능 중단
- 빠른 정상 복구가 최우선인 상황

새 Hotfix를 계속 덧대기보다 직전 정상 Commit으로 복구한다.

---

# 9. RULE 6 — 기능은 MODULE로 분리한다

## 9.1 원칙

CORE 파일에 기능 코드를 흩뿌리지 않는다.

기능은 가능한 한 별도:
- HTML/CSS/JS 파일
- Worker
- API
- Backend 저장소

로 분리한다.

## 9.2 현재 채팅 구조

Frontend: `live.html`  
Style: `live-chat.css`  
Client: `live-chat.js`  
Backend: `cloudflare-chat-worker/`  
Worker Source: `cloudflare-chat-worker/src/index.js`

채팅 문제를 해결하기 위해 메인 사이트 JS를 수정하지 않는다.

## 9.3 Visitor Counter

권장 구조:

Visitor → SFANDOM → Counter API/Worker → Counter Storage

LocalStorage +1이나 새로고침마다 +1 같은 브라우저 기반 “글로벌 카운터”를 사용하지 않는다.

Counter 장애 시 사이트 로딩이 중단되어서는 안 된다.

---

# 10. RULE 7 — MODULE 장애가 CORE 장애로 이어지지 않게 한다

## Fail-Safe

Chat 장애 → Chat만 OFF  
Counter 장애 → Counter만 숨김/마지막 정상값  
Analytics 장애 → Tracking만 실패  
사이트 본체 → 정상

외부 API 응답을 기다리느라 메인 렌더링이 무한 대기하지 않게 한다.

---

# 11. RULE 8 — MAIN 전체 덮어쓰기 금지

작업자가 과거 파일, 로컬 파일, AI 생성 전체 파일을 `main` 최신 파일 위에 그대로 덮어쓰는 것을 금지한다.

반드시 최신 `main`을 기준으로 필요한 영역만 수정한다.

전체 파일 교체가 필요한 경우:
- 변경 사유
- 비교 Diff
- 손실 위험
- Rollback Commit
을 사전 기록하고 승인받는다.

---

# 12. RULE 9 — 변경 파일 최소화

“뉴스 1건 수정”이라면 뉴스에 필요한 파일만 바뀌어야 한다.

불필요한 Formatter, 자동 정렬, CSS 전체 재저장으로 수백 줄 Diff를 만들지 않는다.

PR 검수자는 “이 파일이 왜 바뀌었는가?”에 모든 파일마다 답할 수 있어야 한다.

---

# 13. RULE 10 — 수정 전에 Rollback을 검토한다

장애 발생 시:

1. 장애 발생 시각 기록.
2. 직전 Merge/Commit 확인.
3. 변경 파일 확인.
4. MODULE/CONTENT/CORE 장애 분류.
5. 직전 정상 상태 확인.
6. 빠른 복구가 필요하면 Rollback.
7. 새 Branch에서 원인 분석.
8. 최소 수정 후 재배포.

금지:
- `fix1`, `fix2`, `fix3`
- `override.css`
- `emergency.js`
- 원인 미확인 상태에서 반복 배포

---

# 14. 음악 기능 정책

SFANDOM은 음악 기능을 사용하지 않는다.

다음 항목은 현재 배포본에서 유지하지 않는다.

- autoplay audio
- background music
- audio player
- hidden `<audio>`
- music button
- audio-related JS/CSS
- 음악 상태 저장 코드
- 음악 전용 Asset

삭제된 음악 코드가 필요하면 Git History에서만 확인한다.

---

# 15. LIVE CHAT 운영

현재 LIVE는 Guest 기반 공개 채팅 구조이며 별도 Worker Backend를 사용한다.

운영 원칙:
- Chat 기능을 메인 JS에 통합하지 않는다.
- Worker 장애는 Chat만 차단한다.
- 관리자 인증/신고/차단 등 고급 기능은 공개 확장 전 별도 설계한다.
- Secret/Token을 Repository 코드에 직접 기록하지 않는다.

---

# 16. Visitor Counter 운영

## 16.1 데이터 정의

PAGE VIEW: 페이지가 열린 횟수  
VISITOR: 방문 단위  
UNIQUE VISITOR: 일정 기간 중복 제거 방문자  
SESSION: 하나의 방문 흐름

## 16.2 기준값

58,777은 공개 표시 목적의 기준값을 사용할 경우 실제 추적 데이터와 내부적으로 분리한다.

내부 필드 개념:
- `DISPLAY_BASELINE = 58777`
- `ACTUAL_TRACKED = 실제 측정값`

검증되지 않은 기준값을 분석 화면에서 “실제 과거 Unique Visitor”로 혼동하지 않는다.

## 16.3 Fail-Safe

API 실패 시:
- `NaN`, `undefined`, 잘못된 `0` 표시 금지
- 카운터 숨김 또는 마지막 정상값
- 사이트 로딩은 정상 지속

---

# 17. 트래픽 관리

목표 구조:

User → CDN/Edge → GitHub Pages

대형 SNS 유입 시 HTML보다 이미지/영상 Bandwidth를 우선 점검한다.

확인 우선순위:
1. Bandwidth
2. Cache HIT
3. 대형 이미지
4. 영상
5. Worker 요청
6. HTTP 오류율

홍보 직전에 디자인/구조를 대규모 변경하지 않는다.

---

# 18. 이미지/영상 관리

이미지:
- WebP/AVIF 우선
- 일반 콘텐츠 100~400KB 목표
- Hero 500KB 이하 목표(화질이 심하게 손상되면 예외)

파일명:
`player-team-date.webp`

금지:
`image1.jpg`, `final.jpg`, `new2.png`

영상:
대용량 파일이 누적되면 GitHub Pages 직접 제공 대신 별도 CDN/Media Hosting 검토.

---

# 19. 배포 SOP

1. `main` 최신 확인.
2. Branch 생성.
3. 변경 예정 파일 기록.
4. 작업.
5. Archive/Asset 확인.
6. 변경 파일 목록 검토.
7. PC 1440px 검수.
8. Mobile 390px 검수.
9. Broken Image/Link 확인.
10. PR 생성.
11. 예상 외 파일 변경 확인.
12. 승인 후 Merge.

---

# 20. 배포 체크리스트

- KST 날짜/시간 확인
- 팀/선수/선발 확인
- 기록/스코어 확인
- 이미지 신원/경로 확인
- 링크 확인
- 이전 콘텐츠 Archive 확인
- 현재 슬롯 중복 없음
- 숨김 코드 없음
- 예상 외 CSS/JS 변경 없음
- PC 1440 PASS
- Mobile 390 PASS
- Rollback 가능한 Commit 확인

하나라도 실패하면 배포 보류.

---

# 21. 장애 등급

SEV-1: 사이트 전체 접속 불가  
SEV-2: 메인 주요 기능 장애  
SEV-3: Chat/Counter 등 MODULE 장애  
SEV-4: 오타/단일 링크/UI 경미 오류

SEV-1/2는 복구 우선, 원인 분석은 서비스 정상화 후 별도 Branch에서 수행한다.

---

# 22. 운영 주기

## DAILY
- 메인 정상
- 이미지/PICK/날짜 정상
- LIVE 접근
- Counter
- 404/Broken Link

## WEEKLY
- 대용량 Asset
- 불필요 파일
- Console Error
- Worker/Counter 상태
- CDN Cache

## MONTHLY
- Repository 크기
- Traffic/Bandwidth
- 영상 누적
- Archive 구조
- 보안/권한 점검

---

# 23. 3주년 리뉴얼 전 FREEZE

허용:
- CONTENT 업데이트
- Archive
- Visitor Counter
- LIVE 유지
- CDN/Traffic Protection
- Analytics
- 보안
- 장애 수정

원칙적 금지:
- 전체 디자인 변경
- 메뉴 구조 변경
- 신규 애니메이션
- 음악
- 불필요한 플러그인
- 대규모 CSS/JS 변경
- 사이트 구조 개편

---

# 24. 이번 대화에서 확정한 운영 결정 기록 — 2026-08-31

1. SFANDOM 정적 본체는 가능한 한 변경하지 않는다.
2. 음악 관련 현재 코드는 완전 제거 대상으로 관리한다. 숨김 보존하지 않는다.
3. LIVE CHAT은 본체와 독립 MODULE로 유지한다.
4. Visitor Counter는 별도 MODULE/Backend로 관리한다.
5. Visitor Counter를 브라우저 LocalStorage 기반 글로벌 카운터로 구현하지 않는다.
6. SNS 홍보로 유입이 증가하면 CDN/Edge 구조로 Origin 부담을 줄인다.
7. 3주년 리뉴얼 전까지 신규 구조 개발은 최소화하고 CONTENT 중심 운영으로 전환한다.
8. 과거 콘텐츠는 Archive에, 과거 코드는 Git History에 보존한다.
9. 관리자 매뉴얼은 신입 관리자가 구두 설명 없이 바로 적용할 수 있도록 “무엇을”뿐 아니라 “어떻게”를 명시한다.
10. 모든 수정은 최소 파일 변경, Branch/PR 검수, PC/Mobile 확인, Rollback 가능 상태를 원칙으로 한다.

---

# 25. 신입 관리자 핵심 암기 문장

**정상 코드는 건드리지 않는다.**  
**현재 화면에는 현재 콘텐츠만 둔다.**  
**과거 콘텐츠는 Archive에 둔다.**  
**과거 코드는 Git History에 둔다.**  
**기능은 MODULE로 분리한다.**  
**문제가 생기면 Hotfix보다 Rollback을 먼저 검토한다.**

---

# 26. 문서 관리

이 문서는 SFANDOM 운영의 Source of Truth다.

개정 규칙:
- 기존 내용을 임의로 덮어쓰지 않는다.
- 중요한 정책 변경은 Version을 올린다.
- 변경 사유와 날짜를 기록한다.

Version 예:
- v2.1
- v2.2
- v2.3

3주년 리뉴얼 시:
**SFANDOM OPERATIONS MANUAL v3.0**으로 개정한다.
