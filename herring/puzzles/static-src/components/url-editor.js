'use strict';

const React = require('react');
const PropTypes = require('prop-types');
const Shapes = require('../shapes');
const Modal = require('./utils/modal');


class UrlEditor extends React.Component {
  constructor(props) {
    super(props);
    this.state = { newUrl: this.props.puzzle.url };
  }

  render() {
    return (
      <Modal closeCallback={ this.props.closeCallback }>
        <div className="url-editor">
          <h3>URL where puzzle { this.props.puzzle.name } is being worked on:</h3>
          <form onSubmit={ this.handleSubmit }>
            <input
              type="url"
              name="newUrl"
              value={ this.state.newUrl }
              onChange={ this.handleChange}
            />
            <input type="submit"/>
          </form>
        </div>
      </Modal>
    );
  }

  handleChange = (evt) => {
    this.setState({
      newUrl: evt.target.value
    });
  }

  handleSubmit = (evt) => {
    evt.preventDefault();
    if (this.state.newUrl) {
      this.props.actionCallback(this.state.newUrl);
    }
    this.props.closeCallback();
  }
};

UrlEditor.propTypes = {
  puzzle: Shapes.PuzzleShape.isRequired,
  actionCallback: PropTypes.func.isRequired,
  closeCallback: PropTypes.func.isRequired
}

module.exports = UrlEditor;
