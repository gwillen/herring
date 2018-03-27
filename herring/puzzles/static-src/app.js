'use strict';

const React = require('react');
const ReactDOM = require('react-dom');
const request = require('then-request');

const NavHeaderComponent = require('./components/nav-header');
const RoundsComponent = require('./components/rounds');


class Page extends React.Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

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
          <RoundsComponent
            rounds={ this.state.rounds }
            onChange={ this.loadDataFromServer }
          />
        </div>);
    }
    return null;
  }

  loadDataFromServer = () => {
    request('GET', '/puzzles/').done(function (res) {
      this.setState(JSON.parse(res.getBody()));
    }.bind(this));
  }
};

const renderedPage = ReactDOM.render(
  <Page pollInterval={ 10000 } />,
  document.getElementById('react-root')
);
