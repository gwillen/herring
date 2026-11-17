'use strict';

import React from 'react';
import { classNames } from '../utils';
import { tagChoices } from '../puzzle-list';

// One-click filters for the tags in use: click a tag to show only puzzles
// with it, click it again to show all.
export default function TagFilters({ rounds, selectedTag, selectTag }) {
    const choices = tagChoices(rounds, selectedTag);
    if (choices.length === 0) {
        return null;
    }
    return (
        <div className="tag-filters">
            <span className="tag-filters-label">Tags:</span>
            { choices.map(([tag, count]) =>
                <button key={ tag }
                        className={ classNames({ 'tag-filter': true, 'selected': tag === selectedTag }) }
                        aria-pressed={ tag === selectedTag }
                        onClick={ () => selectTag(tag === selectedTag ? '' : tag) }>
                    { tag } <span className="tag-count">{ count }</span>
                </button>) }
        </div>
    );
}
