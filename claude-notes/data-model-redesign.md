# Data model / structure redesign (planning; ON HOLD)

Status (2026-10-06): user asked to hold off on design/implementation while they describe more existing problems. Collect requirements here; don't start the refactor until they say so.

## Findings about the current model (verified in code, 2026-10-06)

- Discord channel identity = channel **name** = `Puzzle.slug`, everywhere in `discordbot.py` (joins, reactions, `on_message` activity, `hb!answer`/`tag`/`note`, `who`, `cleanup_channels`, `get_channel_pair`). No channel IDs are stored.
- `Puzzle.slug` is an AutoSlugField fixed at creation, and includes the round prefix (`r4-anagrams`, `r2m-...` for metas), so moving a puzzle between rounds or renaming it leaves slug/channel/category out of sync.
- `ChannelParticipation.channel_puzzle` is a FK to Puzzle with `to_field='slug'` (db column `channel_name`).
- `Round.discord_categories` is a comma-separated string of category IDs (a round can need several categories: 50 channels per category, `PUZZLES_PER_CATEGORY = 20`).
- `Puzzle.sheet_id` holds the Google Sheet; sheet titles include the round prefix at creation and are never updated.
- Each puzzle has exactly one round (`Puzzle.parent` FK).
- `hunt_id` is an int column on Round and Puzzle, defaulting to `settings.HERRING_HUNT_ID` (env `HUNT_ID`); the UI and bot only ever show that one hunt.
- `Puzzle.slack_channel_id` exists and is unused (Slack era).

## Requirements from the user (2026-10-06)

- Puzzles may be in multiple rounds, in no obvious round, or in nested/overlapping rounds; teams change their minds about what's a round vs. a puzzle and need to reassign existing Discord channels and Google Sheets.
- Renaming / moving puzzles must be safe (currently avoided for fear of breaking Discord).
- Drafts: anyone (or automation) can propose puzzles; admins approve. Automated creation of puzzle entries.
- An editing UI better than the Django admin.
- **Hunts:** usually one Discord server per hunt (required for large hunts by channel limits; minor hunts sometimes share). Currently switching hunt/server is a yearly manual change of `HUNT_ID` / `DISCORD_GUILD` config. Want: the bot handles multiple servers at once; probably a "primary hunt" that decides how it answers DMs. Everything must **default to the current active hunt** (many users aren't tech-savvy).
- The site should allow working with old hunts, but it must be hard to do by accident; solving the current hunt stays the simple default path.
- Move configuration from environment variables into in-app admin settings where sensible.
- General cleanup of historical baggage, e.g. the bot predates Discord's modern interaction model (slash commands, components) and is only partly updated.

## Earlier proposal (before the hunt/server requirements; to be revised)

1. Store Discord channel/category IDs and sheet IDs as linked resources; bot looks up by ID, not name.
2. Idempotent "reconcile" task: DB is truth; make Discord/Drive names and categories match. Allow re-linking a channel/sheet to a different puzzle.
3. Puzzle ↔ Round many-to-many (meta-ness on the membership), nested rounds, a primary round for the Discord category.
4. Draft → approved workflow; token-authenticated API for automated drafts.
5. In-app editing UI.

Notes for revision: a Hunt model (owning its Discord guild ID, Drive folder, template sheet, active flag) would replace `HUNT_ID`/`DISCORD_GUILD` env config and fits multi-server. Discord channel/category IDs are globally unique snowflakes, so per-server scoping doesn't affect ID-based lookup, but bot commands need to resolve "which hunt" from the guild a command came from (DMs → primary hunt).
