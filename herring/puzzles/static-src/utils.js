'use strict';

export function targetifyRound(round) {
    return 'round-' + round.id.toString();
}
export function interleave(element, array) {
    var retval = [];
    for (var i = 0; i < array.length; i++) {
        retval.push(array[i]);
        if (i !== array.length - 1) {
            retval.push(element);
        }
    }
    return retval;
}
