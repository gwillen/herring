'use strict';

const React = require('react');
const PropTypes = require('prop-types');

const Shapes = require('../shapes');
const RoundComponent = require('./round');
const Filters = require('./filters');

class RoundsComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      filter: '',
      showAnswered: true
    };
  }
  render() {
    const { onChange } = this.props;
    const { state } = this;
    const rs = this.props.rounds.map(function(round) {
      return (
        <RoundComponent
          key={ round.id }
          round={ round }
          onChange={ onChange }
          { ...state }
        />
      );
    });
    return (
      <div>
        <div className='row'>
          <div className="col-xs-12">
            <Filters
              updateFulltextFilter={ this.changeFilter }
              updateAnswerFilter={ this.toggleAnswerStatus } />
          </div>
        </div>
        { rs.length > 0 ? rs : <p>No puzzles are available</p> }
      </div>
    );
  }

  changeFilter = (filter) => {
    this.setState({
      filter: filter
    });
  }

  toggleAnswerStatus = () => {
    this.setState({
      showAnswered: !this.state.showAnswered
    });
  }
};

RoundsComponent.propTypes = {
  rounds: PropTypes.arrayOf(Shapes.RoundShape).isRequired,
  onChange: PropTypes.func,
};

module.exports = RoundsComponent;
