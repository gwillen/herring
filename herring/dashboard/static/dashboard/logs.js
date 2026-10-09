// Log page: live tail, "load older", and expanding long messages.
'use strict';

(function () {
  const POLL_MS = 3000;
  const LIVE_KEY = 'herring.dashboard.logs.live';
  const tbody = document.getElementById('log-entries');
  const liveBox = document.getElementById('live');
  const olderButton = document.getElementById('load-older');
  const notice = document.getElementById('log-notice');
  const filters = new URLSearchParams(new FormData(document.getElementById('log-filters')));

  function entryRow(entry) {
    const row = document.createElement('tr');
    row.className = `log-entry level-${entry.level.toLowerCase()}`;
    row.dataset.id = entry.id;
    const cells = [entry.time, entry.level, entry.logger, entry.process];
    cells.forEach((text, i) => {
      const td = row.insertCell();
      td.textContent = text;
      if (i === 0 || i === 3) td.className = 'nowrap';
    });
    const pre = document.createElement('pre');
    pre.className = 'log-message';
    pre.textContent = entry.message;
    row.insertCell().appendChild(pre);
    return row;
  }

  async function fetchEntries(bound) {
    const response = await fetch(`entries.json?${filters}&${new URLSearchParams(bound)}`);
    if (!response.ok) throw new Error(`entries.json: ${response.status} ${response.statusText}`);
    return response.json();
  }

  function showNotice(text) {
    notice.textContent = text;
    notice.hidden = !text;
  }

  function idOf(row) { return row && row.dataset.id; }
  function removePlaceholder() { tbody.querySelector('.no-entries')?.remove(); }

  async function pollNewer() {
    const newest = idOf(tbody.querySelector('.log-entry'));
    try {
      const { entries, more } = await fetchEntries(newest ? { after: newest } : {});
      if (entries.length) removePlaceholder();
      entries.slice().reverse().forEach(entry => tbody.prepend(entryRow(entry)));
      if (more) showNotice('Many new entries arrived at once; only the newest were added. Reload to see everything.');
    } catch (err) {
      showNotice(`Live update failed: ${err.message}`);
      console.error(err);
    }
  }

  async function loadOlder() {
    const rows = tbody.querySelectorAll('.log-entry');
    const oldest = idOf(rows[rows.length - 1]);
    try {
      const { entries, more } = await fetchEntries(oldest ? { before: oldest } : {});
      entries.forEach(entry => tbody.appendChild(entryRow(entry)));
      olderButton.hidden = !more;
    } catch (err) {
      showNotice(`Loading older entries failed: ${err.message}`);
      console.error(err);
    }
  }

  let timer = null;
  function setLive(on) {
    clearInterval(timer);
    timer = on ? setInterval(pollNewer, POLL_MS) : null;
    try { localStorage.setItem(LIVE_KEY, on ? '1' : ''); } catch (err) { console.error(err); }
  }

  liveBox.addEventListener('change', () => setLive(liveBox.checked));
  olderButton.addEventListener('click', loadOlder);
  // Click a long message to expand or collapse it.
  tbody.addEventListener('click', event => event.target.closest('.log-message')?.classList.toggle('expanded'));

  try { liveBox.checked = localStorage.getItem(LIVE_KEY) === '1'; } catch (err) { console.error(err); }
  setLive(liveBox.checked);
})();
