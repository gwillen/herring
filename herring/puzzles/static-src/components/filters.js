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
                               onChange={ this.updateSearch } />
                        Tag or puzzle name
                    </label>
                </div>
                <div>
                    <label>
                        <input type="checkbox"
                               checked={ this.props.uiSettings.unsolved_only }
                               onChange={ this.toggleUnsolvedOnly } />
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
    updateSearch = evt => {
        this.props.updateSearch(evt.target.value);
    };
    toggleUnsolvedOnly = () => {
        this.props.updateUiSetting('unsolved_only', !this.props.uiSettings.unsolved_only);
    };
    toggleLinkType = () => {
        this.props.updateUiSetting('app_links', !this.props.uiSettings.app_links);
    };
    focus() {
        this.searchFilter.current.focus();
    }
}
