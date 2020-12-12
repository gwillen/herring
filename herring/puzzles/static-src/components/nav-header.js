'use strict';

import React from 'react';
import * as Utils from '../utils';
import cx from 'classnames';

// importing these as react/webpack images does NOT work because we don't really have webpack
// and Django set up to talk to each other
const slackIcon = '/static/Slack_Mark_Web.png';
const discordIcon = '/static/Discord-Logo-Color.png';
const gappsIcon = '/static/sheets_64dp.png';

export default function NavHeaderComponent({ rounds, settings }) {
    var rs,
        roundTags = rounds.map(function(round) {
          var target = '#' + Utils.targetifyRound(round);
          var key = 'shortcut-' + round.id.toString();
          return (
              <a key={key} href={target}>R{round.number}</a>
          );
        });
    rs = Utils.interleave(' | ', roundTags);
    var slack;
    var discord;
    var gapps;
    if (settings.slack) {

      slack = <span className={cx({"messaging-logo": true, "broken": !settings.service_status.slack})}>
        <img className="messaging-logo" src={ slackIcon } alt={ `Slack` } />
      </span>
    }
    if (settings.discord) {
      discord = <span className={cx({"messaging-logo": true, "broken": !settings.service_status.discord})}>
        <img className="messaging-logo" src={ discordIcon } alt={ `Discord` } />
      </span>
    }
    if (settings.gapps) {
      gapps = <span className={cx({"messaging-logo": true, "broken": !settings.service_status.gapps})}>
        <img className="messaging-logo" src={ gappsIcon } alt={ `Google Sheets` } />
      </span>
    }

    return (<div className="row">
          <div className="col-lg-12">
            <div className="shortcuts">
              Hop to: {rs}
              <div className="integration-status">
                Integrations:
                {slack}
                {discord}
                {gapps}
              </div>
            </div>
          </div>
        </div>
         );
}
