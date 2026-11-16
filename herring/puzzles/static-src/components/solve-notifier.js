'use strict';

import React from 'react';
import { onStoredChange, loadStored, updateStored } from '../utils';
import {
    ANNOUNCED, DISMISSED, findNewSolves, indexPuzzles, liveEntries, markNotices, pruneNotices,
    updateEntries,
} from '../solve-tracking';
import { announceSolves, closeSolveNotifications } from '../solve-alerts';
import Celebration from './celebration';

// localStorage key for the notices shared between tabs (see solve-tracking.js).
const NOTICES_KEY = 'solveNotices';

function updateNotices(change) {
    return updateStored(NOTICES_KEY, {}, change);
}

// Marks the new solves no tab has announced yet as announced (by this tab),
// and prunes notices for puzzles no longer solved. Returns the updated
// notices and the solves this tab should announce.
function claimAnnouncements(newSolves, index) {
    const current = pruneNotices(loadStored(NOTICES_KEY, {}), index);
    const toAnnounce = newSolves.filter(id => !(id in current));
    const notices = updateNotices(() => markNotices(current, toAnnounce, ANNOUNCED));
    return { notices, toAnnounce };
}

// Watches each poll of the puzzle data for new solves. The first tab to see a
// solve plays the sound and shows the browser notification; every tab lists it
// in one popup until someone dismisses it in any tab. All of this is
// best-effort: two tabs polling at the same moment may both announce a solve.
export default class SolveNotifier extends React.Component {
    state = {
        entries: [],  // {puzzleId, seenAt}: solves in this tab's popup
    };
    componentDidMount() {
        this.stopWatchingNotices = onStoredChange(NOTICES_KEY, this.applySharedNotices);
    }
    componentWillUnmount() {
        this.stopWatchingNotices();
    }
    componentDidUpdate(prevProps) {
        if (prevProps.rounds !== this.props.rounds) {
            this.handlePoll(indexPuzzles(prevProps.rounds), indexPuzzles(this.props.rounds));
        }
    }
    handlePoll(before, index) {
        const newSolves = findNewSolves(before, index);
        const { notices, toAnnounce } = claimAnnouncements(newSolves, index);
        announceSolves(toAnnounce.map(id => index.get(id)), this.props.uiSettings);
        if (newSolves.length > 0) {
            console.info(`Solves seen (puzzle ids): ${newSolves.join(', ')}; announced by this tab: ${toAnnounce.join(', ') || 'none'}`);
        }
        const popupSolves = this.props.uiSettings.solve_popup === 'off' ? [] : newSolves;
        this.setState(({ entries }) => ({
            entries: updateEntries({ entries, newSolves: popupSolves, seenAt: Date.now(), index, notices }),
        }));
    }
    render() {
        const popupStyle = this.props.uiSettings.solve_popup;
        if (this.state.entries.length === 0 || popupStyle === 'off') {
            return null;
        }
        return <Celebration entries={ this.state.entries }
                            index={ indexPuzzles(this.props.rounds) }
                            popupStyle={ popupStyle }
                            onDismiss={ this.dismiss } />;
    }
    // Another tab changed the notices, maybe dismissing solves shown here.
    applySharedNotices = () => {
        const notices = loadStored(NOTICES_KEY, {});
        closeSolveNotifications(Object.keys(notices).filter(id => notices[id] === DISMISSED));
        this.setState(({ entries }) => ({
            entries: liveEntries(entries, indexPuzzles(this.props.rounds), notices),
        }));
    };
    dismiss = () => {
        const puzzleIds = this.state.entries.map(entry => entry.puzzleId);
        updateNotices(notices => markNotices(notices, puzzleIds, DISMISSED));
        closeSolveNotifications(puzzleIds);
        this.setState({ entries: [] });
    };
}
