'use strict';

// Pure logic for the puzzle list: filtering, tags, solve counts, and whether
// a round is expanded. No React or browser APIs, so `node --test` can run it.

// Tags as the bot writes them ("logic, grid"), compared case-insensitively.
export function puzzleTags(puzzle) {
    return puzzle.tags.split(',').map(tag => tag.trim().toLowerCase()).filter(Boolean);
}

// `search` matches the name or tags; `tag` (if any) must be one of the tags.
export function puzzleMatches(puzzle, { search, unsolvedOnly, tag }) {
    const text = `${puzzle.tags} ${puzzle.name}`.toLowerCase();
    return (!unsolvedOnly || !puzzle.answer)
        && text.includes(search.toLowerCase())
        && (!tag || puzzleTags(puzzle).includes(tag));
}

// [tag, number of puzzles with it] for every tag in use, alphabetically,
// plus `selectedTag` (with 0) if no puzzle has it any more, so a filter on
// it stays visible.
export function tagChoices(rounds, selectedTag) {
    const counts = new Map();
    rounds.flatMap(round => round.puzzle_set).flatMap(puzzleTags)
        .forEach(tag => counts.set(tag, (counts.get(tag) ?? 0) + 1));
    if (selectedTag && !counts.has(selectedTag)) {
        counts.set(selectedTag, 0);
    }
    return [...counts].sort(([a], [b]) => a.localeCompare(b));
}

export function solveCounts(puzzles) {
    const metas = puzzles.filter(puzzle => puzzle.is_meta);
    const solved = list => list.filter(puzzle => puzzle.answer).length;
    return { solved: solved(puzzles), total: puzzles.length, metasSolved: solved(metas), metasTotal: metas.length };
}

function allSolved(round) {
    return round.puzzle_set.every(puzzle => puzzle.answer);
}

// A round is collapsed when all its puzzles are solved (including when it
// has none yet), unless someone expanded or collapsed it by hand. That choice
// (`roundDisplay[id]`, saved with whether the round was all solved then)
// holds until the round's all-solved state changes, e.g. a puzzle is added.
export function isRoundShown(round, roundDisplay) {
    const saved = roundDisplay[round.id];
    return saved && saved.allSolved === allSolved(round) ? saved.shown : !allSolved(round);
}

export function toggleRoundShown(roundDisplay, round) {
    return { ...roundDisplay, [round.id]: { shown: !isRoundShown(round, roundDisplay), allSolved: allSolved(round) } };
}
