'use strict';

import React from 'react';
import { classNames, postJson } from '../utils';
import ActivityComponent from './activity';
import CelebrationModal from './celebration';
import RoundInfoComponent from './round-info';

// importing these as react/webpack images does NOT work because we don't really have webpack
// and Django set up to talk to each other
const discordIcon = '/static/Discord-Logo-Color.png';
const gappsIcon = '/static/sheets_64dp.png';

export default class PuzzleComponent extends React.Component {
    state = {
        celebrating: false
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
        var classes = classNames({
          'col-lg-12': true,
          'puzzle': true,
          'meta': puzzle.is_meta,
          'solved': puzzle.answer
        });
        var celebrationModal;
        var puzzlePageButton;

        if (this.state.celebrating) {
            celebrationModal = <CelebrationModal puzzle={ puzzle }
                                                 roundNumber={ this.props.parent.number }
                                                 roundName={ this.props.parent.name }
                                                 closeCallback={ this.stopCelebrating } />;
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
        var discordButton;
        if (this.props.settings.discord) {
          if (this.props.settings.profile.discord_identifier) {
            discordButton = (
                <a
                    title={ `#${puzzle.slug}` }
                    href={ `/disc/${puzzle.id}/${Number(this.props.uiSettings.app_links)}` }
                    target="discord" rel="noopener">
                  <img className="messaging-logo" src={ discordIcon } alt={ `Discord` } />
                </a>
            )
          } else {
            discordButton = (
                <img className="messaging-logo" src={discordIcon} alt={`Discord`} title={`Click to copy!`}
                     onClick={ () => copyToClipboard(`hb!join ${puzzle.slug}`) }/>
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
                <div className={ classes }>

                  <div className="row">
                    <div className="col-xs-6 col-sm-6 col-md-4 col-lg-3 name">
                      { puzzlePageButton }
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
                            channelActive: puzzle.channel_active,
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
        postJson(`/puzzles/${this.props.puzzle.id}/`, { [key]: val })
            .then(() => this.props.changeMade && this.props.changeMade())
            .catch(err => console.error(`Updating ${key} failed:`, err));
    }
    stopCelebrating = () => {
        this.state.celebrating && this.setState({
            celebrating: false
        });
    };
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .catch(err => console.error('Copying to clipboard failed:', err));
}
