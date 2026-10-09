# Roadmap: data model redesign and admin features (planning; ON HOLD)

Status (2026-10-06): user asked to hold off on design/implementation while they describe more existing problems. Collect requirements here; don't start until they say so.

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

## More requirements from the user (2026-10-06, second batch)

- **Log in with Discord** (OAuth) to link accounts, instead of typing a Discord username into the profile. User unsure it's worth it.
  - Thought: it would also let us store the Discord *user ID* (stable) instead of a username. The current code splits usernames on `#`, from before Discord dropped discriminators, and usernames can change. Scope `identify` is enough.
- **Discord admin panel in the web app:** channel cleanup; setting up a new hunt's server: roles (copied from last year's server), onboarding, the fixed non-puzzle channels (general/social, copied from last year). Server templates exist but are missing things and awkward.
  - Checked 2026-10-06: Discord's current guild docs no longer list a Create Guild endpoint (bots apparently can't create servers any more), so server creation stays manual. Modify Guild Onboarding (`PUT /guilds/{id}/onboarding`) exists, needs MANAGE_GUILD + MANAGE_ROLES; when enabled, Discord requires ≥7 default channels, ≥5 of them writable by @everyone. Roles, channels, categories and permission overwrites can all be copied via the API ("clone from last hunt's server").
- **Google Drive visibility:** sheets are owned by a service ("bot/role") account in one shared folder. Occasionally things go wrong (an Android Sheets bug once removed sheets from the folder), and there's no web UI for the service account's Drive, only the API. Want: how many objects it owns, whether they're all in the right folder, and where the others are. (Drive API `files.list` on the service account can answer this.)
- **Google Forms and Groups:** each year a Form goes out to find who's on the team; a new Google Group per hunt year gets created, populated from the form results, and given access to the Drive folder. Steps get forgotten. Want automation, or at least one place in the app showing the state of it all.
  - Answered (2026-10-07): they're consumer googlegroups.com groups, which have no public API (as far as known), so group creation and population stay manual, with guidance and status in the app (like Discord server creation). Forms API can read responses; Drive API can share the folder with a group.
