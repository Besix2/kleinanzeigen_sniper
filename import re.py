import re
from playwright.sync_api import Playwright, sync_playwright, expect
import os


class kleinanzeigen_monitor:
    def __init__(self, playwright: Playwright, link):
        self.browser = playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.link = link
        self.seen_ids = set()
        self.cookie_accepted = False
        self.first_start = True
        #initialize cache------------------------------------------------
        self.cache_name = str(self.link).split("/")[-2]
        self.id_folder = "cached_ids"
        self.full_cache_path = os.path.join(self.id_folder, self.cache_name)
        os.makedirs(self.id_folder, exist_ok=True)

    def check_link(self):
        # go to given link
        self.page.goto(self.link)
        # try to accept cookie banner
        if self.cookie_accepted:
            return
        print("Trying to accept cookies")
        try:
            self.page.get_by_test_id(
                "gdpr-banner-accept"
            ).click()  # accept cookie banner
            self.cookie_accepted = True
        except Exception as e:
            print(e)
        self.first_start = False
        listings_parent = self.page.locator("#srchrslt-content")
        listings = listings_parent.locator('//*[@id="srchrslt-adtable"]')
        listings_list = listings.locator("li")
        for li in listings_list.all():
            headline = li.locator("h2 > a").first
            if headline.count() > 0:
                headline_text = headline.get_attribute("href")
                # getting the actuall ID
                id_part = str(headline_text).split("/")[-1]
                clean_id = id_part.split("-")[0]
                self.seen_ids.add(clean_id)
            else:
                continue
        self.write_cache()
        
        
    def write_cache(self): #write cache
        with open(self.full_cache_path, "w") as f:
            for id in self.seen_ids:
                f.write(f"{id}\n")
                
                
                
    def offer_observer(self):

        pass


def main():
    with sync_playwright() as p:
        link = "https://www.kleinanzeigen.de/s-preis:2000:4000/gasgas-ec-250/k0"
        mein_bot = kleinanzeigen_monitor(p, link)
        mein_bot.check_link()


main()
