"""
Drive the Herring UI in headless Chromium: log in, screenshot, use the menu,
edit an answer, check the solve notifications (with two tabs), filter, and
check UI settings survive a reload and reach other tabs. Exits nonzero on
browser console errors/warnings, page errors, failed requests, or failed checks.
Run by scripts/ui-test.sh; usage: browse.py BASE_URL OUTPUT_PREFIX
"""
import sys
from playwright.sync_api import sync_playwright

base, out = sys.argv[1], sys.argv[2]
problems = []
POLL_WAIT_MS = 15000  # the page polls every 10 s

# Count applause plays per tab instead of playing (and avoid autoplay rules).
COUNT_PLAYS = """
window.applausePlays = 0;
HTMLMediaElement.prototype.play = function () { window.applausePlays++; return Promise.resolve(); };
"""

# Sets a puzzle's answer as another team member would, through the API.
SET_ANSWER = """async ([name, answer]) => {
    const data = await (await fetch('/puzzles/')).json();
    const puzzle = data.rounds.flatMap(r => r.puzzle_set).find(p => p.name === name);
    const response = await fetch(`/puzzles/${puzzle.id}/`, {method: 'POST', body: JSON.stringify({answer}),
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken}});
    return response.status;
}"""

def check(description, ok):
    print(('ok:     ' if ok else 'FAILED: ') + description)
    ok or problems.append(f'check failed: {description}')

def shot(page, name):
    page.screenshot(path=f'{out}-{name}.png', full_page=True)

def watch(page, label):
    page.on('console', lambda m: m.type in ('error', 'warning') and problems.append(f'{label} console {m.type}: {m.text}'))
    page.on('pageerror', lambda e: problems.append(f'{label} pageerror: {e}'))
    page.on('response', lambda r: r.status >= 400 and problems.append(f'{label} HTTP {r.status} {r.url}'))

def set_answers(page, answers):
    for name, answer in answers.items():
        check(f'set answer of {name} to {answer!r}', page.evaluate(SET_ANSWER, [name, answer]) == 200)

def listed_solves(page):
    return page.locator('.solved-puzzle h1').all_inner_texts()

def check_solve_notifications(page, other):
    page.locator('.puzzle', has_text='Anagram Antics').locator('.answer').click()
    page.keyboard.type('NEWANSWER'); page.keyboard.press('Enter')
    page.wait_for_selector('.celebration', timeout=POLL_WAIT_MS)
    other.wait_for_selector('.celebration', timeout=POLL_WAIT_MS)
    shot(page, '3-celebration')
    plays = page.evaluate('applausePlays') + other.evaluate('applausePlays')
    check(f'one applause across two tabs (got {plays})', plays == 1)
    page.click('.close-button')
    other.wait_for_selector('.celebration', state='detached', timeout=3000)
    check('dismissing in one tab dismissed the other', other.locator('.celebration').count() == 0)

    set_answers(page, {'Logic of Lists': 'ONE', 'Final Warehouse Meta': 'META', 'Shipping Containers': 'TWO', 'Knots and Ropes': 'THREE'})
    page.wait_for_selector('.solved-puzzle', timeout=POLL_WAIT_MS)
    check('one popup for many solves', page.locator('.modal').count() == 1)
    check(f'two newest + meta listed, rest summarized (got {listed_solves(page)})',
          len(listed_solves(page)) == 2 and page.locator('.show-all').count() == 1)
    shot(page, '4-many-solves')
    page.click('.show-all')
    check('show all lists all four', len(listed_solves(page)) == 4)
    set_answers(page, {'Logic of Lists': 'CORRECTED'})
    page.wait_for_selector('.answer:text("CORRECTED")', timeout=POLL_WAIT_MS)
    page.keyboard.press('Escape')
    check('Escape dismisses', page.locator('.celebration').count() == 0)

def check_puzzle_list(page):
    """Runs when every puzzle is solved, so both rounds start collapsed."""
    page.click('.tag-filter:has-text("grid")')
    check('tag filter shows only tagged puzzles', page.locator('.puzzle').count() == 1)
    page.click('.tag-filter:has-text("grid")')
    check('clicking the tag again shows all', page.locator('.puzzle').count() == 6)
    page.locator('h2', has_text='The Warehouse').locator('button').click()
    page.check('text=Unsolved')
    page.reload(); page.wait_for_selector('.filters')
    check('Unsolved filter survived reload', page.is_checked('text=Unsolved') and page.locator('.puzzle').count() == 0)
    page.uncheck('text=Unsolved')
    page.wait_for_selector('.puzzle', state='attached')
    check('hand-expanded round stayed expanded after reload',
          page.locator('.puzzle', has_text='Anagram Antics').is_visible()
          and not page.locator('.puzzle', has_text='Knots and Ropes').is_visible())
    shot(page, '7-puzzle-list')

def check_settings(page, other):
    page.check('text=Use app links')
    page.select_option('.solve-settings select', 'toast')
    # Every puzzle is solved by now, so both rounds load collapsed (hidden).
    page.reload(); page.wait_for_selector('.puzzle', state='attached')
    check('app links setting survived reload', page.is_checked('text=Use app links'))
    check('popup setting reached the other tab', other.input_value('.solve-settings select') == 'toast')
    set_answers(page, {'Shipping Containers': ''})
    page.wait_for_timeout(POLL_WAIT_MS)  # let the page see it unsolved
    set_answers(page, {'Shipping Containers': 'AGAIN'})
    page.wait_for_selector('.toast-popup .solved-puzzle', timeout=POLL_WAIT_MS)
    check('re-solve after unsolving notifies again, as a toast', page.locator('.modal').count() == 0)
    shot(page, '5-toast')

with sync_playwright() as p:
    context = p.chromium.launch().new_context(viewport={'width': 1400, 'height': 900})
    context.add_init_script(COUNT_PLAYS)
    page = context.new_page()
    watch(page, 'tab 1')
    page.goto(f'{base}/accounts/login/?next=/')
    page.fill('#id_username', 'admin'); page.fill('#id_password', 'admin')
    page.click('button[type=submit]')
    page.wait_for_selector('.puzzle')
    other = context.new_page()
    watch(other, 'tab 2')
    other.goto(f'{base}/'); other.wait_for_selector('.puzzle')
    page.bring_to_front()
    print('puzzles shown:', page.locator('.puzzle').count())
    shot(page, '1-index')
    page.click('#nav-menu')
    page.wait_for_selector('.dropdown-menu', state='visible')
    shot(page, '2-menu')
    page.click('#nav-menu')
    check_solve_notifications(page, other)
    page.fill('input[type=search]', 'logic')
    print('puzzles after filter "logic":', page.locator('.puzzle').count())
    shot(page, '6-filtered')
    page.fill('input[type=search]', '')
    check_puzzle_list(page)
    check_settings(page, other)
print('\n'.join(problems) or 'no console errors / failed requests / failed checks')
sys.exit(1 if problems else 0)
