'use strict';

import PropTypes from 'prop-types';
import React from 'react';

export default class Filters extends React.Component {
    searchFilter = React.createRef();
    componentDidMount() {
        this.focus();
    }
    render() {
        return (
            <div className="filters">
                <h4>Filter by:</h4>
                <div>
                    <label>
                        <input type="search"
                               ref={ this.searchFilter }
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
                <div>
                    <label>
                        <input type="checkbox"
                               onChange={ this.props.toggleLinkType } />
                        Use app links
                    </label>
                </div>
            </div>
        );
    }
    updateFilter = evt => {
        this.props.updateFulltextFilter(evt.target.value);
    };
    focus() {
        this.searchFilter.current.focus();
    }
}

Filters.propTypes = {
    updateFulltextFilter: PropTypes.func.isRequired,
    updateAnswerFilter: PropTypes.func.isRequired,
    toggleLinkType: PropTypes.func.isRequired,
};
