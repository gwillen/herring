'use strict';

import React from 'react';

// A box in the corner of the page that doesn't block anything else; the
// non-modal counterpart of Modal, taking the same props.
export default function Toast({ closeCallback, children }) {
    return (
        <div className="toast-popup">
            <button className="close-button" onClick={ closeCallback }>x</button>
            { children }
        </div>
    );
}
