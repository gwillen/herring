'use strict';

const React = require('react');
const Utils = require('../utils');


const NavHeaderComponent = React.createClass({
  render: function() {
    const roundTags = this.props.rounds.map(function(round) {
      const target = '#' + Utils.targetifyRound(round);
      const key = 'shortcut-' + round.id.toString();
      return (
        <a key={key} href={target}>R{round.number}</a>
      );
    });
    return (
      <div className="row">
        <div className="col-lg-12">
          <div className="shortcuts">
            Hop to: { Utils.interleave(' | ', roundTags) }
          </div>
        </div>
      </div>
    );
  }
});

module.exports = NavHeaderComponent;
