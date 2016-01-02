'use strict';

var React = require('react');
var RoundComponent = require('./round');
var Shapes = require('../shapes');

var RoundsComponent = React.createClass({
  propTypes: {
    rounds: React.PropTypes.arrayOf(Shapes.RoundShape.isRequired).isRequired,
    changeMade: React.PropTypes.func,
  },
  changeMade() {
    this.props.changeMade && this.props.changeMade();
  },
  render: function() {
    var self = this;
    var rs = this.props.rounds.map(function(round) {
      return (
        <RoundComponent key={ round.id }
                        round={ round }
                        changeMade={ self.changeMade }/>
      );
    });
    return (
      <div>{rs.length > 0 ? rs : <p>No puzzles are available</p>}</div>
    );
  }
});

module.exports = RoundsComponent;
