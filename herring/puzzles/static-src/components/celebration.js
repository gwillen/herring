'use strict';

import PropTypes from 'prop-types';
import React from 'react';
import Modal from './utils/modal';
import { PuzzleShape } from '../shapes';

var n;

export default class Celebration extends React.Component {
    componentDidMount() {
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
    }
    render() {
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
    }
    handleClose = () => {
        if (n) {
            n.close();
        }
        this.props.closeCallback();
    };
}

Celebration.propTypes = {
    puzzle: PuzzleShape.isRequired,
    roundName: PropTypes.string,
    roundNumber: PropTypes.number,
    closeCallback: PropTypes.func.isRequired,
};
