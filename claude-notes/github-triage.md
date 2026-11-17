# GitHub issues and PRs triage (2026-11-17)

All 55 open issues and 7 open PRs on gwillen/herring, read in full 2026-11-17 and checked against the code where noted. Re-check before acting; things change.

## Quick fixes (all done 2026-11-17 on claude-2026-nov, except #104)

Done: #102 escape Markdown/mentions in bot posts; #41 hb!who hides solved; #100 ✋ on update announcements; #98 topic follows link changes (hand-edited topics left alone, link posted instead); #97 team name / hunt site / menu notes as dashboard settings; #73 Unsolved saved; #34 + PR #95 round collapse saved, new puzzles expand a round; #103 tag quick filters (over tags; a status field is redesign); #88 direct sheet links; #93 solve counts; #69 Activity hint and tooltips; #67 compact mode; #40 favicon. Also the security lock upgrade (Dependabot #105/#107/#108/#109).

Left on purpose: #104 (open all links in one click). The user wants to do it separately to check popup blocking across the browsers the team uses.

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

Each fix is on `claude-2026-nov`; the user merges to master. Closing comments should name the commit.
- Close as done (2026-11-16/17 work): #99, #49, #96 (solve notifications); #102, #41, #100, #98, #97, #73, #34, #88, #93, #69, #67, #40 (quick fixes); #103 (tag filters; or keep open for a status field).
- Close as done earlier: #33 (Discord log channel removed, 2026-10); #94 (Procfile.dev `--no-restart-on-command-exit`); #23 (done per Zahariel, 2024).
- Close as obsolete: #16 (README rewritten), #26 (README and dashboard give the invite link); probably #28, #68, #70 (per-puzzle voice channels off).
- PRs: #97 and #95, superseded by the fixes above (credit dgulotta); #81 keep as reference or close pointing at #101.
- Dependabot #105, #107, #108, #109: superseded by the lock upgrade (29f801b); Dependabot closes them once master has the versions.
- #53: link this triage, or extract the docs if the user wants.

## Dependabot alerts (24 open, 2026-11-17)

- certifi (critical): bundle trusts emSign roots with compromised intermediate keys; used by requests (Google APIs). Update soon.
- aiohttp (many high/medium): nearly all server-side; Herring uses aiohttp only as a client (discord.py, one ClientSession to Discord). Low practical risk.
- pyasn1 (high): quadratic-time decoding DoS; only parses Google auth material. Low.
- opentelemetry-api (medium): trace header parsing DoS; pulled in by google-api-core, Herring doesn't parse inbound trace headers. Negligible.
- Fixed versions (aiohttp 3.14.4, certifi 2026.10.18, pyasn1 0.6.5, opentelemetry-api 1.45.2) are all past the 14-day `exclude-newer`; `uv lock --upgrade-package` each, then deploy.