- **Bulk operations must be safe and reviewable.** The user is afraid to run `cleanup_channels` (opaque; deleted channels lose their history forever; suspects it has bugs, though it hasn't deleted anything regrettable yet). For cleanup, reconcile, and other bulk Discord/Drive operations, want an admin UI that:
  - builds and shows the list of operations,
  - lets an admin select some or all,
  - **performs exactly what was previewed** (not dry-run-then-recompute, which is how `cleanup_channels` works now).
  - Caveat from the user: operations don't necessarily commute or work independently; handle ordering/dependencies.
  - Design thoughts: store a plan as DB rows (op, target IDs, preconditions captured at planning time, e.g. channel's last_message_id); applying an op re-checks its preconditions and refuses if the world changed (stale plan); ops declare dependencies (e.g. create category before moving channels into it), selecting an op pulls in its dependencies, execution in dependency order; every applied op goes into an audit log. Prefer archiving (move to an archive category, read-only, after exporting history) over deleting.
- **Log Discord activity:** the bot records messages and other events (edits, deletions, channel changes) to the database, as protection if anything goes wrong on Discord, and so recent chat could be shown lightly on the site.
  - Thoughts: needs the Message Content intent (already used); history of existing channels can be backfilled; attachment URLs are signed and expire, so keeping attachments means downloading them; team members should be told messages are logged. Size is likely modest (order of 100k messages per hunt), but Heroku Essential-0's 1 GB cap would matter. Pairs with "archive before delete" above.

## More notes from the user (2026-10-07)

- Per-puzzle voice channels are no longer created (CREATE_DISCORD_VOICE_CHANNELS off); the team uses a few fixed, pre-created voice channels. Voice-channel issues in cleanup are moot unless that changes.
- Settings like the announcements/debug channel names (env `DISCORD_ANNOUNCEMENTS` / `DISCORD_DEBUG_CHANNEL`, which must exist in the server) should be configurable in the web UI, should **fail gracefully** if missing, and an admin area should **show configuration problems** as notices.

## More notes from the user (2026-10-08)

- **Puzzle resources beyond Sheets:** let people request a Google Doc or Drawing (etc.) for a puzzle, optionally making it the puzzle's "main" document (the sheet stays available). Implies a list of resources per puzzle (type, external ID, which is main), channel topics regenerated when the set changes (topic edits are rate-limited by Discord: about 2 per 10 minutes per channel), and multiple icons per puzzle in the web UI. Today the topic always links `/s/<puzzle id>`, which explains when there's no sheet.

## Slash command registration (researched 2026-10-08)

- Discord docs: 200 application command *creates* per day per guild; bulk overwrite only counts commands that don't already exist, so re-syncing an unchanged set is cheap. Guild commands update instantly; global commands work in every server the bot is in, and in DMs (with a mutual server); guild commands don't work in DMs. The same name can exist both globally and per guild (risk of duplicates).
- What was going on (2026-10-08, verified in discord.py 2.7 source): `add_cog(cog, guilds=[...])` only scopes the cog's *pure* `app_commands` (`__cog_app_commands__`); hybrid commands are registered by `Bot.add_command`, which calls `tree.add_command(command.app_command)` with no guild, so they're always global unless the command itself has guild_ids. Hence `/join` (pure app command) was per-server and every other slash command global, despite `GUILD_COMMANDS_FOR_TESTING = True`. The user also saw global changes take effect immediately on sync; current Discord docs no longer state a propagation delay for global commands.
- **Done (2026-10-08):** all slash commands global (`GUILD_COMMANDS_FOR_TESTING` removed); `/join` looks the member up in the hunt's server, so it works from DMs; channel-specific commands (answer, tag, untag, note, leave, part) marked `commands.guild_only()` so they don't appear in DMs; `sync_app_commands` runs from the listener's `setup_hook`, syncing only when the fingerprint (sha256 of the tree's `to_dict` payloads) differs from the one in Redis (`herring:app-commands-fingerprint:<application id>`), and also clears `DISCORD_GUILD`'s per-server commands (the old per-server `/join`); `/synctree` forces it, administrators only, server-only. Verified live: first start synced 12 global commands and left none per-server; later restarts logged "unchanged; not syncing".
- Still to do with the multi-server redesign: clearing leftover per-server commands only covers `DISCORD_GUILD`.

## Review of `cleanup_channels` (discordbot.py, 2026-10-07)

How it works: owner-only `hb!cleanup_channels`; DM menu of modes (Full Rebuild / Create and Fix Only / Fix Only / Dry Run). Snapshots the current hunt's rounds and puzzles once, then:

1. Deletes channels in every non-protected category that aren't named after a current-hunt puzzle slug, are named like `r<digits>-`, and have no `last_message_id`.
2. For each round, creates missing categories (20 puzzles per category).
3. Moves the round's metas to "no category", moves or creates each puzzle's channels by its position in the sorted list, fixes topics, then moves the metas back.

Why nothing regrettable has been lost: only channels with **no messages** are ever deleted, so chat history can't be. Membership (per-member permission overwrites) can be.

Problems found:
- **Confirmed by running it with mocked Discord objects:** "Dry Run" and "Fix Only" crash with `AttributeError: 'NoneType' object has no attribute 'id'` whenever a round has no category or needs another one (a placeholder `None` category reaches `",".join(str(category.id) ...)`). So dry run fails in exactly the interesting case. In Fix Only, rounds processed before the crash have already been changed.
- **Race with puzzle creation:** the puzzle snapshot is taken once, and the deletion pass is slow (it sends one DM per channel considered, and DMs are rate-limited). A puzzle created during a hunt in that window gets its brand-new, empty channel deleted.
- **Scope:** deletion covers every unprotected category in the guild, judged only against the *configured* `HUNT_ID`. With a wrong `HUNT_ID`, or a server shared by two hunts, every empty `r<n>-` channel of the other hunt is deleted. In create mode, categories and channels for the configured hunt are created in whatever guild `DISCORD_GUILD` points at.
- **Name-based identity everywhere:** `_make_category_inner` reuses any category with the same name (could belong to another round or hunt); `get_channel_pair` takes the first channel with that name anywhere in the guild; duplicates are never noticed.
- **"Empty" means only `last_message_id is None`:** voice channels are effectively always "empty"; a text channel people joined but haven't typed in loses its membership when deleted.
- **Churn:** in fix modes, metas are moved out to "no category" and back on *every* run, even when already correct. If the run aborts in between, they're left uncategorized. They can also end up at the bottom of the category instead of the top. Category assignment comes from a puzzle's index in the sorted round, so adding or renumbering one puzzle can shift every later puzzle across a 20-puzzle category boundary, causing mass moves.
- **No error handling:** any Discord API error (permissions, a full category at 50 channels, network) aborts mid-run with partial changes; there's no record of what was done.
- **Noise:** one DM per non-puzzle channel in unprotected categories ("Skipping ..."), every run.
- Meta slugs (`r2m-...`) don't match `r\d+-`, so meta channels are never deletion candidates (inconsistent, but the safe direction).

Implications for the replacement (plan/apply design above): identify channels by stored ID; scope every operation to a hunt and its guild; compute category placement stably (don't renumber everything); no meta shuffle; plan-time preconditions (e.g. `last_message_id`, member overwrites, "created before the plan") checked at apply time; never delete, archive; per-op error handling, continuing or stopping by dependency; audit log.

## Earlier proposal (before the hunt/server requirements; to be revised)

1. Store Discord channel/category IDs and sheet IDs as linked resources; bot looks up by ID, not name.
2. Idempotent "reconcile" task: DB is truth; make Discord/Drive names and categories match. Allow re-linking a channel/sheet to a different puzzle.
3. Puzzle ↔ Round many-to-many (meta-ness on the membership), nested rounds, a primary round for the Discord category.
4. Draft → approved workflow; token-authenticated API for automated drafts.
5. In-app editing UI.

Notes for revision: a Hunt model (owning its Discord guild ID, Drive folder, template sheet, active flag) would replace `HUNT_ID`/`DISCORD_GUILD` env config and fits multi-server. Discord channel/category IDs are globally unique snowflakes, so per-server scoping doesn't affect ID-based lookup, but bot commands need to resolve "which hunt" from the guild a command came from (DMs → primary hunt).
