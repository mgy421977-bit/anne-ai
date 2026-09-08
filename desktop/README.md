# ANNE Desktop Runtime

ANNE Desktop is offline-first. GitHub is used only for release discovery and optional updates; meeting audio, transcripts, translations, and MITOS memory remain on the user's local disk.

## First run

1. Launch `ANNE.exe`.
2. ANNE creates the configured local workspace.
3. Required runtime/model assets are checked locally.
4. If internet is available, ANNE may check `release.json` for a newer signed-by-hash release package.
5. If internet is unavailable, ANNE continues in offline mode.

## Local data

The default workspace is `%USERPROFILE%\\ANNE\\data`. It can be changed in `config.json` or with `ANNE_DATA_DIR`.

- `recordings/meetings/<meeting-id>/audio.wav`
- `transcripts/<meeting-id>.jsonl`
- `translations/<meeting-id>/direct_tr.jsonl`
- `translations/<meeting-id>/semantic_tr.jsonl`
- `reports/<meeting-id>.json`
- `memory/mitos.sqlite3`
- `models/`
- `logs/`

No meeting data is uploaded by the updater.

## Release process

A release ZIP is published as the `anne-desktop.zip` asset. After computing SHA-256, update `desktop/release.json` with the release version and hash. The client verifies the hash before extraction.
