'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var request = require('then-request');
var NavHeaderComponent = require('./components/nav-header');
var RoundsComponent = require('./components/rounds');


var Page = React.createClass({
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

var page = <Page pollInterval={ 10000 } />;
var renderedPage = ReactDOM.render(page, document.getElementById('react-root'));
