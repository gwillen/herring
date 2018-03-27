'use strict';

const React = require('react');
const PropTypes = require('prop-types');
const cx = require('classnames');
const request = require('then-request');

const PuzzleInfoComponent = require('./puzzle-info');
const CelebrationModal = require('./celebration');
const UrlChangeModal = require('./url-editor');


class PuzzleComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      celebrating: false,
      changingUrl: false
    };
  }

  componentWillReceiveProps(nextProps) {
    // Did this puzzle just get solved?
    if (nextProps.puzzle.answer && nextProps.puzzle.answer !== this.props.puzzle.answer) {
      this.setState({
        celebrating: true
      });
    } else if (nextProps.puzzle.answer === '') {
      this.stopCelebrating();
    }
  }

  render() {
    const puzzle = this.props.puzzle;
    const classes = cx({
      'col-lg-12': true,
      'puzzle': true,
      'meta': puzzle.is_meta,
      'solved': puzzle.answer
    });
    let celebrationModal;
    let urlChangeModal;
    let puzzlePageButton;

    if (this.state.celebrating) {
      celebrationModal = (
        <CelebrationModal 
          puzzle={ puzzle }
          roundNumber={ this.props.roundNumber }
          roundName={ this.props.roundName }
          closeCallback={ this.stopCelebrating } />
      );
    }
    if (this.state.changingUrl) {
      urlChangeModal = (
        <UrlChangeModal 
          puzzle={ puzzle }
          actionCallback={ (val) => this.updateData('url', val)}
          closeCallback={ this.toggleUrlModal } />
      );
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
            <button
              title={ `${puzzle.hunt_url ? "Edit" : "Add"} hunt puzzle page` }
              onClick={ this.toggleUrlModal }
            >
              { puzzle.hunt_url ? "Edit" : "Add" }
            </button>
            <a
              title={ `#${puzzle.slug}` }
              href={ `https://ireproof.slack.com/app_redirect?channel=${puzzle.slug}` }
              target="_blank" rel="noopener">
              { puzzle.name }
            </a>
          </div>
          <PuzzleInfoComponent
            className="col-xs-6 col-sm-3 col-md-3 col-lg-2 answer editable"
            val={ puzzle.answer }
            onSubmit={ (val) => this.updateData('answer', val) }
          />
          <PuzzleInfoComponent
            className="visible-md visible-lg col-md-3 col-lg-4 note editable"
            val={ puzzle.note }
            onSubmit={ (val) => this.updateData('note', val) }
          />
          <PuzzleInfoComponent
            className="hidden-xs col-sm-3 col-md-2 col-lg-2 tags editable"
            val={ puzzle.tags }
            onSubmit={ (val) => this.updateData('tags', val) }
          />
          </div>
        </div>
        </div>
      </div>
    );
  }

  updateData = (key, val) => {
    let update = {};

    update[key] = val;
    request('POST', `/puzzles/${this.props.puzzle.id.toString()}/`,
      {
        body: JSON.stringify(update),
        headers: {
          'X-CSRFToken': csrfToken
        }
      }
    ).done(function (res) {
      this.props.onChange && this.props.onChange();
      }.bind(this));
  }

  stopCelebrating = () => {
    this.setState({
      celebrating: false
    });
  }

  toggleUrlModal = () => {
    this.setState({
      changingUrl: !this.state.changingUrl
    });
  }
};

PuzzleComponent.propTypes = {
  puzzle: PropTypes.object.isRequired,
  roundNumber: PropTypes.number,
  roundName: PropTypes.string,
  onChange: PropTypes.func,
};

module.exports = PuzzleComponent;
