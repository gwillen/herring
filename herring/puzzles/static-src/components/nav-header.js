'use strict';

import React from 'react';
import * as Utils from '../utils';

export default function NavHeaderComponent({ rounds }) {
    var rs,
        roundTags = rounds.map(function(round) {
          var target = '#' + Utils.targetifyRound(round);
          var key = 'shortcut-' + round.id.toString();
          return (
              <a key={key} href={target}>R{round.number}</a>
          );
        });
    rs = Utils.interleave(' | ', roundTags);
    return (<div className="row">
          <div className="col-lg-12">
            <div className="shortcuts">
              Hop to: {rs}
            </div>
          </div>
        </div>
         );
}
