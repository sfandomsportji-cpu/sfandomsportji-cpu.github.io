# SFANDOM SITE INSPECTION INDEX

SFANDOM 사이트 점검 기록 색인.

점검 기록은 날짜 + 순번으로 누적하며, 과거 점검 파일을 덮어쓰지 않는다.

| Date (KST) | Inspection | Status | Summary | File |
|---|---|---|---|---|
| 2026-08-31 | #1 | Recorded | 전체 오류 점검. SEV-1/2 없음. 캐시 버전 불일치, Content 최신성, 외부 의존성 위험 확인. | [2026-08-31-check-01.md](inspections/2026-08-31-check-01.md) |

## Naming rule

`docs/inspections/YYYY-MM-DD-check-NN.md`

예:
- `docs/inspections/2026-08-31-check-01.md`
- `docs/inspections/2026-08-31-check-02.md`
- `docs/inspections/2026-09-01-check-01.md`

## Rule

- 점검은 진단 기록과 실제 수정 작업을 분리한다.
- 오류가 1건이라도 발생하면 ERROR STOP & NORMALIZATION 절차를 따른다.
- 해결 완료 여부는 후속 점검에서 재검증한다.
