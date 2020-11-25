'use strict';

import PropTypes from 'prop-types';
import React from 'react';
import Filters from './filters';
import RoundComponent from './round';
import { RoundShape } from '../shapes';

export default class RoundsComponent extends React.Component {
    state = {
        filter: '',
        showAnswered: true
    };
    changeMade = () => {
        this.props.changeMade && this.props.changeMade();
    };
    render() {
        var rs = this.props.rounds.map(round =>
                    <RoundComponent key={ round.id }
                                    round={ round }
                                    changeMade={ this.changeMade }
                                    settings={ this.props.settings }
                                    { ...this.state } />);
        return (
            <div>
                <div className='row'>
                    <div className="col-xs-12">
                        <Filters updateFulltextFilter={ this.changeFilter }
                                 updateAnswerFilter={ this.toggleAnswerStatus } />
                    </div>
                </div>
                { rs.length > 0 ? rs : <p>No puzzles are available</p> }
            </div>
        );
    }
    changeFilter = filter => {
        this.setState({
            filter: filter
        });
    };
    toggleAnswerStatus = () => {
        this.setState({
            showAnswered: !this.state.showAnswered
        });
    };
}

RoundsComponent.propTypes = {
    rounds: PropTypes.arrayOf(RoundShape.isRequired).isRequired,
    changeMade: PropTypes.func,
    settings: PropTypes.object
};
