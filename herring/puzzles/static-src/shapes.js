'use strict';

const PropTypes = require('prop-types');

const PuzzleShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  number: PropTypes.number,
  answer: PropTypes.string.isRequired,
  is_meta: PropTypes.bool.isRequired,
  tags: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  note: PropTypes.string.isRequired,
});

const RoundShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  number: PropTypes.number,
  name: PropTypes.string.isRequired,
  puzzle_set: PropTypes.arrayOf(PuzzleShape).isRequired,
});

module.exports = {PuzzleShape, RoundShape};
