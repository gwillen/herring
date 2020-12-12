'use strict';

import cx from 'classnames';
import PropTypes from 'prop-types';
import React from 'react';
import request from 'then-request';
import {CopyToClipboard} from 'react-copy-to-clipboard';
import ActivityComponent from './activity';
import CelebrationModal from './celebration';
import RoundInfoComponent from './round-info';
import UrlChangeModal from './url-editor';

// importing these as react/webpack images does NOT work because we don't really have webpack
// and Django set up to talk to each other
const slackIcon = '/static/Slack_Mark_Web.png';
const discordIcon = '/static/Discord-Logo-Color.png';
const gappsIcon = '/static/sheets_64dp.png';

export default class PuzzleComponent extends React.Component {
    state = {
        celebrating: false,
        changingUrl: false
    };
    componentDidUpdate(prevProps) {
        // did we solve a new puzzle?
        if (this.props.puzzle.answer && this.props.puzzle.answer !== prevProps.puzzle.answer) {
            this.state.celebrating || this.setState({
                celebrating: true
            });
        } else if (this.props.puzzle.answer === '') {
            this.stopCelebrating();
        }
    }
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
        } else {
          puzzlePageButton = (
              <span className="missing-button" />
          )
        }
        var slackButton;
        if (this.props.settings.slack) {
          var href;
          if (this.props.uiSettings.app_links){
            if (puzzle.slack_channel_id) {
            href = `slack://channel?team=T0ESH0TS5&id=${puzzle.slack_channel_id}`
            } else {
              href = `https://ireproof.slack.com/app_redirect?channel=${puzzle.slug}`
            }
          } else {
            href = `https://ireproof.slack.com/messages/${puzzle.slug}`
          }
          slackButton = (
              <a
                  title={ `#${puzzle.slug}` }
                  href={ href }
                  target="_blank" rel="noopener">
                <img className="messaging-logo" src={ slackIcon } alt={ `Slack` } />
              </a>
          )
        }
        var discordButton;
        if (this.props.settings.discord) {
          if (this.props.settings.profile.discord_identifier) {
            discordButton = (
                <a
                    title={ `#${puzzle.slug}` }
                    href={ `/disc/${puzzle.id}/${Number(this.props.uiSettings.app_links)}` }
                    target="_blank" rel="noopener">
                  <img className="messaging-logo" src={ discordIcon } alt={ `Discord` } />
                </a>
            )
          } else {
            discordButton = (
                <CopyToClipboard
                    text={`hb!join ${puzzle.slug}`}>
                  <img className="messaging-logo" src={discordIcon} alt={`Discord`} title={`Click to copy!`}/>
                </CopyToClipboard>
            )
          }
        }
        var gappsButton;
        if (this.props.settings.gapps) {
          gappsButton = (
              <a
                  title={ `#${puzzle.slug}` }
                  href={ `/s/${puzzle.id}` }
                  target="_blank" rel="noopener">
                <img className="messaging-logo" src={ gappsIcon } alt={`Google Sheets`} />
              </a>
          )
        }
        return (
            <div key={ puzzle.id } className="row">
              <div className="col-lg-12">
                { celebrationModal }
                { urlChangeModal }
                <div className={ classes }>

                  <div className="row">
                    <div className="col-xs-6 col-sm-6 col-md-4 col-lg-3 name">
                      { puzzlePageButton }
                      { slackButton }
                      { discordButton }
                      { gappsButton }
                      <span className="name-text">{ puzzle.name }</span>
                    </div>
                    <RoundInfoComponent
                        className="col-xs-6 col-sm-3 col-md-3 col-lg-2 answer editable"
                        val={ puzzle.answer }
                        onSubmit={ this.updateAnswer }
                    />
                    <RoundInfoComponent
                        className="visible-md visible-lg col-md-3 col-lg-3 note editable"
                        val={ puzzle.note }
                        onSubmit={ this.updateNote }
                    />
                    <RoundInfoComponent
                        className="hidden-xs col-sm-3 col-md-2 col-lg-2 tags editable"
                        val={ puzzle.tags }
                        onSubmit={ this.updateTags }
                    />
                    <ActivityComponent
                        className="visible-lg-block col-lg-2 activity"
                        activity={ {
                            channelCount: puzzle.channel_count,
                            channelActiveCount: puzzle.channel_active_count,
                            activityHisto: puzzle.activity_histo,
                            lastActive: new Date(puzzle.last_active),
                        } }
                    />
                  </div>
                </div>
              </div>
            </div>
        );
    }
    showPuzzleUrlModal() {
        this.setState({
            changingUrl: true
        });
    }
    updateUrl = val => {
        this.updateData('url', val);
    };
    updateAnswer = val => {
        this.updateData('answer', val);
    };
    updateNote = val => {
        this.updateData('note', val);
    };
    updateTags = val => {
        this.updateData('tags', val);
    };
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
    }
    stopCelebrating = () => {
        this.state.celebrating && this.setState({
            celebrating: false
        });
    };
    closeUrlModal = () => {
        this.setState({
            changingUrl: false
        });
    };
}

PuzzleComponent.propTypes = {
    puzzle: PropTypes.object.isRequired,
    parent: PropTypes.object,
    changeMade: PropTypes.func,
    settings: PropTypes.object,
    uiSettings: PropTypes.object,
};
