# SFANDOM — NHL & NFL club crest assets (review only)

**Status:** Assets staged in a separate branch for review. No main-branch site code or CSS/HTML updated. No automatic publication.

## Inventory
- 32 NHL team crests (2026–27): `assets/teams/nhl/2026-27/*.svg`
- 32 NFL team crests (2026): `assets/teams/nfl/2026/*.png`
- League-specific `index.json` provides exact team identity, slug, original image provenance, and local file path.

NHL images are original vector SVGs from the NHL asset server, using each team's `_light.svg` logo variant.
NFL images are PNG team marks fetched via ESPN's public team logo CDN; most are 500×500, while the New York Jets source serves 4096×4096.
Each of the 64 image files was downloaded and validated as the expected file format before staging.
Utah Mammoth uses the modern Utah Mammoth identity, NHL asset code `UTA`.

## Usage
These are local repository files: no external image hotlinks are required at runtime after approved deployment.
Suggested alt text: exact team name in each `index.json`.
Only use after checking club/logo trademark, publisher, redistribution, and editorial usage rights.

**Important:** Authentic team crests are third-party intellectual property; images being publicly retrievable does **not** grant rights to republish or redistribute them. Review brand usage permissions before merging into the public site.

## Quality checks
- 32 NHL team SVGs parsed and rejected if they contained script/javascript markers.
- 32 NFL logo PNGs validated with PNG signature and raster dimensions.
- 32+32 unique team slugs and individual image paths.
- No existing images, articles, pages or CSS changed.
