'use strict';

var React = require('react');
var cx = require('classnames');
var request = require('then-request');
var RoundInfoComponent = require('./round-info');
var CelebrationModal = require('./celebration');
var UrlChangeModal = require('./url-editor');


var PuzzleComponent = React.createClass({
    propTypes: {
        puzzle: React.PropTypes.object.isRequired,
        parent: React.PropTypes.object,
        changeMade: React.PropTypes.func,
    },
    getInitialState: function () {
        return {
            celebrating: false,
            changingUrl: false
        };
    },
    componentWillReceiveProps(nextProps) {
        // did we solve a new puzzle?
        if (nextProps.puzzle.answer && nextProps.puzzle.answer !== this.props.puzzle.answer) {
            this.setState({
                celebrating: true
            });
        } else if (nextProps.puzzle.answer === '') {
            this.stopCelebrating();
        }
    },
    render() {
        var puzzle = this.props.puzzle;
        var classes = cx({
          'col-lg-12': true,
          'puzzle': true,
          'meta': puzzle.is_meta,
          'solved': puzzle.answer
        });
        var celebrationModal;
        var urlChangeModal;
        var puzzlePageButton;

        if (this.state.celebrating) {
            celebrationModal = <CelebrationModal puzzle={ puzzle }
                                                 roundNumber={ this.props.parent.number }
                                                 roundName={ this.props.parent.name }
                                                 closeCallback={ this.stopCelebrating } />;
        }
        if (this.state.changingUrl) {
            urlChangeModal = <UrlChangeModal puzzle={ puzzle }
                                             actionCallback={ this.updateUrl }
                                             closeCallback={ this.closeUrlModal } />
        }
        if (puzzle.hunt_url) {
            puzzlePageButton = (
                <a
                    className="button"
                    title="View puzzle on hunt website"
                    href={ puzzle.hunt_url }
                    target="_blank" rel="noopener">
                  <span className="glyphicon glyphicon-share-alt"></span>
                </a>
            );
        }
        return (
            <div key={ puzzle.id } className="row">
              <div className="col-lg-12">
                { celebrationModal }
                { urlChangeModal }
                <div className={ classes }>

                  <div className="row">
                    <div className="col-xs-6 col-sm-6 col-md-4 col-lg-4 name">
                      { puzzlePageButton }
                      <a
                          title={ `#${puzzle.slug}` }
                          href={ `https://ireproof.slack.com/app_redirect?channel=${puzzle.slug}` }
                          target="_blank" rel="noopener">
                        { puzzle.name }
                      </a>
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
    showPuzzleUrlModal() {
        this.setState({
            changingUrl: true
        });
    },
    updateUrl(val) {
        this.updateData('url', val);
    },
    updateAnswer(val) {
        this.updateData('answer', val);
    },
    updateNote(val) {
        this.updateData('note', val);
    },
    updateTags(val) {
        this.updateData('tags', val);
    },
    updateData(key, val) {
        // TODO
        var update = {};

        update[key] = val;
        request('POST', '/puzzles/' + this.props.puzzle.id.toString() + '/',
          {
            body: JSON.stringify(update),
            headers: {
              'X-CSRFToken': csrfToken
            }
          }
        ).done(function (res) {
            this.props.changeMade && this.props.changeMade();
          }.bind(this));
    },
    stopCelebrating() {
        this.setState({
            celebrating: false
        });
    },
    closeUrlModal() {
        this.setState({
            changingUrl: false
        });
    }
});

module.exports = PuzzleComponent;
