'use strict';

var React = require('react');
var Shapes = require('../shapes');
var Modal = require('./utils/modal');


var UrlEditor = React.createClass({
    propTypes: {
        puzzle: Shapes.PuzzleShape.isRequired,
        actionCallback: React.PropTypes.func.isRequired,
        closeCallback: React.PropTypes.func.isRequired
    },
    getInitialState() {
        return {
            newUrl: this.props.puzzle.url
        };
    },
    render() {
        return (
            <Modal closeCallback={ this.props.closeCallback }>
                <div className="url-editor">
                    <h3>URL where puzzle { this.props.puzzle.name } is being worked on:</h3>
                    <form onSubmit={ this.handleSubmit }>
                        <input type="url"
                               name="newUrl"
                               value={ this.state.newUrl }
                               onChange={ this.handleChange} />
                        <input type="submit"/>
                    </form>
                </div>
            </Modal>
        );
    },

    handleChange(evt){
        this.setState({
            newUrl: evt.target.value
        });
    },
    handleSubmit(evt) {
        evt.preventDefault();
        if (this.state.newUrl) {
            this.props.actionCallback(this.state.newUrl);
        }
        this.props.closeCallback();
    }
});

module.exports = UrlEditor;
