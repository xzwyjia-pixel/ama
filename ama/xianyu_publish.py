"""Auto-publish to Xianyu via web browser — fully automated version.

Opens Chrome, waits for you to login, then auto-fills product form.
No terminal interaction needed — just login in the browser.

The browser stays open after filling. Review and click Publish yourself.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json, time, os
from pathlib import Path
from playwright.sync_api import sync_playwright

data = json.loads(
    Path('c:/Users/25454/业务中控台/ama/output/listings/all_listings.json')
    .read_text(encoding='utf-8')
)

PRODUCTS = [
    {
        'pid': 'ai-tool-suite', 'name': 'AI Tool Suite v1.0',
        'price': '79',
        'images': ['01-主图.png', '02-功能总览.png', '03-价格对比.png', '04-信任与售后.png'],
    },
    {
        'pid': 'ai-roundtable', 'name': 'AI Roundtable',
        'price': '39',
        'images': ['roundtable-01-主图.png', 'roundtable-02-功能详解.png', 'roundtable-03-适用场景.png', 'roundtable-04-信任背书.png'],
    },
    {
        'pid': 'platform-review-rules', 'name': '平台审核规则库',
        'price': '19',
        'images': ['rules-main.png'],
    },
]

IMG_DIR = 'c:/Users/25454/业务中控台/ama/output/product-images'


def get_xianyu_listing(pid):
    for l in data.get(pid, []):
        if l['platform'] == '闲鱼':
            return l
    return None


def try_fill_form(page, listing, price):
    """Try to fill the publish form with various selector strategies."""
    print('  Scanning form fields...')

    # Dump page structure to help debug
    form_info = page.evaluate('''() => {
        const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        return Array.from(inputs).map(e => ({
            tag: e.tagName,
            type: e.type || '',
            placeholder: e.placeholder || '',
            name: e.name || '',
            id: e.id || '',
            class: e.className || '',
            visible: e.offsetParent !== null
        }));
    }''')
    for f in form_info:
        if f['visible']:
            print(f'    [{f["tag"]}] placeholder="{f["placeholder"]}" name="{f["name"]}" id="{f["id"]}"')

    # Title
    title_filled = False
    for sel in [
        'input[placeholder*="标题"]',
        'input[name*="title"]',
        'textarea[placeholder*="标题"]',
        '[class*="title"] input',
        '#title',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.click()
                el.fill('')
                el.fill(listing['title'])
                print(f'  TITLE: {listing["title"][:50]}')
                title_filled = True
                break
        except:
            continue

    if not title_filled:
        # Try to find by label text
        try:
            page.locator('text=标题').locator('..').locator('input, textarea').first.fill(listing['title'])
            print(f'  TITLE (by label): {listing["title"][:50]}')
            title_filled = True
        except:
            print('  WARNING: Could not find title field')

    # Description
    desc_filled = False
    for sel in [
        'textarea[placeholder*="描述"]',
        'textarea[placeholder*="正文"]',
        'textarea[name*="desc"]',
        'textarea[name*="content"]',
        '[class*="desc"] textarea',
        '[class*="content"] textarea',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.click()
                el.fill('')
                el.fill(listing['description'])
                print(f'  DESC: {len(listing["description"])} chars')
                desc_filled = True
                break
        except:
            continue

    if not desc_filled:
        try:
            # Find the largest visible textarea
            textareas = page.locator('textarea').all()
            biggest = None
            biggest_size = 0
            for ta in textareas:
                try:
                    box = ta.bounding_box()
                    if box and box['width'] * box['height'] > biggest_size:
                        biggest_size = box['width'] * box['height']
                        biggest = ta
                except:
                    pass
            if biggest:
                biggest.fill(listing['description'])
                print(f'  DESC (largest textarea): {len(listing["description"])} chars')
                desc_filled = True
        except:
            print('  WARNING: Could not find description field')

    # Price
    price_filled = False
    for sel in [
        'input[placeholder*="价格"]',
        'input[name*="price"]',
        'input[type="number"]',
        '[class*="price"] input',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.fill(price)
                print(f'  PRICE: {price}')
                price_filled = True
                break
        except:
            continue

    # Tags
    tag_text = ' '.join(listing.get('tags', []))
    for sel in [
        'input[placeholder*="标签"]',
        'input[name*="tag"]',
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.fill(tag_text)
                print(f'  TAGS: {tag_text}')
                break
        except:
            continue

    # Upload images
    file_input = page.locator('input[type="file"]').first
    try:
        if file_input.count() > 0:
            for img in product['images']:
                img_path = f'{IMG_DIR}/{img}'
                if os.path.exists(img_path):
                    file_input.set_input_files(img_path)
                    print(f'  IMG: {img}')
                    time.sleep(0.8)
    except:
        print('  WARNING: Could not upload images automatically')

    print('  FORM FILLED — review and click Publish!')


def main():
    product = PRODUCTS[0]  # Start with AI Tool Suite
    listing = get_xianyu_listing(product['pid'])

    if not listing:
        print('No listing data found!')
        return

    print(f'=== Publishing: {product["name"]} ===')
    print(f'Price: {product["price"]}')
    print(f'Title: {listing["title"]}')
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 900},
        )
        page = context.new_page()

        # Go directly to Xianyu homepage
        print('Opening Xianyu...')
        page.goto('https://www.goofish.com', timeout=30000)

        # Wait for login — detect by looking for user avatar/menu
        print('Waiting for login... (login in the browser)')
        print('Looking for: QR code scan, or phone login...')

        # Wait up to 5 minutes for login
        logged_in = False
        for i in range(150):
            time.sleep(2)
            try:
                # Check if we're logged in by looking for user elements
                has_user = page.evaluate('''() => {
                    return !!(
                        document.querySelector('[class*="avatar"]') ||
                        document.querySelector('[class*="user"]') ||
                        document.querySelector('img[src*="avatar"]') ||
                        document.querySelector('.login-user') ||
                        document.querySelector('[data-spm*="user"]')
                    );
                }''')
                if has_user:
                    logged_in = True
                    print('Login detected!')
                    break
            except:
                pass
            if i % 15 == 0:
                print(f'  Still waiting... ({i*2}s)')

        if not logged_in:
            print('Login not detected. Continuing anyway...')

        # Navigate to publish page
        print('Going to publish page...')
        try:
            page.goto('https://www.goofish.com/publish', timeout=15000)
        except:
            # Try alternative URLs
            for url in [
                'https://2.taobao.com/publish',
                'https://www.goofish.com/im/publish',
            ]:
                try:
                    page.goto(url, timeout=10000)
                    print(f'  Navigated to: {url}')
                    break
                except:
                    continue

        time.sleep(3)

        # Try to click "publish" or "sell" button if we're not already on the form
        try:
            for text in ['发布闲置', '卖闲置', '发布']:
                btn = page.locator(f'text={text}').first
                if btn.is_visible():
                    btn.click()
                    print(f'  Clicked: {text}')
                    time.sleep(2)
                    break
        except:
            pass

        # Fill the form
        try_fill_form(page, listing, product['price'])

        # Keep browser open for review
        print()
        print('=' * 50)
        print('BROWSER WILL STAY OPEN')
        print('Review the listing, upload images if needed,')
        print('then click Publish yourself.')
        print()
        print(f'Next products ready:')
        for p in PRODUCTS[1:]:
            l = get_xianyu_listing(p['pid'])
            if l:
                print(f'  {p["name"]}: {p["price"]}yuan — "{l["title"][:40]}"')
        print('=' * 50)

        # Keep alive
        try:
            input('Press Enter to close browser...')
        except:
            # No stdin — just keep browser open
            print('(Browser stays open. Close it manually when done.)')
            while True:
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    break

        browser.close()


if __name__ == '__main__':
    main()
