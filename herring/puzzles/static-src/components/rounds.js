'use strict';

import React from 'react';
import Filters from './filters';
import RoundComponent from './round';
import SolveSettings from './solve-settings';
import TagFilters from './tag-filters';
import { toggleRoundShown } from '../puzzle-list';

// The filter and settings bars, then every round. The search text lives
// here; the other filters are uiSettings, so they survive a reload.
export default class RoundsComponent extends React.Component {
    state = {
        search: ''
    };
    render() {
        const { rounds, uiSettings, updateUiSetting } = this.props;
        const listFilter = { search: this.state.search, unsolvedOnly: uiSettings.unsolved_only, tag: uiSettings.tag_filter };
        return (
            <div>
                <div className='row'>
                    <div className="col-xs-12">
                        <Filters uiSettings={ uiSettings }
                                 updateSearch={ this.updateSearch }
                                 updateUiSetting={ updateUiSetting } />
                        <TagFilters rounds={ rounds }
                                    selectedTag={ uiSettings.tag_filter }
                                    selectTag={ tag => updateUiSetting('tag_filter', tag) } />
                        <SolveSettings uiSettings={ uiSettings }
                                       updateUiSetting={ updateUiSetting } />
                    </div>
                </div>
                { rounds.length > 0 ? rounds.map(round =>
                    <RoundComponent key={ round.id }
                                    round={ round }
                                    listFilter={ listFilter }
                                    roundDisplay={ uiSettings.round_display }
                                    toggleRound={ this.toggleRound }
                                    changeMade={ this.props.changeMade }
                                    settings={ this.props.settings }
                                    uiSettings={ uiSettings } />)
                  : <p>No puzzles are available</p> }
            </div>
        );
    }
    updateSearch = search => {
        this.setState({ search });
    };
    toggleRound = round => {
        this.props.updateUiSetting('round_display', toggleRoundShown(this.props.uiSettings.round_display, round));
    };
}
