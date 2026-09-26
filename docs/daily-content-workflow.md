# SFANDOM Current Content / Work Workflow

**Last updated:** 2026-09-27 KST  
**Status:** CURRENT / CANONICAL

## 0. Source-of-truth order
When rules conflict, use this order:
1. Ji's latest explicit instruction in the current work
2. Currently enabled ChatGPT Work / automation instruction
3. This document
4. Older GitHub history, archived docs, or past commits

Never revive an older rule just because it remains in Git history.

## 1. SFANDOM main site
- Main-site work is independent from Naver Blog, Google Blogger, and Instagram.
- Before any publish, inspect the current live/site code state and preserve the previous live edition in Archive.
- Prepare long-form editorial content; do not collapse it into cards, placeholders, or 300–500 character summaries.
- Do not merge to main or deploy without the day's explicit approval when the active Work instruction requires approval.
- Pick remains excluded unless Ji explicitly reopens it.
- After a real publish, verify the live site and record changed files / commit / live status. Never report completion before verification.

## 2. Naver Blog
- Naver Blog is text-first and independent from the main site and Google Blogger.
- **Legacy rule deleted:** 2 posts per day / approximately 300 Korean characters.
- Never use 300–500 character short-form as a fallback for a requested magazine article.
- The exact number of posts and page-length target must come from Ji's latest explicit instruction or the currently enabled Work automation for that run.
- If no current run rule is active, do not infer an old count or old page target from Git history.
- When long-form is requested, measure the **pure body**, excluding title, image captions, hashtags, and keyword padding.
- Verify current facts, schedules, standings, transfers/contracts, and statistics before drafting.
- Do not call an article complete merely because it has many headings; actual body density and length must pass.

## 3. Google Blogger
- Current operating target: **3 independent articles, each approximately 7 pages of real long-form body text**.
- "3 articles total 7 pages" is invalid.
- Title, image text, hashtags, labels, and repeated keywords do not count toward the body-length target.
- Before publication, run quality review for title, one-line summary, flow, body density, relevant images/charts when needed, key emphasis, closing, hashtags, labels, and actual 7-page reading length.
- If any item fails, **report first and do not auto-edit**. Edit only after Ji instructs it.
- Use Blogger CMS posting only.
- Do not recreate or modify Blogger theme, custom pages, Bridge, RSS sync, Google Cloud/API/OAuth auto-posting, or a separate /blog/ structure.
- Actual publication requires Ji's explicit approval.

## 4. Instagram Reels
- Current daily operation is the **10-Reels pre-meeting workflow**, not the obsolete one-Reel-per-day rule.
- Review Ji's candidate synopses before production and classify them as confirm / hold / replace.
- Do not force low-value content just to fill the number.
- Global reach is prioritized.
- Default caption direction: English 3 lines + Korean 1–2 lines when appropriate.
- Hashtags / core keywords: English 70% + Korean 30%, and every keyword begins with #.
- Production does not auto-publish; move to production/publishing only after the day's explicit decision.

## 5. Reels / video file production
- Follow `docs/SFANDOM_VIDEO_WORKFLOW_V1.md` for technical production.
- Preserve source frame rate when practical; fixed final delivery rule is MP4 H.264 High + yuv420p + AAC + faststart.
- No blurred background for vertical/mobile fill; crop the source naturally.
- Start with a short fade-in and end with a gradual video + audio fade-out; never end with an abrupt cut.
- Do not label a file final until the file exists and technical/visual QA is complete.

## 6. Image extraction
- `00_CRITICAL_IMAGE_WORKFLOW.md` is the current image-collection authority.
- Real recent news/official photos only; no AI-generated substitutes for requests for real news/game photos.
- Exclude visible broadcaster/news/blog/SNS watermarks where the workflow requires clean photos.
- Do not reuse an old download bundle as if it were the current result.

## 7. Publication / record integrity
- A saved draft is not a published post.
- A prepared automation instruction is not proof that an external platform action occurred.
- Report only states actually verified through the relevant tool/platform.
- After a real SFANDOM site publication, follow `docs/PORTFOLIO_WORKFLOW.md` for publication-history recording.

## 8. Deleted legacy rules
The following are explicitly obsolete and must not be restored from Git history:
- Naver Blog: 2 text posts × about 300 Korean characters
- Instagram Reels: mandatory 1 Reel/day as the master daily rule
- Blogger: 10 chapters / 10 pages as a mechanical template
- Blogger Bridge / RSS / Cloud API/OAuth auto-posting
- Treating heading count as proof of page-length compliance
