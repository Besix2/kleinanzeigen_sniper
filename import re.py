from playwright.sync_api import Playwright, sync_playwright, expect
import os
import random
import time
import json
from groq import Groq
from dotenv import load_dotenv
import yaml
from datetime import datetime
import requests


class kleinanzeigen_monitor:
    def __init__(self, playwright: Playwright, link, categorie_for_this_instance):
        # load api keys
        load_dotenv() 
        #generall stuff
        self.categorie = categorie_for_this_instance
        #load playwright
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
        #os.makedirs(self.id_folder, exist_ok=False)
        self.cache = {}
        #load cache
        self.scanned_offers = self.load_cache()
        #load ai
        self.ai = AiAnalyst()
        
    def initial_scan(self):
        print("Initial scan")
        initial_scanned_offers = self.check_link() #first scan to actually fill the cache
        self.write_cache(initial_scanned_offers)
        
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
        scanned_offers = {}
        # go to given link
        self.page.goto(self.link)
        # try to accept cookie banner
        if self.cookie_accepted:
            pass
        else:
            print("Trying to accept cookies")
            try:
                self.page.get_by_test_id(
                    "gdpr-banner-accept"
                ).click()  # accept cookie banner
                self.cookie_accepted = True
            except Exception as e:
                print(e)
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
                scanned_offers.update(offer_data)
            else:
                continue
        return scanned_offers

    def write_cache(self, data):  # write cache
        self.load_cache()
        if not os.path.exists(self.full_cache_path):
            return{}
        new_id_check= data.keys() - self.cache.keys() #checking if id is new
        if len(new_id_check) == 0:
            print("Already cached. Skipping")
            pass
        else:
            self.cache.update(data)
            with open(self.full_cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4, ensure_ascii=False)

                
    def offer_getter(self, new_offer_link):
        print("Scanning new offer...")
        new_offer_link
        #offer_link = list(new_offer_data.values())[1]
        full_link = f"https://kleinanzeigen.de{new_offer_link}"
        self.page.goto(full_link)
        self.page.get_by_test_id("gdpr-banner-accept").click()  # accept cookie banner
        details_div = self.page.locator('//*[@id="viewad-details"]/div')
        details_div_lis = details_div.locator("li")
        offer_details_list = ""
        for li in details_div_lis.all():
            offer_details_list = f"{offer_details_list} \n" + str(li.inner_text())
            #print(f"{li.inner_text()}")
        offer_description = self.page.locator('//*[@id="viewad-description-text"]')
        #print(offer_description.inner_text())
        ai_data = offer_description.inner_text() + "\n" + offer_details_list + str(new_offer_link)
        Ai_result = self.ai.analyze(ai_data, self.categorie)
        #getting seller score
        
        badges_locator = self.page.locator(".userbadge-tag")
        
        all_ratings = badges_locator.all_inner_texts()
        clean_ratings = [text.strip() for text in all_ratings]
        #getting account creation date
        account_creation_date = self.page.locator(".userprofile-vip-details-text" , has_text="Aktiv seit").inner_text().strip()
        date_str = account_creation_date.replace("Aktiv seit", "").strip()
        account_date = datetime.strptime(date_str, "%d.%m.%Y") #getting clean account creation date
        now = datetime.now()#getting current date
        #tranforming into year difference
        delta = now - account_date
        days_active = delta.days
        years_active = days_active / 365.25
        #score system for account creation date(youger accounts are more suspicious especially really new ones)
        if days_active < 30:
        # younger than 1 month
            score = 0
            
        elif years_active >= 3:
            # older than 3 years
            score = 50
            
        elif years_active >= 2:
            # older than 2 years
            score = 30
            
        elif years_active >= 1:
            # older than 1 year
            score = 20
            
        else:
            #older than one month
            score = 10
        if "sehr gut" in clean_ratings[0].lower():
            score += 30
        elif "ok" in clean_ratings[0].lower():
            score += 10
        
        if len(clean_ratings) == 3:
            score += 20
        elif len(clean_ratings) == 2:
            score += 10
        print(Ai_result, score)
        return Ai_result, score
        
        
        
        #return(Ai_result)

    def offer_observer(self):
        print("starting Tracking of new offers")
        while True:
            try:
                scanned_offers = self.check_link()
                new_ids = scanned_offers - self.cache.keys()
                if len(new_ids) == 0:
                    print("No new Listings found. Sleeping again.")
                    wait_time = random.uniform(60, 120)
                    time.sleep(wait_time)
                    
                else:
                    for o in new_ids:
                        offer_link = scanned_offers[new_ids[o]] #getting the link from the new offer
                        Ai_result, seller_score = self.offer_getter(offer_link)
                        
                        
            except Exception as e:
                print(e)
    def notifyer(self, Ai_result, seller_score):
        pass
        #sends message to your phone about new offer
class AiAnalyst:
    def __init__(self):
        print("Loading config...")
        with open("config.yaml") as f:
            self.config = yaml.safe_load(f) #load yaml config
        #loading api key
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    def get_prompt(self, categorie): #function to choose prompt based on categorie
        return self.config.get(categorie)
    
    def analyze(self, text, categorie="default"):
        print("starting analyszes")
        system_prompt = self.get_prompt(categorie)
        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama-3.1-8b-instant",
        )
        print("finished analyzes")
        return chat_completion.choices[0].message.content

def main():
    with sync_playwright() as p:
        #link = "https://www.kleinanzeigen.de/s-preis:2000:4000/gasgas-ec-250/k0"
        link = "/s-anzeige/gasgas-ec-250-enduro-baujahr-2008-belgische-papiere/3284149557-305-7455"
        mein_bot = kleinanzeigen_monitor(p, link, "motorrad")
        #mein_bot.offer_observer()
        mein_bot.offer_getter(link)


main()
