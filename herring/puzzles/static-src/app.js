'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var NavHeaderComponent = require('./components/nav-header');
var RoundsComponent = require('./components/rounds');


var Page = React.createClass({
  getInitialState() {
    return {rounds: rounds};
  },
  render: function() {
    return (<div>
          <NavHeaderComponent rounds={this.state.rounds} />
          <RoundsComponent rounds={this.state.rounds} />
        </div>);
  }
});

var page = <Page />;
var renderedPage = ReactDOM.render(page, document.getElementById('react-root'));
