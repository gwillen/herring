var interleave = function(element, array) {
    retval = [];
    for (var i = 0; i < array.length; i++) {
        retval.push(array[i]);
        if (i != array.length - 1) {
            retval.push(element);
        }
    }
    return retval;
}

var NavHeaderComponent = React.createClass({
    render: function() {
        var roundTags = this.props.rounds.map(function(round) {
            var target = "#R" + round.number + "-" + round.name;
            return <a href={target}>R{round.number}</a>
        });
        rs = interleave(" | ", roundTags);
        return (<div className="shortcuts row">
                <div className="col-lg-12">
                Hop to: {rs}
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

var RoundComponent = React.createClass({
    render: function() {
        var round = this.props.round;
        var target = "#R" + round.number + "-" + round.name;
        var puzzles = round.puzzle_set.map(function(puzzle) {
            return <PuzzleComponent puzzle={puzzle} />;
        });
        return (
          <div className="row">
            <div className="col-lg-12 round">
              <h2 id={target}>R{round.number} {round.name}</h2>
              {puzzles}
            </div>
          </div>
          );
    }
});

var PuzzleComponent = React.createClass({
    render: function() {
        var puzzle = this.props.puzzle;
        return (
                <div className="row">
                  <div className="col-lg-12 puzzle">
                    <span className="name" title={puzzle.name}>{puzzle.name}</span>
                  </div>
                </div>
               );
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

