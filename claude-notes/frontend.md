# Frontend (React, `herring/puzzles/static-src`)

## UI settings

- `uiSettings` in localStorage (same key/format as the old store.js): `app_links`, `solve_popup` ('modal' | 'toast' | 'off'), `solve_sound`, `solve_desktop`. Defaults in `app.js` `DEFAULT_UI_SETTINGS`, merged under stored values. Per browser, not per user.
- Saved only when they change, and every tab reloads them on the `storage` event. Before 2026-11-16 each tab saved its copy on every poll, so a stale tab overwrote another tab's change within 10 s.

## Solve notifications (rebuilt 2026-11-16)

Files: `solve-tracking.js` (pure logic, unit-tested by `solve-tracking.test.js` via `pnpm test`), `solve-alerts.js` (sound, browser notifications, permission), `components/solve-notifier.js` (wiring, popup state), `components/celebration.js` (popup contents), `components/solve-settings.js` (settings bar), `components/utils/toast.js` (corner frame, parallel to `modal.js`).

- Detection is in one place: `SolveNotifier` compares consecutive polls of all puzzles (unsolved → solved, puzzle present in both). It used to be per `PuzzleComponent`, which missed solves of filtered-out puzzles and rendered the popup inside a round that had just auto-collapsed (all puzzles solved), so meta solves often showed no popup.
- localStorage `solveNotices`: puzzle id → 'announced' | 'dismissed', shared by tabs. The first tab to see a solve marks it announced and plays the sound (once per poll, whatever the number of solves) and shows the browser notification (tag `herring-solve-<id>`). Dismissing marks every listed solve dismissed; other tabs drop them on the storage event and close their browser notifications. Each poll prunes notices for puzzles no longer solved.
- Popup entries are `{puzzleId, seenAt}`; the contents are looked up in the current poll data, so answer changes update the open popup.
- Summary: newest `RECENT_SHOWN` (2) plus all metas; the rest behind "…and N more (show all)", unless only one would be hidden. Esc or clicking outside dismisses the modal.
- **User decisions (2026-11-16):** all features on by default (easier to get people to turn things off than to discover them); default popup style stays the modal (toast available); answer change A → B updates an open popup but doesn't re-show a dismissed one; unsolve then re-solve notifies again; your own solves notify like anyone else's; cross-tab dismissal wanted; races between tabs don't matter (best-effort, so no Web Locks). `solved_at` on the server is deferred to the redesign (roadmap.md).
- Ordering uses the time the tab noticed the solve; solves seen in the same poll are tied and keep data order.
- `Notification` is missing on some mobile browsers and on non-localhost http; Android Chrome throws from `new Notification` (needs a service worker). Both are handled (setting shows why; error logged as a warning).

## Tests

- `pnpm test` (in static-src): `node --test`, pure modules only (no JSX/browser APIs).
- `scripts/ui-test.sh` / `scripts/ui/browse.py`: two tabs in one browser context; stubs `HTMLMediaElement.play` to count applause plays; sets answers through the API to simulate teammates; checks one sound across tabs, cross-tab dismissal, one popup for many solves, summary and show-all, answer correction, Esc, settings reaching other tabs, re-solve as toast. Polls take up to 10 s, so it waits up to 15 s per step.
