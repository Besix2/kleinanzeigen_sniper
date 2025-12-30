import re
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright, search_link) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(search_link)
    page.get_by_test_id("gdpr-banner-accept").click()