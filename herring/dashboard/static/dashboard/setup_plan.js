// Setup plan page: keep the ticked operations consistent with their dependencies.
'use strict';

(function () {
  const boxes = [...document.querySelectorAll('input[name="operation"]')];
  const byKey = new Map(boxes.map(box => [box.value, box]));
  const depsOf = box => box.dataset.deps.split(' ').filter(Boolean);

  function tickWithDependencies(box) {
    box.checked = true;
    depsOf(box).forEach(key => { const dep = byKey.get(key); if (dep && !dep.checked) tickWithDependencies(dep); });
  }

  function untickWithDependents(box) {
    box.checked = false;
    boxes.filter(other => other.checked && depsOf(other).includes(box.value)).forEach(untickWithDependents);
  }

  boxes.forEach(box => box.addEventListener('change',
    () => (box.checked ? tickWithDependencies : untickWithDependents)(box)));
  document.getElementById('toggle-all').addEventListener('change', event =>
    boxes.forEach(box => { box.checked = event.target.checked; }));
})();
