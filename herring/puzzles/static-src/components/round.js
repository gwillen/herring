'use strict';

import React from 'react';
import PuzzleComponent from './puzzle';
import { targetifyRound } from '../utils';
import { isRoundShown, puzzleMatches } from '../puzzle-list';

// One round: its title (click the caret to expand/collapse) and the puzzles
// that pass `listFilter`. Nothing at all if none pass.
export default function RoundComponent({ round, listFilter, roundDisplay, toggleRound, changeMade, settings, uiSettings }) {
    const filteredPuzzles = round.puzzle_set.filter(puzzle => puzzleMatches(puzzle, listFilter));
    if (filteredPuzzles.length <= 0) {
        return <div className="row"></div>;
    }
    const shown = isRoundShown(round, roundDisplay);
    const contentsStyle = shown ? {} : { display: 'none' };
    return (
        <div className="row">
            <div className="col-lg-12 round">
              <RoundTitle round={ round } shown={ shown } toggle={ () => toggleRound(round) } />
              <div className="col-lg-12" style={ contentsStyle }>
                <Legend settings={ settings } />
              </div>
              <div style={ contentsStyle }>
                { filteredPuzzles.map(puzzle =>
                    <PuzzleComponent key={ puzzle.id }
                                     puzzle={ puzzle }
                                     changeMade={ changeMade }
                                     settings={ settings }
                                     uiSettings={ uiSettings } />) }
              </div>
            </div>
        </div>
    );
}

function RoundTitle({ round, shown, toggle }) {
    const name = `R${round.number} ${round.name}`;
    const caret = (
        <button onClick={ evt => { evt.preventDefault(); toggle(); } }>
            { shown ? 'v' : '^' }
        </button>
    );
    return (
        <h2 id={ targetifyRound(round) }>
            { round.hunt_url ? <a href={ round.hunt_url }>{ name }</a> : name } { caret }
        </h2>
    );
}

function Legend({ settings }) {
    return (
        <div className="row legend">
          <div className="col-xs-6 col-sm-6 col-md-4 col-lg-3">
            <span className="missing-button" />
            { settings.discord && <span className="messaging-spacer" /> }
            { settings.gapps && <span className="messaging-spacer" /> }
            <span className="name-legend">
              Name
            </span>
          </div>
          <div className="col-xs-6 col-sm-3 col-md-3 col-lg-2">Answer</div>
          <div className="visible-md visible-lg col-md-3 col-lg-3">Notes</div>
          <div className="hidden-xs col-sm-3 col-md-2 col-lg-2">Tags</div>
          <div className="visible-lg-block col-lg-2">Activity</div>
        </div>
    );
}
