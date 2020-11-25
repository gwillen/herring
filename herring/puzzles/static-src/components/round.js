'use strict';

import PropTypes from 'prop-types';
import React from 'react';
import PuzzleComponent from './puzzle';
import { RoundShape } from '../shapes';
import { targetifyRound } from '../utils';

export default class RoundComponent extends React.Component {
    state = {
        show: true
    };
    componentDidMount() {
        if (this.allSolved()) {
            this.setState({
                show: false
            });
        }
    }
    componentDidUpdate(prevProps) {
        if (!this.allSolved(prevProps.round.puzzle_set) && this.allSolved()) {
            this.setState({
                show: false
            });
        }
    }
    changeMade = () => {
        this.props.changeMade && this.props.changeMade();
    };
    render() {
        var round = this.props.round;
        var target = targetifyRound(round);
        var filteredPuzzles = this.getFilteredPuzzles();
        if (filteredPuzzles.length <= 0 ) {
            return <div key={round.id} className="row"></div>;
        }
        var puzzles = filteredPuzzles.map(puzzle =>
            <PuzzleComponent key={ puzzle.id }
                             puzzle={ puzzle }
                             parent={ round }
                             changeMade={ this.changeMade } />);
        var caret = (
            <button onClick={ this.onCaretClick }>
                { this.state.show ? 'v' : '^' }
            </button>
        );
        var roundTitle = (<h2 id={target}>R{ round.number } { round.name } { caret }</h2>);
        if (round.hunt_url) {
            roundTitle = (<h2 id={target}><a href={ round.hunt_url }>R{ round.number } { round.name }</a> { caret }</h2>);
        }
        var contentsStyle = {};
        if (!this.state.show) {
            contentsStyle.display = 'none';
        }
        return (
            <div key={ round.id } className="row">
                <div className="col-lg-12 round">
                  { roundTitle }
                  <div className="col-lg-12" style={ contentsStyle }>
                    <div className="row legend">
                      <div className="col-xs-6 col-sm-6 col-md-4 col-lg-3">
                        <span style={{marginRight: '6.5em'}} />
                        Name
                      </div>
                      <div className="col-xs-6 col-sm-3 col-md-3 col-lg-2">Answer</div>
                      <div className="visible-md visible-lg col-md-3 col-lg-3">Notes</div>
                      <div className="hidden-xs col-sm-3 col-md-2 col-lg-2">Tags</div>
                      <div className="visible-lg-block col-lg-2">Activity</div>
                    </div>
                  </div>
                  <div style={ contentsStyle }>
                    { puzzles }
                  </div>
                </div>
            </div>
        );
    }
    onCaretClick = evt => {
        evt.preventDefault();
        this.setState({
            show: !this.state.show || false
        });
    };
    allSolved(puzzleList) {
        puzzleList = puzzleList ? puzzleList : this.props.round.puzzle_set;
        return puzzleList.every(puzzle => puzzle.answer);
    }

    getFilteredPuzzles() {
        return this.props.round.puzzle_set.filter(puzzle => {
            if (this.props.showAnswered && !this.props.filter) {
                return true;
            }
            var tagsAndName = puzzle.tags.toLowerCase() + ' ' + puzzle.name.toLowerCase();
            return (this.props.showAnswered || !puzzle.answer) &&
                tagsAndName.indexOf(this.props.filter.toLowerCase()) >= 0;
        });
    }
}

RoundComponent.propTypes = {
    round: RoundShape.isRequired,
    changeMade: PropTypes.func,
    filter: PropTypes.string.isRequired,
    showAnswered: PropTypes.bool.isRequired,
};
