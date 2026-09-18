# SFANDOM Community DB V1

This directory contains only the database/schema and cloud data access layer for the community prototype.

## Principle

- GitHub stores code, schema, migrations, and recovery instructions.
- Live posts/comments are stored in a cloud database.
- No production/live community data is committed to GitHub.
- No secret/service-role key is committed to GitHub.
- The current SFANDOM site is not modified by this branch.

## V1 scope

- posts
- comments
- cloud adapter
- read + insert only from the public client
- update/delete/admin moderation are deferred until authentication is added

## Files

- `schema.sql`: PostgreSQL schema + indexes + basic RLS policies
- `community-store.js`: provider-neutral contract helpers
- `supabase-store.js`: Supabase/PostgreSQL cloud adapter
- `config.example.js`: placeholder config only; never put secrets here

## Test flow

1. Create a DEV cloud database.
2. Apply `schema.sql`.
3. Copy `config.example.js` to a local/non-secret runtime config.
4. Connect the adapter from a separate community-lab page.
5. Verify: create post -> reload -> persists -> list comments -> create comment.
6. Observe several days before any merge into the main site.

This is an isolated prototype. Do not merge into `main` until the storage flow is verified.
