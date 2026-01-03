from playwright.sync_api import Playwright, sync_playwright, expect
import os
import random
import time
import json


class kleinanzeigen_monitor:
    def __init__(self, playwright: Playwright, link):
        self.browser = playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.link = link
        self.cookie_accepted = False
        self.first_start = True
        # initialize cache------------------------------------------------
        self.cache_name =f"{str(self.link).split("/")[-2]}.json"
        self.id_folder = "cached_ids"
        self.full_cache_path = os.path.join(self.id_folder, self.cache_name)
        os.makedirs(self.id_folder, exist_ok=True)
        self.cache = {}
        #load cache
        self.scanned_offers = self.load_cache()

    def load_cache(self):
        #create new empty id cache
        if not os.path.exists(self.full_cache_path):
            print(f"Erstelle neue Datenbank: {self.cache_name}")
            with open(self.full_cache_path, "w", encoding="utf-8") as f:
                #writing empty directory
                json.dump({}, f)
        else:
            with open(self.full_cache_path, "r", encoding="utf-8") as f:
                try:
                    self.cache = json.load(f) # loading cache into self
                except json.JSONDecodeError:
                    self.cache = {} #if file is broken

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
                print(headline_text)
                # getting the actuall ID
                id_part = str(headline_text).split("/")[-1]
                clean_id = id_part.split("-")[0]
                offer_data = {}
                offer_data[clean_id] = str(headline_text)
                self.write_cache(offer_data)
            else:
                continue
        self.write_cache()

    def write_cache(self, data):  # write cache
        self.load_cache()
        if not os.path.exists(self.full_cache_path):
            return{}
        new_id_check= data.keys() - self.cache.keys()
        if len(new_id_check) == 0:
            print("Already cached. Skipping")
            pass
        else:
            self.cache.update(data)
            with open(self.full_cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4, ensure_ascii=False)

    def offer_observer(self):
        print("starting Tracking of new offers")
        
        while True:
            try:
                self.check_link()
                new_ids = self.scanned_ids - self.seen_ids
                if len(new_ids) == 0:
                    print("No new Listings found. Sleeping again.")
                    wait_time = random.uniform(60, 120)
                    time.sleep(wait_time)
                    
                else:
                    print(new_ids)
                    break
            except Exception as e:
                print(e)
        


def main():
    with sync_playwright() as p:
        link = "https://www.kleinanzeigen.de/s-preis:2000:4000/gasgas-ec-250/k0"
        mein_bot = kleinanzeigen_monitor(p, link)
        mein_bot.offer_observer()


main()
