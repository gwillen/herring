'use strict';

import React from 'react';
import { createRoot } from 'react-dom/client';
import { getJson, loadStored, saveStored } from './utils';
import NavHeaderComponent from './components/nav-header';
import RoundsComponent from './components/rounds';

class Page extends React.Component {
  state = {
    // Same localStorage key and format the old store.js library used.
    uiSettings: loadStored('uiSettings', {app_links: false})
  };
  componentDidMount() {
    this.loadDataFromServer();
    setInterval(this.loadDataFromServer, this.props.pollInterval);


    // Request permission to send web notifications--this has to take place in
    // an event handler triggered by a user interaction, or modern browsers
    // will ignore it.
    const askForPermissionToNotify = () => {
      Notification.requestPermission(permission => {
        document.removeEventListener('click', askForPermissionToNotify);
        if (permission === 'granted') {
          console.log('Browser notifications are active.');
        }
      });
    };
    document.addEventListener('click', askForPermissionToNotify);
  }
  componentDidUpdate() {
    saveStored('uiSettings', this.state.uiSettings);
  }
  render() {
    if (this.state.rounds) {
        return (
          <div>
            <NavHeaderComponent rounds={ this.state.rounds }
                                settings={ this.state.settings }
            />
            <RoundsComponent rounds={ this.state.rounds }
                             changeMade={ this.loadDataFromServer }
                             settings={ this.state.settings }
                             uiSettings={ this.state.uiSettings }
                             toggleLinkType={ this.toggleLinkType }
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
  toggleLinkType = () => {
    // this just deep-merges into state.uiSettings
    this.setState(state => ({
      uiSettings: {...state.uiSettings, app_links: !state.uiSettings.app_links}
    }))
  }
}

createRoot(document.getElementById('react-root')).render(<Page pollInterval={ 10000 } />);
