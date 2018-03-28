'use strict';

const React = require('react');
const PropTypes = require('prop-types');

const DefaultInputComponent = React.createClass({
  propTypes: {
    defaultValue: PropTypes.string.isRequired,
    disabled: PropTypes.bool,
  },

  getInitialState: function() {
    return { val: this.props.defaultValue };
  },

  componentDidMount: function () {
    // focus on mount...
    this.refs.editInput.focus();

    // ...and move cursor to end
    this.refs.editInput.value = '';
    this.refs.editInput.value = this.state.val;
  },

  render: function(){
    return (
      <input
        ref="editInput"
        type="text"
        value={ this.state.val }
        onChange={ this.handleChange }
        disabled={ this.props.disabled }
      />
    );
  },

  handleChange: function(evt){
    this.setState({ val: evt.target.value });
  },
});

module.exports = DefaultInputComponent;
