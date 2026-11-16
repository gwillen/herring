// Unit tests for solve-tracking.js. Run with `pnpm test` (node --test).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    ANNOUNCED, DISMISSED, findNewSolves, indexPuzzles, liveEntries, markNotices, pruneNotices,
    summarizeEntries, updateEntries,
} from './solve-tracking.js';

// answers: {puzzle id: answer}; ids in `metas` are metas.
function data(answers, metas = []) {
    const puzzle_set = Object.entries(answers).map(([id, answer]) =>
        ({ id: Number(id), name: `P${id}`, answer, is_meta: metas.includes(id) }));
    return indexPuzzles([{ id: 1, number: 1, name: 'R1', puzzle_set }]);
}

test('findNewSolves: only unsolved -> solved, among puzzles seen before', () => {
    const before = data({ 1: '', 2: 'A', 3: '', 4: 'B' });
    const after = data({ 1: 'X', 2: 'C', 3: '', 4: '', 5: 'NEW' });
    assert.deepEqual(findNewSolves(before, after), ['1']);
});

test('pruneNotices: keeps only puzzles still solved', () => {
    const index = data({ 1: 'A', 2: '' });
    const notices = { 1: DISMISSED, 2: DISMISSED, 3: ANNOUNCED };
    assert.deepEqual(pruneNotices(notices, index), { 1: DISMISSED });
});

test('markNotices: sets the state for the given puzzles', () => {
    assert.deepEqual(markNotices({ 1: ANNOUNCED }, ['1', '2'], DISMISSED), { 1: DISMISSED, 2: DISMISSED });
});

test('updateEntries: adds new solves once, keeps the original seenAt', () => {
    const index = data({ 1: 'A', 2: 'B' });
    const entries = [{ puzzleId: '1', seenAt: 10 }];
    const result = updateEntries({ entries, newSolves: ['1', '2'], seenAt: 20, index, notices: {} });
    assert.deepEqual(result, [{ puzzleId: '1', seenAt: 10 }, { puzzleId: '2', seenAt: 20 }]);
});

test('liveEntries: drops unsolved and dismissed puzzles', () => {
    const index = data({ 1: 'A', 2: '', 3: 'C' });
    const entries = ['1', '2', '3'].map(puzzleId => ({ puzzleId, seenAt: 0 }));
    const result = liveEntries(entries, index, { 3: DISMISSED, 1: ANNOUNCED });
    assert.deepEqual(result.map(entry => entry.puzzleId), ['1']);
});

function summarize(count, metas, showAll = false) {
    const ids = Array.from({ length: count }, (_, i) => String(i + 1));
    const index = data(Object.fromEntries(ids.map(id => [id, 'X'])), metas);
    const entries = ids.map(puzzleId => ({ puzzleId, seenAt: Number(puzzleId) }));
    const { listed, hiddenCount } = summarizeEntries({ entries, index, showAll });
    return { listed: listed.map(entry => entry.puzzleId), hiddenCount };
}

test('summarizeEntries: newest two plus metas, the rest counted', () => {
    assert.deepEqual(summarize(6, ['1']), { listed: ['6', '5', '1'], hiddenCount: 3 });
});

test('summarizeEntries: a single leftover is listed, not hidden', () => {
    assert.deepEqual(summarize(3, []), { listed: ['3', '2', '1'], hiddenCount: 0 });
});

test('summarizeEntries: showAll lists everything', () => {
    assert.deepEqual(summarize(5, [], true), { listed: ['5', '4', '3', '2', '1'], hiddenCount: 0 });
});
