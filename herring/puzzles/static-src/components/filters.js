'use strict';

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
                               checked={ this.props.uiSettings.app_links }
                               onChange={ this.toggleLinkType } />
                        Use app links
                    </label>
                </div>
            </div>
        );
    }
    updateFilter = evt => {
        this.props.updateFulltextFilter(evt.target.value);
    };
    toggleLinkType = () => {
        this.props.updateUiSetting('app_links', !this.props.uiSettings.app_links);
    };
    focus() {
        this.searchFilter.current.focus();
    }
}
