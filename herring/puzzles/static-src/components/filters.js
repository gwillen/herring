'use strict';

const React = require('react');
const ReactDOM = require('react-dom');
const PropTypes = require('prop-types');


class Filters extends React.Component {
  componentDidMount() {
    this.focus();
	}
	
  render() {
    return (
      <div className="filters">
        <h4>Filter by:</h4>
        <div>
          <label>
						<input 
							type="search"
              ref="searchFilter"
              placeholder="Search..."
              onChange={ (evt) => this.props.updateFulltextFilter(evt.target.value) }
						/>
            Tag or puzzle name
          </label>
        </div>
        <div>
          <label>
						<input 
							type="checkbox"
              onChange={ this.props.updateAnswerFilter }
						/>
            Unsolved
          </label>
        </div>
      </div>
    );
	}
	
  focus = () => {
    ReactDOM.findDOMNode(this.refs.searchFilter).focus();
  }
}

Filters.propTypes = {
	updateFulltextFilter: PropTypes.func.isRequired,
	updateAnswerFilter: PropTypes.func.isRequired
};

module.exports = Filters;
