# SFANDOM private message intake

This directory contains the optional Google Apps Script receiver for `message.html`.

Deployment is intentionally not automatic. Before enabling the page:

1. Create or select the private `SFANDOM 방문자 메시지함` Google Sheet.
2. Replace `__SFANDOM_MESSAGE_SPREADSHEET_ID__` in `Code.gs`.
3. Deploy as a Google Apps Script web app running as the owner and allowing anonymous form submissions.
4. Replace `__SFANDOM_MESSAGE_WEB_APP_URL__` in `message.html` with the deployed `/exec` URL.
5. Submit test messages from desktop and mobile and verify only the `메시지함` sheet receives them.
6. Review the privacy notice before linking `message.html` from the public navigation.

Until both placeholders are replaced, the submit button remains disabled and the page must not be linked from `index.html`.
