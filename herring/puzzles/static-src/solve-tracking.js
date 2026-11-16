'use strict';

// Pure logic for solve notifications (no React, no browser APIs, so it can be
// unit-tested with `node --test`). See components/solve-notifier.js for how
// it's used.
//
// Puzzle ids are strings throughout, so they match the keys of the notices
// object, which round-trips through JSON in localStorage.

// Notices are shared between tabs in localStorage: puzzle id -> one of these.
// A puzzle keeps its notice only while it's solved, so a re-solve after the
// answer was cleared notifies again.
export const ANNOUNCED = 'announced';  // a tab played the sound / showed the browser notification
export const DISMISSED = 'dismissed';  // someone dismissed the popup showing it

// How many of the most recent solves the popup always lists (plus all metas).
export const RECENT_SHOWN = 2;

// Map of puzzle id -> {puzzle, round}, for every puzzle in the polled data.
export function indexPuzzles(rounds) {
    return new Map(rounds.flatMap(round =>
        round.puzzle_set.map(puzzle => [String(puzzle.id), { puzzle, round }])));
}

function isSolved(index, puzzleId) {
    return Boolean(index.get(puzzleId)?.puzzle.answer);
}

// Puzzles unsolved in `before` and solved in `after`. Puzzles that weren't in
// `before` at all don't count: their solve wasn't seen happening.
export function findNewSolves(before, after) {
    return [...after.keys()].filter(id =>
        before.has(id) && !isSolved(before, id) && isSolved(after, id));
}

// Drops notices for puzzles that are no longer solved (or no longer exist).
export function pruneNotices(notices, index) {
    return Object.fromEntries(Object.entries(notices).filter(([id]) => isSolved(index, id)));
}

export function markNotices(notices, puzzleIds, state) {
    return { ...notices, ...Object.fromEntries(puzzleIds.map(id => [id, state])) };
}

// Popup entries ({puzzleId, seenAt}) that should still be shown.
export function liveEntries(entries, index, notices) {
    return entries.filter(entry =>
        isSolved(index, entry.puzzleId) && notices[entry.puzzleId] !== DISMISSED);
}

// Adds new solves (not already listed) to the popup entries, then drops
// entries that are no longer solved or have been dismissed.
export function updateEntries({ entries, newSolves, seenAt, index, notices }) {
    const listed = new Set(entries.map(entry => entry.puzzleId));
    const added = newSolves.filter(id => !listed.has(id)).map(puzzleId => ({ puzzleId, seenAt }));
    return liveEntries([...entries, ...added], index, notices);
}

// Which entries the popup lists, newest first: all metas and the most recent
// few, unless `showAll`. Hiding a single entry saves nothing, so then all are
// listed. Returns the listed entries and how many were left out.
export function summarizeEntries({ entries, index, showAll }) {
    const newestFirst = [...entries].sort((a, b) => b.seenAt - a.seenAt);
    const alwaysListed = (entry, rank) =>
        showAll || rank < RECENT_SHOWN || index.get(entry.puzzleId).puzzle.is_meta;
    const listed = newestFirst.filter(alwaysListed);
    const hiddenCount = newestFirst.length - listed.length;
    return hiddenCount > 1 ? { listed, hiddenCount } : { listed: newestFirst, hiddenCount: 0 };
}
