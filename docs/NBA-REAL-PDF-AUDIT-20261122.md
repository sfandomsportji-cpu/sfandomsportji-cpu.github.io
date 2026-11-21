# SFANDOM — NBA 실물 PDF / 팀 오매칭 검증 기록 (2026-11-22)

**실행 위치:** 독립 브라우저 테스트 환경 / `pdfplumber 0.11.7` + `PyMuPDF 1.26.3` (실제 PDF 바이너리). 원본 PDF는 저장소에 커밋하지 않았습니다.

**비고:** 본 기록은 내부 감사용입니다. 선발 라인업 검증이나 공개·재배포 승인이 아닙니다.

## P0 발견과 수정

원본 5페이지 보고서의 제목 `Injury Report:`와 꼬리말 `Page N of 5`가 좌표상 **Team 열**에 들어왔습니다. 기존 `parse_pages`는 이를 팀명으로 덮어썼고, 다음 페이지에서 이어지는 선수에게 잘못된 팀을 연결했습니다.

실제 발견: Grant, Jerami / Jerome, Ty / Reese, Julian / Watford, Trendon 일부가 `team = "Injury Report:"`로 파싱됨.

수정:
1. 매 페이지 머리말 `Injury Report:` 및 `Page N of M` 꼬리말을 팀 컨텍스트 변경 전에 제외.
2. **30개 NBA 팀명 → 공식 경기 약어** 매핑으로 매 선수의 팀이 해당 `AWAY@HOME` 경기 안에 있는지 검사. 불일치 시 전체 PDF 격리.
3. 선수·팀·상태를 두 개의 독립 PDF 엔진으로 일치 검증하는 로컬 감사기 `src/tools/nba_pdf_audit.py` 추가.

## 2026-11-21 실제 보고서 3개 대조

| 보고서 (ET) | 원문 페이지 | 상태 행 수 | 페이지별 행 수 | 독립 엔진 불일치 | SHA-256 |
|---|---:|---:|---|---:|---|
| [07:00 AM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_07_00AM.pdf) | 5 | 51 | 15,17,15,4,0 | 0 | `0a01587ca00acedd25fa92f0257d098ed87e61bf24b80abe25e25e1c58554053` |
| [01:15 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_01_15PM.pdf) | 5 | 59 | 15,17,16,11,0 | 0 | `30e110d348f9b2dfcf83bf7e91d87ec7fbb72e77d795394c3daa52722e04f67e` |
| [03:00 PM](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_03_00PM.pdf) | 5 | 60 | 15,17,16,12,0 | 0 | `311d15dc867b534cdb09fd9afe282ba0a1742931679018c0e8499b5757535e1a` |
| **합계** | **15** | **170** | | **0** | |

**검증 기준:** 두 PDF 엔진이 추출한 170개 `(경기일, 대진, 팀, 선수명, 부상상태)` 키 전체가 일치했고, 파서의 NBA 팀-경기 교차 검증을 통과했습니다. 원본을 시각적으로도 확인해 페이지 경계·선수 상태 변경 사례를 표본 검토했습니다.

실제 보고서 간 확인된 변동 예: Barlow, Dominick **Probable → Available**, Maxey, Tyrese **Questionable → Available**, Jerome, Ty **Probable → Available** (03:00 PM 보고서). 이는 공식 부상 상태이며 선발 확정이 아닙니다.

## 재현 방법 (원본 파일은 직접 확보; 인터넷 요청 기능 없음)

```bash
python -m pip install pdfplumber==0.11.7 PyMuPDF==1.26.3
python src/tools/nba_pdf_audit.py \
  --sample /secure/nba-0700.pdf https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_07_00AM.pdf \
  --sample /secure/nba-1315.pdf https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_01_15PM.pdf \
  --sample /secure/nba-1500.pdf https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-11-21_03_00PM.pdf
```

- 감사기 `PASS`는 **이 세 PDF만 검증**했음을 의미함. 다른 날짜/양식의 자동 통과 근거가 아님.
- 오해 방지: 원본 보고서의 `NOT YET SUBMITTED`는 **선수가 없거나 Available이라는 뜻이 아님**.
- NBA/PDF 이용 권리는 별도 검토 대상. 원본 PDF를 public git 저장소에 배포하지 않음.
- 운영 `main`, PR #30/31/32 병합 또는 사이트 발행은 이 브랜치에서 수행하지 않음.
