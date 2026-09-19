# SFANDOM Official Website

SFANDOM 스포츠 데이터·분석·콘텐츠 사이트 운영 저장소입니다.

## Production
- 기본 브랜치: `main`
- 사이트: `sfandom.com`
- 일일 콘텐츠는 홈의 Daily News / KAIRO Feature / Next Match / Player Spotlight 슬롯에 발행합니다.
- 커뮤니티 v1은 메인 페이지의 10-post pagination 보드로 통합되어 있습니다.
- 실제 게시글·댓글 등 운영 데이터는 GitHub 코드와 분리된 클라우드 저장소를 사용합니다.

## Maintenance
- 교체 전 콘텐츠/프리뷰는 `archive/`에 날짜별 보존합니다.
- 브라우저 캐시는 파일명 뒤 버전 쿼리로 갱신합니다.
- 임시 파일, 로그, 로컬 캐시, 환경변수 파일은 커밋하지 않습니다.
- 이미지에는 가능한 경우 `srcset` / `sizes`를 사용해 모바일 전송량을 줄입니다.
