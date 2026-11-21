# SFANDOM 감시·보관·ESPN 권리 검증 (2026-11-22)

**상태:** 검토용 브랜치. 운영 `main`·PR #30/#31/#32 또는 사이트 발행에 자동 적용되지 않음.

## 1. 외부 감시 프로그램 — 준비 완료 / 실행 인프라 미등록

`src/tools/external_nba_watchdog.py`는 GitHub Actions의 예약 실행 이력을 **외부 환경에서 읽는 검사기**입니다. 모니터 대상: `main`의 `.github/workflows/nba-injury-watch.yml` 예약 실행만.

- `OK`: 마지막 예약 실행과 정상 종료가 모두 22분 이내.
- `PENDING_WITH_RECENT_SUCCESS`: 최근 정상 종료가 존재하며 신규 실행 대기/진행 중.
- `SCHEDULE_SILENT`: 최근 예약 실행이 22분을 넘게 없음.
- `LATEST_FAILED`: 마지막 실행 실패.
- `NO_RECENT_VERIFIED_RUN`: 최근 실행 흔적은 있어도 최근 22분 내 정상 종료 없음.
- `NO_SCHEDULE_RUNS`: 운영 PR 미병합·미가동 등. **정상 실행으로 간주 금지.**
- `CHECKER_FAILED`, `INVALID_RESPONSE`, `FUTURE_RUN_TIME`: 검사기 장애·시계 이상. 반드시 경고.

```bash
# 이 커맨드는 모니터 자체가 아닌 별도 서버/PC/외부 서비스에서 실행
python src/tools/external_nba_watchdog.py
# 0=정상/최근 정상+진행 중, 1=비정상; JSON 형태의 실행 시각/상태 출력
```

**실제 독립 감시는 아직 활성화되지 않았음:** GitHub 외부의 독립 스케줄러(예: 외부 모니터링 서비스, 별도 호스트)와 통지 채널이 있어야 합니다. 동일 GitHub Actions 기반의 별도 저장소는 *워크플로 간* 장애만 분리하고 **GitHub 전체 장애**는 탐지하지 못할 수 있습니다. 10분 간격으로 검사한다면 22분 공백 + 다음 검사까지 최대 약 10분의 발견 지연이 가능합니다. 비정상 발생 즉시 격리를 보장하지 않습니다.

**상태별 실제 실행:** 이 스크립트는 알림 대상 JSON을 출력하고 비정상일 때 1로 종료합니다. 실제 문자·메일 발송 및 스케줄러는 별도 설정 필요. NBA 예약 workflow가 `main`에 활성화되지 않았으므로 지금은 `NO_SCHEDULE_RUNS`가 정상적인 *준비 단계 현상*입니다.

## 2. 마지막 정상 데이터 보관

본 브랜치는 `.github/workflows/nba-injury-watch.yml`의 감사 아티팩트 보존을 **2일 → 30일**로 늘리고, 정상 검증에만 `.monitor/heartbeat.json`을 추가합니다. 부상 데이터는 절대로 사이트에 발행하지 않습니다.

- GitHub 공식 문서상 public repository 아티팩트 보관 설정은 보통 **1~90일** 범위이며, 저장소/조직 정책의 더 낮은 제한이 우선합니다.
- 30일은 **임시 완충 구간**이고 영구 보존이 아닙니다. GitHub 또는 인증서버 중단, 30일 이상 누락에는 독립된 저장소가 필요합니다.
- 권장 상위 보관: 사용자 소유의 **비공개 `sfandom-analysis` 저장소** 또는 암호화·버전 관리·복구 보호를 적용한 별도 스토리지. 검증된 마지막 정상본의 JSON, SHA-256 해시, 원본 URL, 보고서 시각·검증시각, 검증 코드 버전, 변경 이력을 보관. 원본 PDF나 ESPN 이용 허가가 불명확한 원본 JSON을 공개 저장소에 재배포하지 않음.
- 이후 PR #31의 `safe_mode.seal`과 연계할 경우 단순 SHA-256은 *우연한 손상*은 탐지해도 공격자가 파일과 해시를 함께 바꾸는 상황은 방어하지 못함. 권한분리·서명/HMAC 또는 버전 관리 및 잠금이 필요.
- **장기 외부 보관 자동 실행은 아직 설정되지 않음.** 인증·비공개 저장 목적지·보존 정책이 확정되면 별도 승인된 파이프라인으로 연결.

참고: [GitHub Actions 아티팩트 보존 문서](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository), [Actions 예약 지연/누락 문서](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows).

## 3. ESPN 접근 및 재배포 권리 상태 — 미허가, 운영 자동화 보류

**현재 결론:** `site.api.espn.com`의 JSON이 HTTP 200을 반환하는 것은 접근 가능성을 뜻할 뿐, SFANDOM 서비스의 자동 수집·반복 저장·상업 활용·공개 재배포에 관한 **허가 증거가 아닙니다.**

ESPN 고객지원은 ESPN 이용약관으로 Disney 약관을 연결합니다. 확인된 Disney 일반 이용약관은 명시적인 허가 없이는 자동화된 수집·복사·추출 및 상업/사업 활용을 제한합니다.

1. [ESPN Fan Support — Terms of Use](https://support.espn.com/hc/en-us/articles/360035445091-Terms-of-Use)
2. [Disney Terms of Use — License/Restrictions](https://disneytermsofuse.com/english/)
3. [Disney Studios Licensing — ESPN/ABC Sports 문의 항목](https://www.disneystudiolicensing.com/) (영상/콘텐츠 권리 문의; **데이터 API 승인 창구로 확정되지 않음**)

SFANDOM 담당자가 서면으로 확인해야 할 범위: (a) 3종목 `site.api.espn.com` 엔드포인트 접근 허용, (b) 자동 폴링 빈도 및 요청량, (c) JSON 데이터를 내부 분석/저장·2차 가공할 수 있는지, (d) 기사·사이트에 표시/재배포 가능한 필드와 귀속 표기, (e) 선수 정보 및 서드파티 리그 권리, (f) 종료·정정·삭제/갱신 조건.

**현재 운용 안전선:** PR #32의 `espn_adapter.py`는 오프라인 JSON 정규화만 사용. 정기 네트워크 수집, ESPN 자료 공개 게시, 자동 '공식 확정' 승격, 재배포는 **권리 확인 전 금지**.

ESPN+ for Business는 주로 공공장소 ESPN+ 영상 상영에 대한 상업 라이선스이며, 스포츠 데이터 API 이용권으로 혼동하지 마세요.

## 4. 병합/실행 구분

- P0 실제 NBA PDF 세 개에 대한 독립 엔진 전수 대조는 `docs/NBA-REAL-PDF-AUDIT-20261122.md` 참고.
- 본 PR은 `feature/nba-injury-monitor-20261121`을 기준으로 생성. 기존 #30, #31, #32는 그대로.
- 별도 PR #31의 복구 실행기 `recovery_runner.py` 및 PR #32의 ESPN 어댑터 연결·통합 테스트는 **운영 병합 전에 임시 통합 브랜치에서**.
- 외부 감시 서비스 및 비공개 장기 보관은 별도 실행 계정·인증·보존 정책이 마련되기 전에는 활성화했다고 주장하지 말 것.
