'use strict';

var React = require('react');
var RoundComponent = require('./round');

var RoundsComponent = React.createClass({
  render: function() {
    var rs = this.props.rounds.map(function(round) {
      return (
        <RoundComponent key={ round.id }
                        round={ round } />
      );
    });
    return (
      <div>{rs.length > 0 ? rs : <p>No puzzles are available</p>}</div>
    );
  }
});

module.exports = RoundsComponent;
