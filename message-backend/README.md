# SFANDOM private message intake

This directory contains the Google Apps Script receiver for `message.html`.

The Google Sheet ID is intentionally **not** stored in the public repository. Configure it as an Apps Script Script Property instead.

## One-time deployment

1. Create a new Google Apps Script project under the SFANDOM Google account.
2. Paste `Code.gs` into the project.
3. In **Project Settings → Script Properties**, add:
   - Property: `SPREADSHEET_ID`
   - Value: the private `SFANDOM 방문자 메시지함` native Google Sheet ID
4. Deploy as a **Web app**:
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Open the deployed `/exec` URL in a browser. It should return:
   - `{\"ok\":true,\"service\":\"sfandom-message-intake\"}`
6. Replace `__SFANDOM_MESSAGE_WEB_APP_URL__` in `message.html` with that `/exec` URL.
7. Submit one real test message from the site and verify a new row appears only in the `메시지함` tab.
8. Keep the pull request in Draft until the real end-to-end receive test passes.

## Safety notes

- The spreadsheet remains private.
- The spreadsheet ID is kept out of GitHub and stored only in Apps Script Script Properties.
- A honeypot, basic rate limit, input length checks, email validation, locking, and spreadsheet-formula injection protection are included.
- The feature is intentionally receive-only; no chat, account, or reply inbox is added to the static site.
