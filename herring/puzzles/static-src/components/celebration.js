'use strict';

import React from 'react';
import { classNames } from '../utils';
import { summarizeEntries } from '../solve-tracking';
import Modal from './utils/modal';
import Toast from './utils/toast';

const FRAMES = { modal: Modal, toast: Toast };

function SolvedPuzzle({ puzzle, round }) {
    return (
        <div className={ classNames({ 'solved-puzzle': true, 'meta': puzzle.is_meta }) }>
            <h1>
                { puzzle.is_meta && <span className="meta-label">META</span> }
                { puzzle.name } SOLVED!!!
            </h1>
            <p>in round { round.number }: { round.name }</p>
            <h2>Answer: <span className="answer">{ puzzle.answer }</span></h2>
        </div>
    );
}

// One popup listing every solve not yet dismissed. `entries` are
// {puzzleId, seenAt}; `index` maps puzzle ids to their current {puzzle, round},
// so answer changes show up here as they're polled.
export default function Celebration({ entries, index, popupStyle, onDismiss }) {
    const [showAll, setShowAll] = React.useState(false);
    const { listed, hiddenCount } = summarizeEntries({ entries, index, showAll });
    const Frame = FRAMES[popupStyle];
    return (
        <Frame closeCallback={ onDismiss }>
            <div className="celebration">
                <div className="solved-list">
                    { listed.map(entry =>
                        <SolvedPuzzle key={ entry.puzzleId } { ...index.get(entry.puzzleId) } />) }
                </div>
                { hiddenCount > 0 &&
                    <button className="show-all" onClick={ () => setShowAll(true) }>
                        …and { hiddenCount } more solved puzzles (show all)
                    </button> }
            </div>
        </Frame>
    );
}
