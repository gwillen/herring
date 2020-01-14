'use strict';

import PropTypes from 'prop-types';
import React from 'react';

export default class RoundInfoComponent extends React.Component {
    state = {
        newVal: undefined,
        editable: false
    };
    editableComponent = React.createRef();
    editInput = React.createRef();
    componentDidMount() {
        document.addEventListener('click', this.handleDocumentClick);
    }

    componentWillUnmount() {
        document.removeEventListener('click', this.handleDocumentClick);
    }
    render() {
        var contents;
        if (this.state.editable) {
            contents = (
                <form onSubmit={ this.onSubmit }>
                    <input
                        ref={ this.editInput }
                        type="text"
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
            <div ref={ this.editableComponent }
                 className={ this.props.className }
                 onClick={ this.editElement } >
                { contents }
            </div>
        );
    }
    handleDocumentClick = evt => {
        var self = this.editableComponent.current,
            target = evt.target;
        if (this.state.editable && (!self || !self.contains(target))) {
            this.setState({ editable: false });
        }
    };
    editElement = () => {
        this.setState({
            editable: true
        },this.focus);
    };
    onSubmit = evt => {
        evt.preventDefault();
        var newState = {
            editable: false
        };

        // if something's changed, call onSubmit
        if (this.editInput.current.value !== this.props.val) {
            this.props.onSubmit(this.editInput.current.value);
        }
        // else just make it not editable
        this.setState(newState);
    };
    focus = () => {
        this.editInput.current.focus();
    };
}

RoundInfoComponent.propTypes = {
    className: PropTypes.string,
    val: PropTypes.string,
    onSubmit: PropTypes.func.isRequired,
};
