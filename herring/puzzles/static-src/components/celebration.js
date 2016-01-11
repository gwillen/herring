'use strict';

var React = require('react');
var Shapes = require('../shapes');
var Modal = require('./utils/modal');


var n;

var Celebration = React.createClass({
    propTypes: {
        puzzle: Shapes.PuzzleShape.isRequired,
        roundName: React.PropTypes.string,
        roundNumber: React.PropTypes.number,
        closeCallback: React.PropTypes.func.isRequired
    },
    componentDidMount: function () {
        var self = this;
        if (Notification.permission === 'granted') {
            // If it's okay let's create a notification
            n = new Notification('We solved puzzle ' + this.props.puzzle.name + '!', {
                body: 'In round ' + this.props.roundNumber + ': ' + this.props.roundName +
                    '. Answer: ' + this.props.puzzle.answer.toUpperCase(),
                tag: this.props.puzzle.name,
            });
            n.onclick = function (){
                window.focus();
                self.props.closeCallback();
                n.close();
            };
        }
    },
    render: function () {
        return (
            <Modal closeCallback={ this.handleClose }>
                <div className="celebration">
                    <audio src="/static/YannickLemieux-applause.mp3" autoPlay />
                    <h1>{ this.props.puzzle.name } SOLVED!!!</h1>
                    <p>in round { this.props.roundNumber }: { this.props.roundName }</p>
                    <h2>Answer: <span className="answer">{ this.props.puzzle.answer }</span></h2>
                </div>
            </Modal>
        );
    },
    handleClose: function () {
        if (n) {
            n.close();
        }
        this.props.closeCallback();
    }
});

module.exports = Celebration;
