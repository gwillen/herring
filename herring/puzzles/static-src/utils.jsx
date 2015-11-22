'use strict';

var utils = {
    targetifyRound: function(round) {
        return 'round-' + round.id.toString();
    },
    interleave: function(element, array) {
        var retval = [];
        for (var i = 0; i < array.length; i++) {
            retval.push(array[i]);
            if (i !== array.length - 1) {
                retval.push(element);
            }
        }
        return retval;
    }
};

module.exports = utils;
