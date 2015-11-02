'use strict';

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
    var s = '#R' + round.number + '-' + round.name;
    return s.replace(/[ \%\$\@\!\(\)\\\/\[\]\^\&\*\?\.\,]+/gi, '-');
};


var NavHeaderComponent = React.createClass({
  render: function() {
    var rs,
        roundTags = this.props.rounds.map(function(round) {
          var target = targetifyRound(round);
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


var PuzzleComponent = React.createClass({
  render: function() {
    var cx = React.addons.classSet;
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
                  <a title={puzzle.name}>{puzzle.name}</a>
                </div>
                <div className="col-xs-6 col-sm-3 col-md-3 col-lg-2 answer">{puzzle.answer}&nbsp;</div>
                <div className="visible-md visible-lg col-md-3 col-lg-4 note" title={puzzle.note}>{puzzle.note}&nbsp;</div>
                <div className="hidden-xs col-sm-3 col-md-2 col-lg-2 tags">{puzzle.tags}&nbsp;</div>
              </div>
            </div>
          </div>
        </div>
         );
  }
});


var RoundComponent = React.createClass({
  render: function() {
    var round = this.props.round;
    var target = targetifyRound(round);
    var puzzles = round.puzzle_set.map(function(puzzle) {
      return <PuzzleComponent puzzle={puzzle} />;
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
    return <div>{rs.length > 0 ? {rs} : <p>No puzzles are available</p>}</div>
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
var renderedPage = React.render(page, document.getElementById('react-root'));
