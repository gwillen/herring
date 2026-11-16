'use strict';

import React from 'react';
import { notificationsSupported, requestNotificationPermission } from '../solve-alerts';

// Why browser notifications won't appear even though the setting is on, if
// we can tell.
function notificationProblem() {
    if (!notificationsSupported()) {
        return '(not available in this browser)';
    }
    if (Notification.permission === 'denied') {
        return '(blocked: allow notifications for this site in your browser settings)';
    }
    return '';
}

// Per-browser choices for what happens when a puzzle is solved; stored in
// uiSettings, so every tab in this browser uses them.
export default function SolveSettings({ uiSettings, updateUiSetting }) {
    const toggleDesktop = () => {
        const wanted = !uiSettings.solve_desktop;
        updateUiSetting('solve_desktop', wanted);
        if (wanted && notificationsSupported() && Notification.permission === 'default') {
            requestNotificationPermission();
        }
    };
    return (
        <div className="filters solve-settings">
            <h4>When a puzzle is solved:</h4>
            <div>
                <label>
                    Popup
                    <select value={ uiSettings.solve_popup }
                            onChange={ evt => updateUiSetting('solve_popup', evt.target.value) }>
                        <option value="modal">in the middle</option>
                        <option value="toast">in the corner</option>
                        <option value="off">off</option>
                    </select>
                </label>
            </div>
            <div>
                <label>
                    <input type="checkbox"
                           checked={ uiSettings.solve_sound }
                           onChange={ () => updateUiSetting('solve_sound', !uiSettings.solve_sound) } />
                    Sound
                </label>
            </div>
            <div>
                <label>
                    <input type="checkbox"
                           checked={ uiSettings.solve_desktop }
                           onChange={ toggleDesktop } />
                    Browser notification { uiSettings.solve_desktop && notificationProblem() }
                </label>
            </div>
        </div>
    );
}
