'use strict';

var React = require('react');
var PuzzleComponent = require('./puzzle');
var targetifyRound = require('../utils').targetifyRound;

var RoundComponent = React.createClass({
  render: function() {
    var round = this.props.round;
    var target = targetifyRound(round);
    var puzzles = round.puzzle_set.map(function(puzzle) {
      return <PuzzleComponent key={ puzzle.id }
                              puzzle={ puzzle } />;
    });
    return (
      <div key={round.id} className="row">
        <div className="col-lg-12 round">
          <h2 id={target}>R{round.number} {round.name}</h2>

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
          {puzzles}
        </div>
      </div>
      );
  }
});

module.exports = RoundComponent;
