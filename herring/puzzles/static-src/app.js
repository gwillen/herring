'use strict';

import React from 'react';
import ReactDOM from 'react-dom';
import request from 'then-request';
import store from 'store';
import NavHeaderComponent from './components/nav-header';
import RoundsComponent from './components/rounds';

class Page extends React.Component {
  state = {
    uiSettings: {
      app_links: false
    }
  };
  componentDidMount() {

    this.setState({uiSettings: store.get('uiSettings', {app_links: false})});
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
    store.set('uiSettings', this.state.uiSettings);
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
    request('GET', '/puzzles/').done(res =>
      this.setState(JSON.parse(res.getBody())));
  };
  toggleLinkType = () => {
    // this just deep-merges into state.uiSettings
    this.setState(state => ({
      uiSettings: {...state.uiSettings, app_links: !state.uiSettings.app_links}
    }))
  }
}

var page = <Page pollInterval={ 10000 } />;
var renderedPage = ReactDOM.render(page, document.getElementById('react-root'));
