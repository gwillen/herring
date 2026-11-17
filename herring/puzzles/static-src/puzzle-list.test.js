// Unit tests for puzzle-list.js. Run with `pnpm test` (node --test).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    isRoundShown, puzzleMatches, puzzleTags, solveCounts, tagChoices, toggleRoundShown,
} from './puzzle-list.js';

const puzzle = (fields) => ({ name: 'P', answer: '', tags: '', is_meta: false, ...fields });
const round = (id, ...puzzles) => ({ id, puzzle_set: puzzles });
const noFilter = { search: '', unsolvedOnly: false, tag: '' };

test('puzzleTags: split on commas, trimmed, lowercase', () => {
    assert.deepEqual(puzzleTags(puzzle({ tags: 'Logic, grid,, ' })), ['logic', 'grid']);
});

test('puzzleMatches: search, unsolved only, tag', () => {
    const p = puzzle({ name: 'Crossword Chaos', tags: 'Wordplay, stuck', answer: 'X' });
    assert.ok(puzzleMatches(p, noFilter));
    assert.ok(puzzleMatches(p, { ...noFilter, search: 'chaos' }));
    assert.ok(puzzleMatches(p, { ...noFilter, search: 'wordp' }));
    assert.ok(!puzzleMatches(p, { ...noFilter, search: 'logic' }));
    assert.ok(!puzzleMatches(p, { ...noFilter, unsolvedOnly: true }));
    assert.ok(puzzleMatches(p, { ...noFilter, tag: 'stuck' }));
    assert.ok(!puzzleMatches(p, { ...noFilter, tag: 'stu' }));
});

test('tagChoices: counts, sorted, keeps the selected tag', () => {
    const rounds = [round(1, puzzle({ tags: 'stuck, grid' }), puzzle({ tags: 'Stuck' })), round(2, puzzle({}))];
    assert.deepEqual(tagChoices(rounds, ''), [['grid', 1], ['stuck', 2]]);
    assert.deepEqual(tagChoices(rounds, 'locked'), [['grid', 1], ['locked', 0], ['stuck', 2]]);
});

test('solveCounts: all puzzles and metas', () => {
    const puzzles = [puzzle({ answer: 'A' }), puzzle({}), puzzle({ is_meta: true }), puzzle({ is_meta: true, answer: 'M' })];
    assert.deepEqual(solveCounts(puzzles), { solved: 2, total: 4, metasSolved: 1, metasTotal: 2 });
});

test('isRoundShown: collapsed when all solved or empty, expanded otherwise', () => {
    assert.equal(isRoundShown(round(1, puzzle({ answer: 'A' })), {}), false);
    assert.equal(isRoundShown(round(1), {}), false);
    assert.equal(isRoundShown(round(1, puzzle({})), {}), true);
});

test('a manual toggle holds until the round becomes (un)solved', () => {
    const solved = round(1, puzzle({ answer: 'A' }));
    const display = toggleRoundShown({}, solved);
    assert.equal(isRoundShown(solved, display), true);
    const withNewPuzzle = round(1, puzzle({ answer: 'A' }), puzzle({}));
    assert.equal(isRoundShown(withNewPuzzle, display), true);  // automatic again: has an unsolved puzzle
    const collapsed = toggleRoundShown({}, withNewPuzzle);
    assert.equal(isRoundShown(withNewPuzzle, collapsed), false);
    assert.equal(isRoundShown(round(1, puzzle({ answer: 'A' }), puzzle({ answer: 'B' })), collapsed), false);
});

test('an empty round expands when its first puzzle is added (PR #95)', () => {
    assert.equal(isRoundShown(round(1, puzzle({})), {}), true);
});
