# SFANDOM Sports Analysis Guideline — File Index

> Repository documentation index only. This file does not alter any website runtime code.

## Document Identity

- **Canonical document:** `SFANDOM_Sports_Analysis_Standard_v1.0.docx`
- **Document title:** SFANDOM 스포츠 분석 표준 지침서
- **Document No.:** `SF-SOP-ANL-001`
- **Version:** `v1.0`
- **Effective date:** `2026-08-29 (KST)`
- **Status:** ACTIVE / CANONICAL
- **Scope:** SFANDOM daily sports analysis, Work analysis, pick selection and publication review

## Mandatory Input Set

Analysis must use the following four source groups as the base input set, in this fixed order:

1. 배당분석표
2. 해외 픽스터 픽
3. 구매율
4. 배당변동표(배변표)

If any required source is missing, do not replace it by assumption. The missing source must be identified before the full analysis is treated as complete.

## Core Analysis Sequence

1. 배당판 통합 및 경기 압축
2. H2H / sample review in the order **100 → 50 → 20**
3. 방향 일치 여부 우선 확인
4. 통계 신뢰 후보 선별
5. 승패·언더/오버·BTTS 등 시장 확장 검토
6. 선발/라인업, 홈·원정, 최근 경기 내용, 배당 변동 원인 교차검증
7. 예상 승리팀 자체 승률은 **마지막 검증 단계**에서 확인
8. 컷 미달 시 **NO PICK / PASS**

## Statistical Rules

- 장기 100경기 → 중기 50경기 → 최근 20경기 순으로 실제 원자료를 검토한다.
- 100/50/20 표본 간 방향 일치를 우선한다.
- 표본 표기는 `50경기`, `100경기`처럼 실제 기준을 명확히 표시한다.
- 축구 O/U 기본 기준선은 **2.5**로 둔다.
- 이변 가능성은 장기 표본의 이변 횟수와 비율을 함께 본다.
- 우선순위는 **통계 신뢰도 → 배당 메리트 → H2H 보조 판단**으로 둔다.

## Purchase-rate / Market Signals

- 구매율 **75–85%:** 가점 구간
- 구매율 **85–90%:** 경계 구간
- 구매율 **90% 이상:** 과열 가능성으로 회피 우선 검토
- 국내·해외 환산 확률 편차가 **3%p 미만**이면 중립 신호로 본다.
- 급격한 배당 변동은 결과 예측 자체가 아니라 원인 확인이 필요한 시장 신호로 취급한다.

## Fixed Pick Card Structure

1. 경기 / KST 시작시간
2. 선발 또는 핵심 라인업
3. 핵심 근거 3–4개
4. 배당 / 변동
5. AI 한줄 판단
6. SFANDOM PICK
7. 리스크 / PASS 조건

## Publication Verification

Before publication, verify at minimum:

- 한국시간(KST)
- 경기 일자 및 시작시간
- 팀명 / 상대팀
- 선수명 및 선발 여부
- 배당 및 변동 수치

Critical publication data should be cross-checked repeatedly before release. Historical picks and news must be preserved rather than silently overwritten.

## Governance

- This index records the currently adopted SFANDOM analysis standard.
- Later approved revisions supersede conflicting portions of this v1.0 index and should be recorded as a new version or revision entry rather than silently overwriting history.
- Website production code, CSS, JavaScript and existing archive data are outside the scope of this document-index commit.

---

**Index created:** 2026-08-31 (KST)  
**Repository:** `sfandomsportji-cpu/sfandomsportji-cpu.github.io`
