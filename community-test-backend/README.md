# SFANDOM Community Test Backend

Test storage is separated from the public GitHub repository.

## Private cloud storage
- Drive folder: `SFANDOM COMMUNITY TEST STORAGE`
- Spreadsheet: `SFANDOM COMMUNITY TEST DB`
- Tabs: `POSTS`, `COMMENTS`, `META`
- Grouping timezone: `Asia/Seoul`
- UI/server page size: **10 posts**

Do not commit the spreadsheet ID or deployed Apps Script URL to a public repository.

## Apps Script deployment
1. Create a standalone Google Apps Script project under the SFANDOM Google account.
2. Paste `Code.gs`.
3. Add Script Property `SPREADSHEET_ID` with the private spreadsheet ID.
4. Deploy as Web app, execute as the owner, access set to Anyone for the tester endpoint.
5. Put the deployed `/exec` URL into the homepage section's `data-endpoint` value on the private/test branch only.
6. Test list paging and one test post before any production merge.

The backend returns at most 10 posts per request and slices server-side.
