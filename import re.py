import re
from playwright.sync_api import Playwright, sync_playwright, expect

class kleinanzeigen_monitor:
    def __init__(self, playwright: Playwright, link):
        self.browser = playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.link = link
        self.seen_ids = set()
        self.cookie_accepted = False
        

    def check_link(self):
        #go to given link
        self.page.goto(self.link) 
        #try to accept cookie banner
        if self.cookie_accepted:
            return 
        print("Trying to accept cookies")
        try:
            self.page.get_by_test_id("gdpr-banner-accept").click() #accept cookie banner
            self.cookie_accepted = True
        except Exception as e:
            print(e)

        listings_parent = self.page.locator("#srchrslt-content")
        listings = listings_parent.locator('//*[@id="srchrslt-adtable"]')
        listings_list = listings.locator("li")
        print(listings_list.all())
        for li in listings_list.all():
            headline = li.locator('h2 > a')
            print(headline.get_attribute("href"))
        test = "test"


        
def main():
    with sync_playwright() as p:
        link = "https://www.kleinanzeigen.de/s-motorraeder-roller/preis:2000:4200/husqvarna-fe-250/k0c305"       
        mein_bot = kleinanzeigen_monitor(p, link)
        mein_bot.check_link()
            
main()


    