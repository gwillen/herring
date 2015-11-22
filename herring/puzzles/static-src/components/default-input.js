'use strict';

var React = require('react');

var DefaultInputComponent = React.createClass({
    propTypes: {
        defaultValue: React.PropTypes.string.isRequired,
    },
    getInitialState: function() {
        return {};
    },
    componentDidMount: function () {
        this.setState({
            val: this.props.defaultValue
        });
    },
    render: function(){
        return (
            <input ref="editInput"
                   type="text"
                   value={ this.state.val }
                   onChange={ this.handleChange } />
        );
    },
    handleChange: function(evt){
        this.setState({val: evt.target.value});
    },
});

module.exports = DefaultInputComponent;
