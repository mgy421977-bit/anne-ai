# GitHub → Dropbox Repository Sync

## Purpose

GitHub remains the source of truth for ANNE AI. Dropbox receives a mirrored
working copy under:

`/ANNE AI/`

The mirror preserves repository-relative paths and skips Git metadata and
local Python cache directories.

## Required GitHub Actions secrets

- `ANNE_DROPBOX_APP_KEY`
- `ANNE_DROPBOX_SYNC_REFRESH_TOKEN`

The refresh token must belong to the Dropbox account intended for the mirror
and must be authorized for file write access.

## Security boundary

The refresh token is never committed to the repository. GitHub Actions reads
it only from repository secrets. The sync job has read-only GitHub contents
permission and write access only to the configured Dropbox account.

Dropbox is a mirror/knowledge surface, not the authoritative Git history.

## First activation

1. Create/configure a Dropbox API app.
2. Enable the required file scopes for the sync credential.
3. Authorize the app with offline access and retain the refresh token.
4. Add the two values above as GitHub Actions secrets.
5. Run **ANNE AI → Dropbox Sync** manually once.
6. Subsequent pushes to `main` trigger synchronization.

## Important

The first sync may be large. The user's Dropbox Basic quota is limited, so
the repository size must remain within the available quota.
