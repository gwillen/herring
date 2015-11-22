'use strict';

var React = require('react');
var cx = require('classnames');
var RoundInfoComponent = require('./round-info');

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

module.exports = PuzzleComponent;
