'use strict';

import React from 'react';

export default class Modal extends React.Component {
    modalBox = React.createRef();
    componentDidMount() {
        document.addEventListener('keydown', this.handleKeyDown);
    }
    componentWillUnmount() {
        document.removeEventListener('keydown', this.handleKeyDown);
    }
    render() {
        return (
            <div className="modal"
                 onClick={ this.handleWrapperClick }>
                <div ref={ this.modalBox }>
                    <button className="close-button"
                            onClick={ this.props.closeCallback }>x</button>
                    { this.props.children }
                </div>
            </div>
        );
    }
    handleKeyDown = evt => {
        if (evt.key === 'Escape') {
            this.props.closeCallback();
        }
    };
    handleWrapperClick = evt => {
        var modal = this.modalBox.current;
        if (modal && !modal.contains(evt.target)) {
            this.props.closeCallback();
        }
    };
}
