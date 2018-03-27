'use strict';

const React = require('react');
const ReactDOM = require('react-dom');
const PropTypes = require('prop-types');

const DefaultInputComponent = require('./utils/default-input');


class PuzzleInfoComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      newVal: undefined,
      editable: false,
      disabled: false,
    };
  }

  componentDidMount() {
    document.addEventListener('click', this.handleDocumentClick);
  }

  componentWillUnmount() {
    document.removeEventListener('click', this.handleDocumentClick);
  }

  render() {
    let contents;
    if (this.state.editable) {
      contents = (
        <form onSubmit={ this.onSubmit }>
          <DefaultInputComponent
            ref="editInput"
            disabled={ this.state.disabled }
            defaultValue={ this.props.val }/>
        </form>
      );
    } else {
      contents = (
        <span title={ this.props.val }>
          { this.props.val }&nbsp;
        </span>
      );
    }
    return (
      <div 
        ref="editableComponent"
        className={ this.props.className }
        onClick={ this.editElement }
      >
        { contents }
      </div>
    );
  }

  handleDocumentClick = (evt) => {
    const self = ReactDOM.findDOMNode(this.refs.editableComponent),
      target = evt.target;
    if (this.state.editable && (!self || !self.contains(target))) {
      this.setState({ editable: false });
    }
  }

  onSubmit = (evt) => {
    evt.preventDefault();
    const newState = { editable: false };

    const newVal = this.refs.editInput.state.val;
    // if something's changed, call onSubmit
    if (newVal !== this.props.val) {
      this.props.onSubmit(newVal);
    }
    this.setState(newState);
  }

  editElement = () => {
    this.setState(
      { editable: true },
      () => {
        ReactDOM.findDOMNode(this.refs.editInput).focus();
      }
    );
  }
};

PuzzleInfoComponent.propTypes = {
  className: PropTypes.string,
  val: PropTypes.string,
  onSubmit: PropTypes.func.isRequired
};

module.exports = PuzzleInfoComponent;
