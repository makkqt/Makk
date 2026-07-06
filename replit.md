# KURANOMI Key Generator Bot

Telegram bot for generating and managing license keys for the KURANOMI BYPASS tool. Admins generate keys via Telegram; the Python client fetches them from the hosted `/api/keys.txt` endpoint.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server + Telegram bot (port 8080)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` (auto-provisioned), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- Bot: Telegraf 4 (long polling)
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/api-server/src/bot/index.ts` — Telegram bot logic
- `artifacts/api-server/src/routes/keys.ts` — `/api/keys.txt` endpoint
- `lib/db/src/schema/keys.ts` — keys table schema

## Bot Commands

**Admin only:**
- `/genkey <device_id> <duration>` — generate a key (e.g. `/genkey K-ABCD-EFGH 7d`)
- `/listkeys` — list active (non-revoked) keys
- `/listall` — list all keys including revoked
- `/revokekey <key>` — revoke a key

**Everyone:**
- `/start` — show help
- `/checkdevice <device_id>` — check keys for a device

## Duration format

`7d`, `30d`, `1d`, `12h`, `60m` — same as the Python client's `parse_duration`

## Python client integration

Change `RAW_KEY_LINK` in the Python script to point to your deployed URL:
```python
RAW_KEY_LINK = "https://<your-domain>/api/keys.txt"
```

## Architecture decisions

- Keys are stored in PostgreSQL; the `/api/keys.txt` endpoint serves them in the format the Python client expects (`device_id|key|duration_str`)
- Bot uses long polling (no webhook needed) — suitable for development and simple deployments
- Admin check uses `TELEGRAM_ADMIN_CHAT_ID` secret, compared as string to handle leading zeros

## User preferences

_Populate as you build._

## Gotchas

- Always run `pnpm run typecheck:libs` before `pnpm --filter @workspace/api-server run typecheck` if schema changes were made — stale lib declarations cause false TS errors
- MarkdownV2 requires escaping `-`, `.`, `!`, `(`, `)`, etc. — use the `escapeMarkdown()` helper in bot/index.ts
