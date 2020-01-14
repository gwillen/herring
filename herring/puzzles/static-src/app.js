'use strict';

import React from 'react';
import ReactDOM from 'react-dom';
import request from 'then-request';
import NavHeaderComponent from './components/nav-header';
import RoundsComponent from './components/rounds';

class Page extends React.Component {
  state = {};
  componentDidMount() {
    this.loadDataFromServer();
    setInterval(this.loadDataFromServer, this.props.pollInterval);
    Notification.requestPermission(function (permission) {
      // If the user accepts, let's create a notification
      if (permission === 'granted') {
        console.log('Browser notifications are active.');
      }
    });
  }
  render() {
    if (this.state.rounds) {
        return (
          <div>
            <NavHeaderComponent rounds={ this.state.rounds } />
            <RoundsComponent rounds={ this.state.rounds }
                             changeMade={ this.loadDataFromServer } />
          </div>);
    } else {
        return null;
    }
  }
  loadDataFromServer = () => {
    request('GET', '/puzzles/').done(res =>
      this.setState(JSON.parse(res.getBody())));
  };
}

var page = <Page pollInterval={ 10000 } />;
var renderedPage = ReactDOM.render(page, document.getElementById('react-root'));
