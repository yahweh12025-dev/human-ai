# Backup Policy

## Obsidian Vault

**Single backup only. No rotating copies.**

- Location: `gdrive:backups/obsidian` (one folder, always overwritten)
- Source: `~/human-ai/data/obsidian/` (canonical vault)
- Sync command: `rclone sync ~/human-ai/data/obsidian gdrive:backups/obsidian`
- Schedule: Every 6 hours via cron (syncs, does NOT create dated copies)

**Historical timestamped backups (`obsidian_vault_backup_YYYYMMDD_*`) have been deleted.**
Never create new dated backup folders — use `rclone sync` (overwrites in place).

## .env Secrets

- Location: `gdrive:backups/env/.env` and `gdrive:backups/env/consolidated.env`
- Manually updated whenever `.env` changes
- Contains: all API keys, credentials, bot tokens

## Supabase (Self-Hosted)

- Location: `gdrive:backups/supabase/`
- Managed by: `scripts/backup_supabase_to_gdrive.sh` (runs every 6h via cron)

## Videos

- Location: `gdrive:videos/christian/` and `gdrive:videos/trading/`
- `christian/`: FaithNexus scripture videos (one file per scripture, best version only)
- `trading/`: XAUUSD/crypto trading signals (one file per topic, proper name)
- No duplicate copies — new videos replace or are added alongside existing ones

## YouTube / Google OAuth2

- Client ID: `692330360777-jhp2f09mb6opjoempdd696fmaq4i75kv.apps.googleusercontent.com`
- Authorized redirect URI: `http://localhost:4200/oauth2/callback/youtube`
- Postiz redirect URI: `http://localhost:4200/oauth2/callback`
- These are set in `.env` as `YOUTUBE_CLIENT_ID`, `YOUTUBE_REDIRECT_URI`, `POSTIZ_REDIRECT_URI`

## GDrive Structure

```
gdrive:
├── backups/
│   ├── env/
│   │   ├── .env
│   │   └── consolidated.env
│   ├── obsidian/          ← single vault backup (sync, not copy)
│   └── supabase/          ← supabase dump
└── videos/
    ├── christian/         ← FaithNexus scripture videos
    └── trading/           ← XAUUSD / crypto signal videos
```
