'use strict';

const React = require('react');
const ReactDOM = require('react-dom');
const PropTypes = require('prop-types');


const Modal = React.createClass({
  propTypes: {
    closeCallback: PropTypes.func.isRequired
  },

  render: function () {
    return (
      <div 
        className="modal"
        onClick={ this.handleWrapperClick }
      >
        <div ref="modalBox">
          <button
            className="close-button"
            onClick={ this.props.closeCallback }
          >
            x
          </button>
          { this.props.children }
        </div>
      </div>
    );
  },
  
  handleWrapperClick: function (evt) {
    const modal = ReactDOM.findDOMNode(this.refs.modalBox);
    if (modal && !modal.contains(evt.target)) {
      this.props.closeCallback();
    }
  }
});

module.exports = Modal;
