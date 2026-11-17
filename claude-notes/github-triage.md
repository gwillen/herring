# GitHub issues and PRs triage (2026-11-17)

All 55 open issues and 7 open PRs on gwillen/herring, read in full 2026-11-17 and checked against the code where noted. Re-check before acting; things change.

## Quick fixes (small, few interactions)

- #102 Escape Markdown in puzzle names in Discord posts (`discord.utils.escape_markdown`; tasks.py announcements, discordbot.py welcome messages).
- #73 Remember the "Unsolved" filter (add to uiSettings, like app_links).
- #34 + PR #95 Rounds: remember collapse state per round; expand a round when puzzles are added (new/empty rounds currently start collapsed and stay collapsed). PR #95 (dgulotta) fixes the latter; its bundle.js conflicts, so redo it on current code.
- #104 One click to open puzzle page + Discord + sheet. Browsers usually allow one `window.open` per click; more need a popup permission.
- #88 Real Google Sheets links in the web UI (sheet_id isn't in the puzzle JSON yet; keep `/s/<id>` for channel topics and the no-sheet page).
- #93 Show counts of puzzles open/solved (metas separately, per round).
- #69 Make the activity column discoverable (hidden below the lg breakpoint).
- #67 Compact mode (CSS in the issue) as a UI setting.
- #40 Favicon (a small red fish).
- #97 / PR #97 Hardcoded team name: header still says "Rage Against the Dying of the Warehouse", menu has a team phone number and "Team room (2020): 3-442". PR #97 references `settings.HERRING_TEAM_NAME`, which nothing defines, and predates site_settings. Better: team name (and menu extras) as dashboard settings.
- #41 `hb!who`: hide solved puzzles.
- #103 Quick filters (e.g. "stuck", "locked") over tags; the status-field version belongs to the redesign.
- #100 React ✋ to join on more messages (e.g. note updates, any message mentioning a puzzle channel).
- #98 Update the Discord topic when the puzzle link changes (topic-edit code exists; Discord allows ~2 topic edits per 10 min per channel).

## Redesign input (schema / architecture; see roadmap.md)

Already covered by roadmap.md: rename/move/delete safely with ID-based channels (#36, #39, #42, #25, #82 comments), drafts and scraper-fed entry (#89; also suggests a prefilled-entry link as a lighter option), more document types per puzzle (#51), solve timestamps (#92, also unlock/entry time and graphs).

New requirements from the issues:
- Puzzle kinds/flags: backsolve (#37); placeholder for a not-yet-unlocked puzzle, later merged/moved (#38); "not a puzzle" entries with channel+sheet that take no answer and don't block round auto-collapse (#50); objects with no name/round yet, e.g. physical items (#82); auto-create a placeholder meta per round (#82).
- Answers: several answers per puzzle, expected count inherited from round, not "solved" until all are in; record guesses (#84). One title with several copies/URLs, each with its own answer (#85).
- Status: puzzle status field (new / progress / stuck / ...) (#74); per-person puzzle status ("looked at", "working on", "done with") and czar update tools (#75); priority settable by the czar, sort by priority/activity (#43); hints available flag and hint-request tracking (#86); filters on all of these, with the set of statuses editable live (#103).
- Rounds as puzzle-like objects: notes, sheet, chat (#43). Meta-feeding relationships and a group-by-meta view; collapse modes (all / keep metas / keep unsolved) (#43).
- Activity/presence: one model of "who is working on what" (channel members, voice, recent typing, sheet edits), shown centrally (#52, #41, #70).
- Robustness: bulk creation lost sheets and channels (#24); sheet creation failure left no channel either, needs a known state and manual retry, and careful rate-limit handling, not blind retries (#65); out-of-channels handling (#44); archive a solved puzzle, kicking members without deleting (#83). Voice-channel issues (#68, #70, #28) are moot while per-puzzle voice is off.
- Per-user data: keyword subscriptions (#101, PR #81; PR adds UserProfile.subscriptions, its migrations 0016/0017 conflict with current ones), role schedules (#45), signups for events/interactions (#48), self-assignable roles e.g. "MIT/Boston knowledge" (#22; Discord onboarding prompts may cover it).
- Bot process management (#32, #47): partly addressed in Oct 2026 (Discord log channel gone, LazyAnnouncer, listener heartbeat); the Redis mutex in `check_connection_to_messaging` and `do_in_loop` (20 s timeout vs 10 s mutex) remain.
- Not schema: mirror the hunt site (#46); old "stuff to fix" Google Docs from 2015/2018/2020/2021 (#53) are a possible further requirements source.

## Proposed GitHub updates (none done; each needs the user's OK)

- Close as done: #99, #49, #96 (solve notifications rework, 2026-11-16); #33 (Discord log channel removed, 2026-10); #94 (Procfile.dev `--no-restart-on-command-exit`); #23 (done per Zahariel, 2024).
- Close as obsolete: #16 (README rewritten), #26 (README and dashboard give the invite link); probably #28, #68, #70 (per-puzzle voice channels off).
- PRs: #97 close in favor of a dashboard setting; #95 close once redone (credit dgulotta); #81 keep as reference or close pointing at #101.
- Dependabot #105, #107, #108, #109: superseded by a lock upgrade; Dependabot closes them once master has the versions.
- #53: link this triage, or extract the docs if the user wants.

## Dependabot alerts (24 open, 2026-11-17)

- certifi (critical): bundle trusts emSign roots with compromised intermediate keys; used by requests (Google APIs). Update soon.
- aiohttp (many high/medium): nearly all server-side; Herring uses aiohttp only as a client (discord.py, one ClientSession to Discord). Low practical risk.
- pyasn1 (high): quadratic-time decoding DoS; only parses Google auth material. Low.
- opentelemetry-api (medium): trace header parsing DoS; pulled in by google-api-core, Herring doesn't parse inbound trace headers. Negligible.
- Fixed versions (aiohttp 3.14.4, certifi 2026.10.18, pyasn1 0.6.5, opentelemetry-api 1.45.2) are all past the 14-day `exclude-newer`; `uv lock --upgrade-package` each, then deploy.
