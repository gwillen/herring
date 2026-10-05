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

// Joins the keys of `classes` whose values are truthy, e.g. for className.
export function classNames(classes) {
    return Object.keys(classes).filter(name => classes[name]).join(' ');
}

async function checkedFetch(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`${options?.method ?? 'GET'} ${url} failed: ${response.status} ${response.statusText}`);
    }
    return response;
}

export async function getJson(url) {
    return (await checkedFetch(url)).json();
}

// `csrfToken` is a global set by the Django template.
export function postJson(url, data) {
    return checkedFetch(url, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    });
}

// Reads a JSON value from localStorage, or `fallback` if it's missing or unreadable.
export function loadStored(key, fallback) {
    try {
        return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch (err) {
        console.error(`Couldn't read ${key} from localStorage:`, err);
        return fallback;
    }
}

export function saveStored(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
        console.error(`Couldn't save ${key} to localStorage:`, err);
    }
}
