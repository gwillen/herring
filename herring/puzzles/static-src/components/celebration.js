'use strict';

var React = require('react');
var Shapes = require('../shapes');
var Modal = require('./utils/modal');


var Celebration = React.createClass({
    propTypes: {
        puzzle: Shapes.PuzzleShape.isRequired,
        roundName: React.PropTypes.string,
        roundNumber: React.PropTypes.number,
        closeCallback: React.PropTypes.func.isRequired
    },
    componentDidMount: function () {
        console.log('YAAAAAAAY we solved a puzzle');
    },
    render: function () {
        return (
            <Modal closeCallback={ this.props.closeCallback }>
                <div className="celebration">
                    <audio src="/static/YannickLemieux-applause.mp3" autoPlay />
                    <h1>{ this.props.puzzle.name } SOLVED!!!</h1>
                    <p>in round { this.props.roundNumber }: { this.props.roundName }</p>
                    <h2>Answer: <span className="answer">{ this.props.puzzle.answer }</span></h2>
                </div>
            </Modal>
        );
    }
});

module.exports = Celebration;
