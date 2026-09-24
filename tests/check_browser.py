"""Optional UI regression check: python3 tests/check_browser.py (requires Playwright and Chrome)."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome')
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((root / 'docs/index.html').as_uri())
    assert page.locator('.chapter:visible').count() == 1
    assert page.locator('.chapter').count() == 9
    page.screenshot(path='/tmp/tutorial-desktop.png', full_page=True)
    assert page.locator('.image-wide').count() == 34
    assert page.locator('.image-inline').count() == 4
    title_box = page.locator('.chapter:visible h1').bounding_box()
    wide_box = page.locator('.chapter:visible .image-wide').first.bounding_box()
    assert wide_box['width'] > title_box['width']
    assert abs(title_box['x'] + title_box['width']/2 - wide_box['x'] - wide_box['width']/2) < 1
    assert page.locator('.screenshot').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(255, 255, 255)'
    page.locator('.chapter:visible .next').click()
    expect(page.locator('.chapter:visible h1')).to_have_text('Connecting external tools (Plugins)')
    page.go_back()
    expect(page.locator('.chapter:visible h1')).to_have_text('What is agentic AI?')
    page.locator('.chapter:visible .prompt').first.click()
    expect(page.locator('.chapter:visible .copy-label').first).to_have_text('Copied')
    page.locator('.chapter:visible .screenshot').first.click()
    assert page.locator('dialog').is_visible()
    page.locator('dialog img').click()
    expect(page.locator('dialog')).not_to_be_visible()
    page.locator('.chapter:visible .screenshot').first.click()
    page.mouse.click(1, 1)
    expect(page.locator('dialog')).not_to_be_visible()
    page.locator('.chapter:visible .screenshot').first.click()
    page.keyboard.press('Escape')
    assert not page.locator('dialog').is_visible()
    for link in page.locator('.rail a').all():
        link.click()
        expect(link).to_have_attribute('aria-current', 'step')
        for figure in page.locator('.chapter:visible .image-inline').all():
            assert figure.bounding_box()['width'] <= 680
        for img in page.locator('.chapter:visible img').all():
            img.scroll_into_view_if_needed()
            img.evaluate('(img) => img.decode()')
            assert img.evaluate('(img) => img.naturalWidth > 0')
    page.reload()
    expect(page.locator('.chapter:visible h1')).to_have_text('Extending your process')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.select_option('#chapter-select', 'what-is-agentic-ai')
    expect(page.locator('.chapter:visible h1')).to_have_text('What is agentic AI?')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path='/tmp/tutorial-mobile.png', full_page=True)
    page.set_viewport_size({'width': 320, 'height': 800})
    for option in page.locator('#chapter-select option').all():
        page.select_option('#chapter-select', option.get_attribute('value'))
        expect(page.locator('.chapter:visible')).to_have_attribute('id', option.get_attribute('value'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
    print('Passed: nine chapters, all screenshots, copy, zoom/Escape, history, persistence, mobile navigation and overflow.')
