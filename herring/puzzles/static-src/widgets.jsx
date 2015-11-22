'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var cx = require('classnames');

var interleave = function(element, array) {
    var retval = [];
    for (var i = 0; i < array.length; i++) {
        retval.push(array[i]);
        if (i !== array.length - 1) {
            retval.push(element);
        }
    }
    return retval;
};

var targetifyRound = function(round) {
    return 'round-' + round.id.toString();
};


var NavHeaderComponent = React.createClass({
  render: function() {
    var rs,
        roundTags = this.props.rounds.map(function(round) {
          var target = '#' + targetifyRound(round);
          var key = 'shortcut-' + round.id.toString();
          return (
              <a key={key} href={target}>R{round.number}</a>
          );
        });
    rs = interleave(' | ', roundTags);
    return (<div className="row">
          <div className="col-lg-12">
            <div className="shortcuts">
              Hop to: {rs}
            </div>
          </div>
        </div>
         );
  }
});


var DefaultInputComponent = React.createClass({
    propTypes: {
        defaultValue: React.PropTypes.string.isRequired,
    },
    getInitialState: function() {
        return {};
    },
    componentDidMount: function () {
        this.setState({
            val: this.props.defaultValue
        });
    },
    render: function(){
        return (
            <input ref="editInput"
                   type="text"
                   value={ this.state.val }
                   onChange={ this.handleChange } />
        );
    },
    handleChange: function(evt){
        this.setState({val: evt.target.value});
    },
});

var RoundInfoComponent = React.createClass({
    propTypes: {
        className: React.PropTypes.string,
        val: React.PropTypes.string,
        onSubmit: React.PropTypes.func.isRequired
    },
    getInitialState: function() {
        return {
            newVal: undefined,
            editable: false
        };
    },
    componentDidMount: function () {
        document.addEventListener('click', this.handleDocumentClick);
    },

    componentWillUnmount: function () {
        document.removeEventListener('click', this.handleDocumentClick);
    },
    render: function() {
        var contents;
        if (this.state.editable) {
            contents = (
                <form onSubmit={ this.onSubmit }>
                    <DefaultInputComponent
                        ref="editInput"
                        defaultValue={ this.props.val }/>
                </form>
            );
        } else {
            contents = (
                <span>
                    { this.props.val }&nbsp;
                </span>
            );
        }
        return (
            <div ref="editableComponent" className={ this.props.className }
                 onClick={ this.editElement } >
                { contents }
            </div>
        );
    },
    handleDocumentClick: function (evt) {
        var self = ReactDOM.findDOMNode(this.refs.editableComponent),
            target = evt.target;
        if (this.state.editable && (!self || !self.contains(target))) {
            this.setState({ editable: false });
        }
    },
    editElement: function(evt) {
        this.setState({
            editable: true
        },this.focus);
    },
    onSubmit: function(evt) {
        evt.preventDefault();
        var newState = {
            editable: false
        };

        // if something's changed, call onSubmit
        if (this.refs.editInput.state.val !== this.props.val) {
            this.props.onSubmit(this.refs.editInput.state.val);
        }
        // else just make it not editable
        this.setState(newState);
    },
    focus: function() {
        ReactDOM.findDOMNode(this.refs.editInput).focus();
    }
});


var PuzzleComponent = React.createClass({
    propTypes: {
        puzzle: React.PropTypes.object.isRequired
    },
    render: function() {
        var puzzle = this.props.puzzle;
        var classes = cx({
          'col-lg-12': true,
          'puzzle': true,
          'meta': puzzle.is_meta,
          'solved': puzzle.answer
        });
        return (
            <div key={puzzle.id} className="row">
              <div className="col-lg-12">
                <div className={classes}>
                  <div className="row">
                    <div className="col-xs-6 col-sm-6 col-md-4 col-lg-4 name">
                      <a title={ puzzle.name } href={ puzzle.url }>{ puzzle.name }</a>
                    </div>
                    <RoundInfoComponent
                        className="col-xs-6 col-sm-3 col-md-3 col-lg-2 answer editable"
                        val={ puzzle.answer }
                        onSubmit={ this.updateAnswer }
                    />
                    <RoundInfoComponent
                        className="visible-md visible-lg col-md-3 col-lg-4 note editable"
                        val={ puzzle.note }
                        onSubmit={ this.updateNote }
                    />
                    <RoundInfoComponent
                        className="hidden-xs col-sm-3 col-md-2 col-lg-2 tags editable"
                        val={ puzzle.tags }
                        onSubmit={ this.updateTags }
                    />
                  </div>
                </div>
              </div>
            </div>
        );
    },
    updateAnswer: function(val) {
        this.updateData('answer', val);
    },
    updateNote: function(val) {
        this.updateData('note', val);
    },
    updateTags: function(val) {
        this.updateData('tags', val);
    },
    updateData: function(key, val){
        // TODO
        var update = {};
        var puzzleID = this.props.puzzle.id;

        update[key] = val;
        console.log('I am totally updating puzzle ' + puzzleID + ' now', update);
    }
});


var RoundComponent = React.createClass({
  render: function() {
    var round = this.props.round;
    var target = targetifyRound(round);
    var puzzles = round.puzzle_set.map(function(puzzle) {
      return <PuzzleComponent key={ puzzle.id }
                              puzzle={ puzzle } />;
    });
    return (
      <div key={round.id} className="row">
        <div className="col-lg-12 round">
          <h2 id={target}>R{round.number} {round.name}</h2>

          <div className="col-lg-12">
            <div className="row legend">
              <div className="col-xs-6 col-sm-6 col-md-4 col-lg-4">
                Name
              </div>
              <div className="col-xs-6 col-sm-3 col-md-3 col-lg-2">Answer</div>
              <div className="visible-md visible-lg col-md-3 col-lg-4">Notes</div>
              <div className="hidden-xs col-sm-3 col-md-2 col-lg-2">Tags</div>
            </div>
          </div>
          {puzzles}
        </div>
      </div>
      );
  }
});


var RoundsComponent = React.createClass({
  render: function() {
    var rs = this.props.rounds.map(function(round) {
      return <RoundComponent round={round} />;
    });
    return <div>{rs.length > 0 ? rs : <p>No puzzles are available</p>}</div>
  }
});


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
