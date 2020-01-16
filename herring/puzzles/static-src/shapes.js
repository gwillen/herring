'use strict';

import PropTypes from 'prop-types';

export const PuzzleShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  number: PropTypes.number,
  answer: PropTypes.string.isRequired,
  is_meta: PropTypes.bool.isRequired,
  tags: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  note: PropTypes.string.isRequired,
});

export const RoundShape = PropTypes.shape({
  id: PropTypes.number.isRequired,
  number: PropTypes.number,
  name: PropTypes.string.isRequired,
  puzzle_set: PropTypes.arrayOf(PuzzleShape).isRequired,
});
