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
        showAnswered: React.PropTypes.bool.isRequired
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
        var roundTitle = (<h2 id={target}>R{round.number} {round.name}</h2>);
        if (round.hunt_url) {
            roundTitle = (<a href={ round.hunt_url }>{ roundTitle }</a>);
        }
        return (
            <div key={round.id} className="row">
                <div className="col-lg-12 round">
                  { roundTitle }

                  <div className="col-lg-12">
                    <div className="row legend">
                      <div className="col-xs-6 col-sm-6 col-md-4 col-lg-4">
                        Name
                      </div>
                      <div className="col-xs-6 col-sm-3 col-md-3 col-lg-2">Answer</div>
                      <div className="visible-md visible-lg col-md-3 col-lg-4">Notes</div>
                      <div className="hidden-xs col-sm-3 col-md-2 col-lg-2">Tags</div>
                    </div>
                  </div>
                  { puzzles }
                </div>
            </div>
        );
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
