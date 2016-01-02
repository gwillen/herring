'use strict';

var React = require('react');
var Shapes = require('../shapes');
var RoundComponent = require('./round');
var Filters = require('./filters');
var _ = require('lodash');

var RoundsComponent = React.createClass({
    propTypes: {
        rounds: React.PropTypes.arrayOf(Shapes.RoundShape.isRequired).isRequired,
        changeMade: React.PropTypes.func,
    },
    getInitialState: function () {
        return {
            filter: '',
            showAnswered: true
        };
    },
    changeMade() {
        this.props.changeMade && this.props.changeMade();
    },
    render: function() {
        var self = this;
        var rs = _.map(this.props.rounds, function(round) {
                return (
                    <RoundComponent key={ round.id }
                                    round={ round }
                                    changeMade={ self.changeMade }
                                    { ...self.state } />
                );
            });
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
    },
    changeFilter: function(filter){
        this.setState({
            filter: filter
        });
    },
    toggleAnswerStatus: function(){
        this.setState({
            showAnswered: !this.state.showAnswered
        });
    }
});

module.exports = RoundsComponent;
