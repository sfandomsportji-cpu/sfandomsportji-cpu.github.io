# SFANDOM MLB Highlight Workflow — Locked Reference

**Saved:** 2026-09-15 KST  
**Purpose:** Prevent future drift, date confusion, recycled footage, or template redesign when producing SFANDOM daily MLB highlight videos.

## Canonical master
- **Style / layout / pacing master:** `SFANDOM_MLB_2026-09-07_FINAL_GAME_AUDIO_FIXED.mp4`
- Treat this file as the **absolute template**, not as a loose visual reference.
- When Ji says **“그대로 / 지난번처럼 / 하던 방식대로”**, do **not** redesign, reinterpret, or invent a new layout.

## Date rule
- Always resolve the requested **KST publishing date first**.
- Example from this chat:
  - User asked on **2026-09-15 KST** for **“어제 메이저리그 하이라이트”**.
  - Target publishing date = **2026-09-14 KST**.
  - Corresponding MLB game date used = **2026-09-13 U.S. local date**.
- Never mix KST publishing date with U.S. game date in filenames, overlays, captions, or source selection.

## Footage rule — non-negotiable
- Use **actual official MLB game footage from the correct requested date only**.
- **NO recycled archive footage.**
- **NO prior-day footage.**
- **NO AI-recreated baseball action.**
- **NO Runway-generated baseball action.**
- If the correct-date official footage cannot be obtained or verified, say **“오늘은 제작 불가”** rather than substituting older footage.

## Audio rule
- **BGM = 0**.
- **Artificial transition SFX = 0**.
- Preserve original broadcast/game audio only: announcer, bat crack, glove, crowd, stadium sound.

## Output spec
- Vertical **9:16**
- **1080×1920**
- **30 fps**
- Video: **H.264**
- Audio: **AAC**
- Typical runtime: about **35 sec**
- Typical structure: **5 strong sequences × about 7 sec each** unless Ji requests otherwise.
- Clean hard cuts.

## Locked visual behavior
- Reproduce the **9/7 approved SFANDOM frame** exactly.
- Do not invent a new “card” design.
- Do not shrink game footage into an arbitrary small band.
- Keep the 9/7 title / matchup / source / footer structure and spacing.
- Use the approved black SFANDOM magazine frame behavior.
- Actual MLB footage remains the visual priority.

## Required production workflow
1. Resolve the requested **KST target date**.
2. Resolve the corresponding **U.S. MLB game date**.
3. Verify that day’s schedule/results from official current data.
4. Obtain only official MLB source clips for that date.
5. Inspect each source clip visually/contact-sheet style before selecting a cut.
6. Verify the selected source contains the intended play/event.
7. Cut the exact action moment deliberately — **never choose timestamps blindly**.
8. Apply the **9/7 master template without redesign**.
9. Render with original game audio only.
10. Run `ffprobe` to verify codec, dimensions, fps, audio, and duration.
11. Inspect rendered frames visually before calling it final.
12. Only after both technical and visual QA, provide the MP4 to Ji.

## Failure policy
- If any required source is missing, uncertain, stale, or visually unverified: **stop and report that the video cannot be produced correctly yet**.
- Never compensate for missing footage by recycling an older MLB clip.
- Never call a file “today / yesterday / final” unless its footage and date were actually verified.

## 2026-09-15 incident — lesson locked
The assistant repeatedly failed this workflow by:
- confusing KST and U.S. dates,
- reusing older footage while calling it current,
- redesigning the approved template,
- cutting by arbitrary timestamps,
- and declaring files complete before sufficient visual verification.

Ji explicitly rejected this behavior. These versions are **invalid and must never be used as references**.

The later corrected workflow succeeded only after returning to the original method: correct date mapping, actual official MLB footage, approved 9/7 template, original game audio, and post-render QA.

## Corrected reference from this chat
**Valid final file:** `SFANDOM_MLB_2026-09-14_FINAL_GAME_AUDIO_FIXED.mp4`

Correct-date source set used for the successful rebuild:
- Miami — Agustín Ramírez walk-off 2-run HR
- Boston — Payton Tolle immaculate inning
- Yankees — Ben Rice leadoff HR #38
- Cleveland — Travis Bazzana 2-run HR sequence used after source verification
- Cincinnati — Eugenio Suárez 3-run HR #24

## Ending / logo outro rule
- At the very end, the final game footage must **fade down gradually** instead of cutting abruptly.
- Transition into a **full black screen**.
- On black, show the **white SFANDOM company logo** cleanly and centered.
- No extra copy, no sponsor-like clutter, no BGM; keep only the visual logo close.
- Default feel: restrained, premium, magazine-like ending.
- Unless Ji requests otherwise, treat this fade-to-black + white SFANDOM logo as the **standard ending for future MLB highlight videos**.

## Communication rule
- Do not bluff progress.
- Do not say “완성 / 검수 완료 / 오늘 영상 맞다” until verified.
- If a step failed, say so directly.
- If the user says a file is recycled/wrong, treat that as a blocking issue and re-check the actual rendered content instead of arguing from source URLs or render logs.

---

**SFANDOM fixed principle:**  
**Correct date → correct official source → exact approved template → original game audio → technical QA → visual QA → final MP4.**
