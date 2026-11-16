'use strict';

// The parts of a solve notification that happen once per browser (not once
// per tab): the applause sound and the browser's own notifications.

const APPLAUSE_URL = '/static/YannickLemieux-applause.mp3';

// Browser notifications this tab showed and that are still open, by puzzle id.
const openNotifications = new Map();

// Missing on some mobile browsers, and on plain-http pages other than localhost.
export function notificationsSupported() {
    return 'Notification' in window;
}

function canNotify() {
    return notificationsSupported() && Notification.permission === 'granted';
}

function playApplause() {
    new Audio(APPLAUSE_URL).play()
        .catch(err => console.warn('Could not play the solve sound:', err));
}

function showSolveNotification({ puzzle, round }) {
    const puzzleId = String(puzzle.id);
    try {
        const notification = new Notification(`We solved puzzle ${puzzle.name}!`, {
            body: `In round ${round.number}: ${round.name}. Answer: ${puzzle.answer.toUpperCase()}`,
            tag: `herring-solve-${puzzleId}`,
        });
        notification.onclick = () => { window.focus(); notification.close(); };
        notification.onclose = () => openNotifications.delete(puzzleId);
        openNotifications.set(puzzleId, notification);
    } catch (err) {
        // e.g. Chrome on Android only allows notifications from a service worker.
        console.warn('Could not show a browser notification:', err);
    }
}

// `solves` are {puzzle, round}; one applause covers any number of them.
export function announceSolves(solves, uiSettings) {
    if (uiSettings.solve_sound && solves.length > 0) {
        playApplause();
    }
    if (uiSettings.solve_desktop && canNotify()) {
        solves.forEach(showSolveNotification);
    }
}

export function closeSolveNotifications(puzzleIds) {
    puzzleIds.forEach(id => openNotifications.get(id)?.close());
}

export function requestNotificationPermission() {
    return Notification.requestPermission()
        .then(permission => console.info(`Browser notification permission: ${permission}`))
        .catch(err => console.error('Asking for notification permission failed:', err));
}

// Browsers only show the permission prompt in response to a user action, so
// ask on the first click anywhere, if `isWanted()` says the setting is on then.
export function askNotificationPermissionOnClick(isWanted) {
    if (!notificationsSupported() || Notification.permission !== 'default') {
        return;
    }
    const ask = () => {
        if (isWanted()) {
            document.removeEventListener('click', ask);
            requestNotificationPermission();
        }
    };
    document.addEventListener('click', ask);
}
