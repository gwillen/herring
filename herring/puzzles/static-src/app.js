'use strict';

import React from 'react';
import { createRoot } from 'react-dom/client';
import { getJson, loadStored, onStoredChange, saveStored } from './utils';
import { askNotificationPermissionOnClick } from './solve-alerts';
import NavHeaderComponent from './components/nav-header';
import RoundsComponent from './components/rounds';
import SolveNotifier from './components/solve-notifier';

// Same localStorage key and format the old store.js library used.
const UI_SETTINGS_KEY = 'uiSettings';
const DEFAULT_UI_SETTINGS = {
  app_links: false,
  solve_popup: 'modal',  // 'modal', 'toast' or 'off'
  solve_sound: true,
  solve_desktop: true,   // browser notifications
};

function loadUiSettings() {
  return {...DEFAULT_UI_SETTINGS, ...loadStored(UI_SETTINGS_KEY, {})};
}

class Page extends React.Component {
  state = {
    uiSettings: loadUiSettings()
  };
  componentDidMount() {
    this.loadDataFromServer();
    setInterval(this.loadDataFromServer, this.props.pollInterval);
    // Keep every tab on the settings last changed in any of them.
    onStoredChange(UI_SETTINGS_KEY, () => this.setState({uiSettings: loadUiSettings()}));
    askNotificationPermissionOnClick(() => this.state.uiSettings.solve_desktop);
  }
  componentDidUpdate(prevProps, prevState) {
    if (prevState.uiSettings !== this.state.uiSettings) {
      saveStored(UI_SETTINGS_KEY, this.state.uiSettings);
    }
  }
  render() {
    if (this.state.rounds) {
        return (
          <div>
            <SolveNotifier rounds={ this.state.rounds }
                           uiSettings={ this.state.uiSettings }
            />
            <NavHeaderComponent rounds={ this.state.rounds }
                                settings={ this.state.settings }
            />
            <RoundsComponent rounds={ this.state.rounds }
                             changeMade={ this.loadDataFromServer }
                             settings={ this.state.settings }
                             uiSettings={ this.state.uiSettings }
                             updateUiSetting={ this.updateUiSetting }
            />
          </div>);
    } else {
        return null;
    }
  }
  loadDataFromServer = () => {
    getJson('/puzzles/')
      .then(data => this.setState(data))
      .catch(err => console.error('Loading puzzle data failed:', err));
  };
  updateUiSetting = (key, value) => {
    this.setState(state => ({
      uiSettings: {...state.uiSettings, [key]: value}
    }));
  };
}

createRoot(document.getElementById('react-root')).render(<Page pollInterval={ 10000 } />);
