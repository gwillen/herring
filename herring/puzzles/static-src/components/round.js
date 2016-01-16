'use strict';

var React = require('react');
var PuzzleComponent = require('./puzzle');
var targetifyRound = require('../utils').targetifyRound;
var Shapes = require('../shapes');
var _ = require('lodash');

var RoundComponent = React.createClass({
    propTypes: {
        round: Shapes.RoundShape.isRequired,
        changeMade: React.PropTypes.func,
        filter: React.PropTypes.string.isRequired,
        showAnswered: React.PropTypes.bool.isRequired,
    },
    getInitialState: function (){
        return {
            show: true
        };
    },
    componentDidMount: function (){
        if (this.allSolved()) {
            this.setState({
                show: false
            });
        }
    },
    componentWillReceiveProps: function(nextProps) {
        if (!this.allSolved() && this.allSolved(nextProps.round.puzzle_set)) {
            this.setState({
                show: false
            });
        }
    },
    changeMade() {
        this.props.changeMade && this.props.changeMade();
    },
    render: function() {
        var round = this.props.round;
        var target = targetifyRound(round);
        var self = this;
        var filteredPuzzles = this.getFilteredPuzzles();
        if (filteredPuzzles.length <= 0 ) {
            return <div key={round.id} className="row"></div>;
        }
        var puzzles = _.map(filteredPuzzles, function(puzzle) {
            return <PuzzleComponent key={ puzzle.id }
                                    puzzle={ puzzle }
                                    parent={ round }
                                    changeMade={ self.changeMade} />;
        });
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
                      <div className="col-xs-6 col-sm-6 col-md-4 col-lg-4">
                        Name
                      </div>
                      <div className="col-xs-6 col-sm-3 col-md-3 col-lg-2">Answer</div>
                      <div className="visible-md visible-lg col-md-3 col-lg-4">Notes</div>
                      <div className="hidden-xs col-sm-3 col-md-2 col-lg-2">Tags</div>
                    </div>
                  </div>
                  <div style={ contentsStyle }>
                    { puzzles }
                  </div>
                </div>
            </div>
        );
    },
    onCaretClick: function (evt) {
        evt.preventDefault();
        this.setState({
            show: !this.state.show || false
        });
    },
    allSolved: function (puzzleList) {
        puzzleList = puzzleList ? puzzleList : this.props.round.puzzle_set;
        return _.filter(puzzleList, function (puzzle) {
            return !puzzle.answer;
        }).length === 0;
    },

    getFilteredPuzzles: function () {
        return _.filter(this.props.round.puzzle_set, function(puzzle) {
            if (this.props.showAnswered && !this.props.filter) {
                return true;
            }
            var tagsAndName = puzzle.tags.toLowerCase() + ' ' + puzzle.name.toLowerCase();
            return (this.props.showAnswered || !puzzle.answer) &&
                _.contains(tagsAndName, this.props.filter.toLowerCase());
        }, this);
    }
});

module.exports = RoundComponent;
