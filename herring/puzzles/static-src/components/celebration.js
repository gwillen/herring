'use strict';

const React = require('react');
const PropTypes = require('prop-types');
const Shapes = require('../shapes');
const Modal = require('./utils/modal');

let n;

class Celebration extends React.Component {
  componentDidMount() {
    if (Notification.permission === 'granted') {
      // If it's okay let's create a notification
      n = new Notification('We solved puzzle ' + this.props.puzzle.name + '!', {
        body: 'In round ' + this.props.roundNumber + ': ' + this.props.roundName +
          '. Answer: ' + this.props.puzzle.answer.toUpperCase(),
        tag: this.props.puzzle.name,
      });
      n.onclick = function (){
        window.focus();
        this.props.closeCallback();
        n.close();
      }.bind(this);
    }
  }

  render() {
    return (
      <Modal closeCallback={ this.handleClose }>
        <div className="celebration">
          <audio src="/static/applause.mp3" autoPlay />
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
  }
};

Celebration.propTypes = {
  puzzle: Shapes.PuzzleShape.isRequired,
  roundName: PropTypes.string,
  roundNumber: PropTypes.number,
  closeCallback: PropTypes.func.isRequired
};

module.exports = Celebration;
