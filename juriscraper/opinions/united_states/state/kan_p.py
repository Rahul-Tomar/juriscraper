# Scraper for Kansas Supreme Court (published)
# CourtID: kan_p
from datetime import datetime
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        # Old url by Deepak
        # self.url = "https://kscourts.gov/Cases-Decisions/Decisions"
        self.status = "Published"
        self.court = "Supreme Court"
        self.filter = 1
        self.courtFilter=10
        self.last_date = None
        self.prox = None  # optional proxy


    def _download(self):
        self.downloader_executed = True
        return None

    def _process_html(self):
        """Scrape the Kansas court website using Playwright and populate self.cases."""
        print("Starting Playwright scraping...")

        HEADLESS = True
        TIMEOUT_MS = 60000
        PROXY_SERVER = "http://192.126.182.31:8800"

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=HEADLESS, proxy={"server": PROXY_SERVER})
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            print(f"🌐 Navigating to: {self.url}")
            page.goto(self.url, timeout=TIMEOUT_MS)

            try:
                page.wait_for_selector("table#searchResultsTable", timeout=30000)
                print("✅ Results table detected.")
            except PlaywrightTimeoutError:
                print("⚠️ Timeout waiting for table.")
                context.close()
                browser.close()
                return

            all_rows = []
            page_number = 1

            while True:
                print(f"📄 Reading page {page_number}...")
                time.sleep(2)

                rows = page.query_selector_all("table#searchResultsTable tbody tr")
                if not rows:
                    print("⚠️ No rows found, stopping.")
                    break

                for row in rows:
                    cols = row.query_selector_all("td")
                    if not cols:
                        continue

                    text_values = [c.inner_text().strip() for c in cols]
                    # Extract PDF link from last column
                    pdf_link = None
                    last_col = cols[-1]
                    link_element = last_col.query_selector("a")
                    if link_element:
                        pdf_link = link_element.get_attribute("href")
                        pdf_link = "https://searchdro.kscourts.gov" + pdf_link

                    # Expected table format: [Date, CaseName, Docket, ...]
                    date = text_values[0]
                    docket = text_values[1]
                    name = text_values[2] if len(text_values) > 2 else ""
                    url = pdf_link

                    date = datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")
                    parse_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")

                    res = CasemineUtil.compare_date(self.crawled_till, parse_date)
                    if res == 1:
                        continue



                    print(date + " | " + name + " | " + docket  + " | " + url + " | " )
                    self.cases.append({
                        "date": date,
                        "name": name,
                        "docket": [docket],
                        "url": url,
                        "status": self.status,
                    })

                # Try clicking the next page
                next_button = page.query_selector("a.paginate_button.next:not(.disabled)")
                if not next_button:
                    print("✅ No more pages found, done.")
                    break

                next_button.click()
                try:
                    page.wait_for_selector("table#searchResultsTable tbody tr", timeout=10000)
                except PlaywrightTimeoutError:
                    print("⚠️ Timeout waiting for next page — stopping.")
                    break

                page_number += 1

            print(f"\n✅ Finished scraping. Total rows collected: {len(self.cases)}")

            context.close()
            browser.close()


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        # last_crawled = datetime.strptime("2025-04-01 00:00:00",
        #                                  "%Y-%m-%d %H:%M:%S")
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = datetime.now().strftime("%Y-%m-%d")

        self.url = (
            f"https://searchdro.kscourts.gov/Documents/Search"
            f"?StartDate={start_date_str}&EndDate={end_date_str}"
            f"&statusFilter={self.filter}&courtFilter={self.courtFilter}&Keyword="
        )
        print(self.url)
        self.parse()
        return 0

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Kansas"

    def get_class_name(self):
        return "kan_p"

    def get_court_name(self):
        return "Supreme Court of Kansas"
