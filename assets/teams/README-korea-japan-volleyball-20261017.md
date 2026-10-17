# SFANDOM team crest assets — 2026-10-17 review

**Status:** Review only — not connected to site UI, not deployed.

This branch adds 103 individually stored team crest files:
- K League 1 (2026): 12 SVG files `soccer/2026-27/k-league-1/`
- K League 2 (2026): 17 SVG files `soccer/2026-27/k-league-2/`
- Japanese J1 League (2026–27): 20 SVG files `soccer/2026-27/j1-league/`
- Japanese J2 League (2026–27): 20 SVG files `soccer/2026-27/j2-league/`
- Japanese J3 League (2026–27): 20 SVG files `soccer/2026-27/j3-league/`
- Korean men's V-League (2026–27): 7 PNG files `volleyball/2026-27/men/`
- Korean women's V-League (2026–27): 7 PNG files `volleyball/2026-27/women/`

All paths are relative to `assets/teams/`.

Each league folder has an `index.json` with exact team names, original source URLs, slugs, and relative paths. SVG files were checked for a valid <svg root and fetched successfully. Volleyball PNGs were checked for PNG signature.

Source details:
- Soccer: FootyLogos editorial/reference crest database; each team's source URL is recorded in that league's `index.json`.
- Volleyball: KOVO official 360 VR venue page `https://cdn.kovo.co.kr/court-views/index.html`, includes current 2026–27 **SOOP SOOPers** club emblem (not discontinued Pepper Savings Bank mark).

**IMPORTANT — usage rights:** Club crests are protected trademarks/copyrights belonging to the respective owners. Source availability does not confer redistribution or publication permission. In particular, KOVO explicitly prohibits unauthorized use of team logos. Review permissions/branding rules before merging into the public site. Do not hotlink source CDNs. Intended only for editorial team identification subject to rights review.

No existing site HTML/CSS/JavaScript or historical logos were changed.
