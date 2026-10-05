"""
Drive the Herring UI in headless Chromium: log in, screenshot, use the menu,
edit an answer, filter, and check a UI setting survives a reload. Exits
nonzero on browser console errors/warnings, page errors, or failed requests.
Run by scripts/ui-test.sh; usage: browse.py BASE_URL OUTPUT_PREFIX
"""
import sys
from playwright.sync_api import sync_playwright

base, out = sys.argv[1], sys.argv[2]
problems = []

def shot(page, name):
    page.screenshot(path=f'{out}-{name}.png', full_page=True)

with sync_playwright() as p:
    page = p.chromium.launch().new_page(viewport={'width': 1400, 'height': 900})
    page.on('console', lambda m: m.type in ('error', 'warning') and problems.append(f'console {m.type}: {m.text}'))
    page.on('pageerror', lambda e: problems.append(f'pageerror: {e}'))
    page.on('response', lambda r: r.status >= 400 and problems.append(f'HTTP {r.status} {r.url}'))
    page.goto(f'{base}/accounts/login/?next=/')
    page.fill('#id_username', 'admin'); page.fill('#id_password', 'admin')
    page.click('button[type=submit]')
    page.wait_for_selector('.puzzle')
    print('puzzles shown:', page.locator('.puzzle').count())
    shot(page, '1-index')
    page.click('#nav-menu')
    page.wait_for_selector('.dropdown-menu', state='visible')
    shot(page, '2-menu')
    page.click('#nav-menu')
    page.locator('.puzzle', has_text='Anagram Antics').locator('.answer').click()
    page.keyboard.type('NEWANSWER'); page.keyboard.press('Enter')
    page.wait_for_selector('.celebration', timeout=15000)
    shot(page, '3-celebration')
    page.click('.close-button')
    page.fill('input[type=search]', 'logic')
    print('puzzles after filter "logic":', page.locator('.puzzle').count())
    shot(page, '4-filtered')
    page.check('text=Use app links')
    page.reload(); page.wait_for_selector('.puzzle')
    print('app links setting survived reload:', page.is_checked('text=Use app links'))
print('\n'.join(problems) or 'no console errors / failed requests')
sys.exit(1 if problems else 0)
