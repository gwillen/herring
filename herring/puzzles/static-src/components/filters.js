'use strict';

var React = require('react');
var ReactDOM = require('react-dom');


var Filters = React.createClass({
    propTypes: {
        updateFulltextFilter: React.PropTypes.func.isRequired,
        updateAnswerFilter: React.PropTypes.func.isRequired
    },
    componentDidMount: function () {
        this.focus();
    },
    render: function() {
        return (
            <div className="filters">
                <h4>Filter by:</h4>
                <div>
                    <label>
                        <input type="search"
                               ref="searchFilter"
                               placeholder="Search..."
                               onChange={ this.updateFilter } />
                        Tag or puzzle name
                    </label>
                </div>
                <div>
                    <label>
                        <input type="checkbox"
                               onChange={ this.props.updateAnswerFilter } />
                        Unsolved
                    </label>
                </div>
            </div>
        );
    },
    updateFilter: function (evt) {
        this.props.updateFulltextFilter(evt.target.value);
    },
    focus: function () {
        ReactDOM.findDOMNode(this.refs.searchFilter).focus();
    }
});

module.exports = Filters;
