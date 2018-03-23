'use strict';

const React = require('react');
const ReactDOM = require('react-dom');
const request = require('then-request');

const NavHeaderComponent = require('./components/nav-header');
const RoundsComponent = require('./components/rounds');

const Page = React.createClass({
  getInitialState() {
    return {};
  },
  componentDidMount: function() {
    this.loadDataFromServer();
    setInterval(this.loadDataFromServer, this.props.pollInterval);
    Notification.requestPermission(function (permission) {
      // If the user accepts, let's create a notification
      if (permission === 'granted') {
        console.log('Browser notifications are active.');
      }
    });
  },
  render: function() {
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
  },
  loadDataFromServer: function() {
    request('GET', '/puzzles/').done(function (res) {
      this.setState(JSON.parse(res.getBody()));
    }.bind(this));
  }
});

const page = <Page pollInterval={ 10000 } />;
const renderedPage = ReactDOM.render(page, document.getElementById('react-root'));
