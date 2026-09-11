# SFANDOM PORTFOLIO ARCHIVE WORKFLOW

**Version:** 1.1  
**Start date:** 2026-09-01 KST  
**Record #1 timestamp:** 2026-09-01 08:41 KST  
**Purpose:** SFANDOM이 실제로 발행한 콘텐츠를 사이트 런타임과 분리해 GitHub 문서 영역에 날짜별·항목별로 축적한다.

---

## 1. Core principle

**사이트 = 현재 발행본**  
**GitHub docs/portfolio = SFANDOM의 작업 이력과 포트폴리오**

메인 사이트는 최신 콘텐츠를 1:1 교체한다. 과거 발행물은 메인 HTML에 숨겨 보존하지 않는다. 포트폴리오 기록은 `docs/portfolio/` 아래에 별도로 저장하며 사이트 런타임에서는 불러오지 않는다.

---

## 2. What to archive

매일 실제 발행된 콘텐츠를 다음 항목으로 분류한다.

1. DAILY NEWS
2. KAIRO FEATURE
3. NEXT MATCH
4. SFANDOM PICK
5. VIDEO / REELS / SPECIAL CONTENT
6. SITE / BRAND MILESTONE

발행하지 않은 후보는 포트폴리오에 "Published"로 기록하지 않는다. 필요하면 별도 Notes에 후보였음을 남긴다.

---

## 3. Folder structure

```
docs/
  PORTFOLIO_WORKFLOW.md
  portfolio/
    PORTFOLIO_INDEX.md
    2026/
      09/
        2026-09-01.md
        2026-09-02.md
```

날짜 파일명은 반드시 KST 기준 `YYYY-MM-DD.md` 형식을 사용한다.

---

## 4. Mandatory save rule

콘텐츠를 실제로 업데이트하거나 발행할 때마다 포트폴리오 저장을 **반드시 같은 작업의 후속 단계로 수행한다.**

누락 금지 항목:
- DAILY NEWS
- KAIRO FEATURE
- NEXT MATCH
- SFANDOM PICK
- VIDEO / REELS / SPECIAL CONTENT
- SITE / BRAND MILESTONE

해당 항목이 없으면 생략하지 말고 **None / Not published**로 명시한다.

각 실제 발행 건은 날짜 안에서도 순번을 부여한다.

예:
- Portfolio #1 — 2026-09-01 08:41 KST
- Portfolio #2 — 같은 날 추가 콘텐츠 발행
- Portfolio #3 — 같은 날 영상/특집 추가 발행

즉, **하루 1회 저장이 아니라 실제 콘텐츠 업데이트 1회마다 저장**한다.

---

## 5. Daily record format

각 날짜 파일에는 최소 다음을 기록한다.

- Portfolio 순번 (#N)
- 기록 시각(KST)

- 발행 날짜(KST)
- 발행 상태
- GitHub main commit SHA
- 관련 PR 번호
- DAILY NEWS 제목과 핵심 사실
- KAIRO FEATURE 제목과 핵심 포인트
- NEXT MATCH 경기·KST·선발
- PICK 발행 여부와 결과
- 사용 이미지/출처 메모
- 영상/특집 여부
- 운영 메모

---

## 6. Index rule

`docs/portfolio/PORTFOLIO_INDEX.md`에서 날짜별 기록을 역순으로 색인한다.

항목:
- Date
- Daily News
- Kairo Feature
- Next Match
- Pick
- Commit
- Record link

---

## 7. Runtime isolation

포트폴리오 저장 작업에서는 다음을 수정하지 않는다.

- `index.html`
- 공통 CSS/JS
- Header / Footer / Navigation
- LIVE
- Archive runtime page
- CDN / GitHub Pages / DNS 설정

즉, Portfolio 기록 작업은 **documentation-only**로 수행한다.

---

## 8. Asset policy

포트폴리오 문서에서는 원본 이미지를 중복 복사하지 않는다.

- 이미 repository asset에 있으면 경로만 기록
- 외부 공식 이미지는 출처 URL/기관만 기록
- 영상은 파일을 중복 저장하지 않고 원본 위치/게시 링크를 기록
- 대용량 자산은 포트폴리오 때문에 복제하지 않는다

---

## 9. Preservation rule

- 과거 날짜 파일을 덮어쓰지 않는다.
- 사실관계 정정이 필요하면 수정 이유와 날짜를 기록한다.
- 삭제보다 정정 기록을 우선한다.
- Git History는 추가 증빙으로 사용한다.
- 포트폴리오 기록은 공개 사이트에서 보이지 않아도 GitHub에서 언제든 조회 가능해야 한다.

---

## 10. Publication workflow integration

콘텐츠 발행 작업이 끝나면 다음 순서로 포트폴리오를 기록한다.

1. 실제 main 반영 여부 확인
2. 최종 commit SHA 확인
3. 실제 발행 항목을 DAILY NEWS / KAIRO FEATURE / NEXT MATCH / PICK / VIDEO·SPECIAL / MILESTONE로 분류
4. 해당 업데이트의 Portfolio 순번과 KST 기록 시각 부여
5. 날짜 파일 작성 또는 같은 날짜 파일에 새 순번 섹션 추가
6. Portfolio Index 업데이트
7. docs-only PR 생성
8. 변경 파일이 Portfolio 문서뿐인지 확인
9. Merge

오류가 1건이라도 발생하면 SFANDOM Operations Manual v2.2의 ERROR STOP & NORMALIZATION 절차를 적용한다.

---

## 11. Goal

이 기록은 단순 백업이 아니다.

SFANDOM이 시간이 지나면서:
- 어떤 콘텐츠를 만들었는지
- 어떤 스포츠를 다뤘는지
- 어떤 분석·편집 기준을 사용했는지
- 사이트와 브랜드가 어떻게 성장했는지

를 실제 날짜와 Git commit으로 증명하는 **장기 포트폴리오 원본**으로 사용한다.
