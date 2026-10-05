# SFANDOM — sfandom.com

"Play First. Analysis Next." 스팬덤 공식 사이트. GitHub Pages에서 그대로 서비스되는 정적 사이트이며, 모든 페이지는 `src/build.py`가 만듭니다.

## 구조

| 경로 | 내용 |
|---|---|
| `/` | 홈 — NBA 개막 주간 · 뉴스 · 팬 존 · MLB 포스트시즌 · 분석 · 매거진 |
| `/nba/` | NBA 허브 (개막 주간 일정 · 뉴스 · 분석 · 매거진 · 주요 날짜) |
| `/mlb/` | MLB 허브 |
| `/special/postseason-2026/` | MLB 포스트시즌 (디비전시리즈 · 와일드카드 결과 · 시드) |
| `/news/` · `/news/YYYY/MM/{slug}/` | 뉴스 목록 · 상세 |
| `/news/morning/` · `/news/morning/{날짜}/` | 모닝 에디션 |
| `/analysis/` · `/analysis/{리그}/{날짜}-{slug}/` · `/analysis/review/` | 분석 · 복기 리포트 |
| `/magazine/` · `/magazine/{slug}/` | 매거진 (블로그 연동 + 기획 글) |
| `/community/` | FAN BOARD (Supabase `posts` 테이블 + `community-post` 함수) |
| `/sitemap/` | 전체 페이지 사이트맵 |
| `/about/` `/contact/` `/privacy/` `/ads-cookies/` `/terms/` `/rules/` `/legal/` | 안내 페이지 |

## 빌드

```
python3 src/build.py
```

Python 3.11 이상, 외부 패키지 없음. 결과 HTML은 저장소 루트에 생성됩니다.

## 콘텐츠

| 파일 | 내용 |
|---|---|
| `src/site.json` | 사이트 설정 (첫 화면, 블로그 주소, 광고 자리, Supabase, 문의 양식 주소) |
| `src/content/articles/*.md` | 글 (머리말은 JSON 값, 본문은 문단 + `::: stats` · `::: angle` 블록) |
| `src/content/editions.json` | 모닝 에디션 묶음 |
| `src/content/nba-2026.json` | NBA 개막 주간 · 크리스마스 · 주요 날짜 |
| `src/content/postseason-2026.json` | MLB 포스트시즌 시드 · 시리즈 |
| `src/content/analysis-records.json` | 복기 리포트 |
| `src/content/pages/*.html` | 안내 페이지 본문 |

## 자동 작업

`.github/workflows/site-build.yml`이 매시간 실행됩니다. 구글 · 네이버 블로그 새 글을 받아 다시 빌드하고, 바뀐 것이 있으면 커밋합니다.

## 점검

```
python3 src/tools/check.py
```

올리기 전과 매일 자동 점검에서 같은 기준으로 씁니다. 찌꺼기 파일, 쓰이지 않는 코드·스타일, 깨진 링크, 페이지 형식, 금지어, 사이트맵·검색 색인, 설정을 확인하고, 실패 항목이 있으면 종료 코드 1로 끝납니다.

## 문의(쪽지) 양식

`/contact/`의 양식은 `src/site.json`의 `contact.endpoint`에 적힌 주소로 내용을 보냅니다. 받는 쪽은 운영자 Google Drive의 "SFANDOM 쪽지함" 시트에 붙인 Apps Script 웹 앱입니다. 주소가 비어 있으면 양식은 보이지만 전송되지 않습니다.

## 자산

| 경로 | 내용 |
|---|---|
| `assets/brand/` | SFANDOM 로고 (SVG · PNG) |
| `assets/sfandom-brand-film-20260901.mp4` | 브랜드 필름 |
| `assets/sfandom-hero-loop.mp4` · `assets/sfandom-hero-poster.jpg` | 첫 화면 배경 영상과 첫 장면 |
| `assets/css/site.css` · `assets/js/site.js` | 스타일 · 스크립트 |

팀 로고는 리그 공식 주소에서 불러옵니다. `python3 src/tools/fetch_logos.py`를 실행하면 `assets/teams/`에 받아 두고 그 파일을 씁니다.
