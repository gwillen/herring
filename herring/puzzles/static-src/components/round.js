'use strict';

const React = require('react');
const PropTypes = require('prop-types');
const _ = require('lodash');

const PuzzleComponent = require('./puzzle');
const targetifyRound = require('../utils').targetifyRound;
const Shapes = require('../shapes');

class RoundComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      show: true
    };
  }

  componentDidMount() {
    if (this.allSolved()) {
      this.setState({
        show: false
      });
    }
  }

  componentWillReceiveProps(nextProps) {
    /* If we just solved the last unsolved puzzle in this round, hide the round */
    if (!this.allSolved() && this.allSolved(nextProps.round.puzzle_set)) {
      this.setState({
        show: false
      });
    }
  }

  render() {
    const { round, onChange } = this.props;
    const filteredPuzzles = this.getFilteredPuzzles();
    if (filteredPuzzles.length <= 0 ) {
      return <div key={round.id} className="row"></div>;
    }

    const puzzles = filteredPuzzles.map(function(puzzle) {
      return (
        <PuzzleComponent
          key={ puzzle.id }
          puzzle={ puzzle }
          roundNumber={ round.number }
          roundName={ round.name }
          onChange={ onChange } />
      );
    });

    let contentsStyle = {};
    if (!this.state.show) {
      contentsStyle.display = 'none';
    }

    return (
      <div key={ round.id } className="row">
        <div className="col-lg-12 round">
          { this.getRoundTitle(round) }
          <div className="col-lg-12" style={ contentsStyle }>
          <div className="row legend">
            <div className="col-xs-6 col-sm-6 col-md-4 col-lg-4">Name</div>
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
  }

  getRoundTitle = (round) => {
    const target = targetifyRound(round);
    if (round.hunt_url) {
      return (
        <h2 id={target}>
          <a href={ round.hunt_url }>{`R${ round.number } ${ round.name }`}</a>
          {" "}
          { this.getCaret() }
        </h2>
      );
    } else {
      return (
        <h2 id={target}>
          {`R${ round.number } ${ round.name }`} { this.getCaret() }
        </h2>
      );
    }
  }

  getCaret = () => {
    return (
      <button onClick={ this.onCaretClick }>
        { this.state.show ? 'v' : '^' }
      </button>
    );
  }

  onCaretClick = (evt) => {
    evt.preventDefault();
    this.setState({
      show: !this.state.show || false
    });
  }

  allSolved = (puzzleList) => {
    puzzleList = puzzleList ? puzzleList : this.props.round.puzzle_set;
    return _.filter(puzzleList, function (puzzle) {
      return !puzzle.answer;
    }).length === 0;
  }

  getFilteredPuzzles = () => {
    const filter = this.props.filter || "";

    if (this.props.showAnswered && !filter) {
      return this.props.round.puzzle_set;
    }
    return _.filter(this.props.round.puzzle_set, function(puzzle) {
      const tagsAndName = puzzle.tags.toLowerCase() + ' ' + puzzle.name.toLowerCase();
      return (this.props.showAnswered || !puzzle.answer) &&
        _.contains(tagsAndName, filter.toLowerCase());
    }, this);
  }
};

RoundComponent.propTypes = {
  round: Shapes.RoundShape.isRequired,
  onChange: PropTypes.func,
  filter: PropTypes.string.isRequired,
  showAnswered: PropTypes.bool.isRequired,
};

module.exports = RoundComponent;
