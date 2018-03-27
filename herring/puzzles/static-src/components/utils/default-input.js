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
