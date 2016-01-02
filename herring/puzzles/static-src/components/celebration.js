'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var Shapes = require('../shapes');


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
            <div className="celebration"
                 onClick={ this.handleWrapperClick }>
                <div ref="celebrationModal">
                    <audio src="/static/YannickLemieux-applause.mp3" autoPlay />
                    <button className="close-button"
                            onClick={ this.props.closeCallback }>x</button>
                    <h1>{ this.props.puzzle.name } SOLVED!!!</h1>
                    <p>in round { this.props.roundNumber }: { this.props.roundName }</p>
                    <h2>Answer: <span className="answer">{ this.props.puzzle.answer }</span></h2>
                </div>
            </div>
        );
    },
    handleWrapperClick: function (evt) {
        var modal = ReactDOM.findDOMNode(this.refs.celebrationModal);
        if (modal && !modal.contains(evt.target)) {
            this.props.closeCallback();
        }
    }
});

module.exports = Celebration;
