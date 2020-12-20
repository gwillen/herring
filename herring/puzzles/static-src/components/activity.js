'use strict';

import React from 'react';

const P = 120000;  // observation period (ms)
const N = 60;      // number of periods in graph
const B = 6;       // number of periods in a bucket

export default function ActivityComponent(props) {
    const { className, activity } = props;
    const { channelCount, channelActive, activityHisto, lastActive } = activity;
    const now = new Date();
    const buckets = histoToBuckets(activityHisto, lastActive, now);
    const activeInvisible = channelActive.length === 0 ? 'invisible' : '';
    const activeUsers = channelActive.join(', ');
    return (
        <div className={className}>
            <span className="allMembers">
                {pad(channelCount)}
                <span className="glyphicon glyphicon-user" aria-hidden="true"></span>
            </span>
            &nbsp;
            <span className={`activeMembers ${activeInvisible}`} title={activeUsers}>
                {pad(channelActive.length)}
                <span className="glyphicon glyphicon-user" aria-hidden="true"></span>
            </span> {
            buckets && <BarChart data={buckets} max={B} width={30} height={13} />} {
            lastActive <= 0 ? 'never' : renderTimeDelta(now - lastActive)}
        </div>);
}

function histoToBuckets(activityHisto, lastActive, now) {
    const d = Math.floor(now / P) - Math.floor(lastActive / P);
    if (d >= N) {
        return;
    }
    const mask = (1 << B) - 1;
    const buckets = [];
    for (let i = d, j = i + B, iMax = N + d; i < iMax; i = j, j += B) {
        let bits = parseInt(activityHisto.substring(i >> 2, -(-j >> 2)), 16);
        if (j < N) {
            bits >>= j & 3;
        }
        bits &= mask;
        buckets.push(popcnt(bits));
    }
    return buckets;
}

function popcnt(x) {
    let count;
    for (count = 0; x; count++) {
        x &= x - 1;
    }
    return count;
}

function pad(x) {
    return x < 10 ? '\u2007' + x : x;
}

function renderTimeDelta(d) {
    if (d < 60000) {
        const c = Math.floor(d/1000);
        return `${c}s ago`;
    }
    if (d < 3600000) {
        const c = Math.floor(d/60000);
        return `${c}m ago`;
    }
    if (d < 86400000) {
        const ch = Math.floor(d/3600000);
        const cm = Math.floor((d % 3600000)/60000);
        return `${ch}h${cm > 0 ? ` ${cm}m` : ''} ago`;
    }
    const cd = Math.floor(d/86400000);
    const ch = Math.floor((d % 86400000)/3600000);
    return `${cd}d${ch > 0 ? ` ${ch}h` : ''} ago`;
}

function BarChart({ data, max, width, height }) {
    const w = width/data.length;
    const h = (height - 1)/max;
    return (
        <svg width={width} height={height}>
            <g fill="currentColor">
                <rect x={0} y={height - 1} width={width} height={1} />
                {data.map((value, i) =>
                    <rect key={i}
                          x={i * w} y={height - value * h}
                          width={w} height={value * h} />)}
            </g>
        </svg>);
}
