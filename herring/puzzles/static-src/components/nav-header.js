'use strict';

import React from 'react';
import * as Utils from '../utils';
import { solveCounts } from '../puzzle-list';

// importing these as react/webpack images does NOT work because we don't really have webpack
// and Django set up to talk to each other
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
    var discord;
    var gapps;
    if (settings.discord) {
      discord = <span className={Utils.classNames({"messaging-logo": true, "broken": !settings.service_status.discord})}>
        <img className="messaging-logo" src={ discordIcon } alt={ `Discord` } />
      </span>
    }
    if (settings.gapps) {
      gapps = <span className={Utils.classNames({"messaging-logo": true, "broken": !settings.service_status.gapps})}>
        <img className="messaging-logo" src={ gappsIcon } alt={ `Google Sheets` } />
      </span>
    }

    return (<div className="row">
          <div className="col-lg-12">
            <div className="shortcuts">
              Hop to: {rs}
              <SolveSummary puzzles={ rounds.flatMap(round => round.puzzle_set) } />
              <span className="hidden-lg activity-hint" title="The Activity column only fits on wide windows">
                (widen the window to see the Activity column)
              </span>
              <div className="integration-status">
                Integrations:
                {discord}
                {gapps}
              </div>
            </div>
          </div>
        </div>
         );
}

function SolveSummary({ puzzles }) {
    const counts = solveCounts(puzzles);
    return (
        <span className="solve-summary">
          Solved {counts.solved}/{counts.total}{ counts.metasTotal > 0 && `, metas ${counts.metasSolved}/${counts.metasTotal}` }
        </span>
    );
}
