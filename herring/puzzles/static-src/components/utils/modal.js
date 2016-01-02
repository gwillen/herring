'use strict';

var React = require('react');
var ReactDOM = require('react-dom');


var Modal = React.createClass({
    propTypes: {
        closeCallback: React.PropTypes.func.isRequired
    },
    render: function () {
        return (
            <div className="modal"
                 onClick={ this.handleWrapperClick }>
                <div ref="modalBox">
                    <button className="close-button"
                            onClick={ this.props.closeCallback }>x</button>
                    { this.props.children }
                </div>
            </div>
        );
    },
    handleWrapperClick: function (evt) {
        var modal = ReactDOM.findDOMNode(this.refs.modalBox);
        if (modal && !modal.contains(evt.target)) {
            this.props.closeCallback();
        }
    }
});

module.exports = Modal;
