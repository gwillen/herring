'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var DefaultInputComponent = require('./default-input');


var RoundInfoComponent = React.createClass({
    propTypes: {
        className: React.PropTypes.string,
        val: React.PropTypes.string,
        onSubmit: React.PropTypes.func.isRequired
    },
    getInitialState: function() {
        return {
            newVal: undefined,
            editable: false
        };
    },
    componentDidMount: function () {
        document.addEventListener('click', this.handleDocumentClick);
    },

    componentWillUnmount: function () {
        document.removeEventListener('click', this.handleDocumentClick);
    },
    render: function() {
        var contents;
        if (this.state.editable) {
            contents = (
                <form onSubmit={ this.onSubmit }>
                    <DefaultInputComponent
                        ref="editInput"
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
            <div ref="editableComponent" className={ this.props.className }
                 onClick={ this.editElement } >
                { contents }
            </div>
        );
    },
    handleDocumentClick: function (evt) {
        var self = ReactDOM.findDOMNode(this.refs.editableComponent),
            target = evt.target;
        if (this.state.editable && (!self || !self.contains(target))) {
            this.setState({ editable: false });
        }
    },
    editElement: function() {
        this.setState({
            editable: true
        },this.focus);
    },
    onSubmit: function(evt) {
        evt.preventDefault();
        var newState = {
            editable: false
        };

        // if something's changed, call onSubmit
        if (this.refs.editInput.state.val !== this.props.val) {
            this.props.onSubmit(this.refs.editInput.state.val);
        }
        // else just make it not editable
        this.setState(newState);
    },
    focus: function() {
        ReactDOM.findDOMNode(this.refs.editInput).focus();
    }
});

module.exports = RoundInfoComponent;
