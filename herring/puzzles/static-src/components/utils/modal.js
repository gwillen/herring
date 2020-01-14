'use strict';

import PropTypes from 'prop-types';
import React from 'react';

export default class Modal extends React.Component {
    modalBox = React.createRef();
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
    handleWrapperClick = evt => {
        var modal = this.modalBox.current;
        if (modal && !modal.contains(evt.target)) {
            this.props.closeCallback();
        }
    };
}

Modal.propTypes = {
    closeCallback: PropTypes.func.isRequired,
};
