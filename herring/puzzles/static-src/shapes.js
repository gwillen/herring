'use strict';

var React = require('react');

var PuzzleShape = React.PropTypes.shape({
  id: React.PropTypes.number.isRequired,
  number: React.PropTypes.number.isRequired,
  answer: React.PropTypes.string.isRequired,
  is_meta: React.PropTypes.bool.isRequired,
  tags: React.PropTypes.string.isRequired,
  name: React.PropTypes.string.isRequired,
  note: React.PropTypes.string.isRequired,
});

var RoundShape = React.PropTypes.shape({
  id: React.PropTypes.number.isRequired,
  number: React.PropTypes.number.isRequired,
  name: React.PropTypes.string.isRequired,
  puzzle_set: React.PropTypes.arrayOf(PuzzleShape).isRequired,
});

module.exports = {PuzzleShape, RoundShape};
