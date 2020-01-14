'use strict';

import PropTypes from 'prop-types';
import React from 'react';
import Modal from './utils/modal';
import { PuzzleShape } from '../shapes';

export default class UrlEditor extends React.Component {
    state = {
        newUrl: this.props.puzzle.url
    };
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
    }

    handleChange = evt => {
        this.setState({
            newUrl: evt.target.value
        });
    };
    handleSubmit = evt => {
        evt.preventDefault();
        if (this.state.newUrl) {
            this.props.actionCallback(this.state.newUrl);
        }
        this.props.closeCallback();
    };
}

UrlEditor.propTypes = {
    puzzle: PuzzleShape.isRequired,
    actionCallback: PropTypes.func.isRequired,
    closeCallback: PropTypes.func.isRequired
};
