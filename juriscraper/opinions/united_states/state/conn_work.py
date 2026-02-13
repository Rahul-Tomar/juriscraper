from datetime import datetime

import requests
import re

from bs4 import BeautifulSoup

from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from casemine.casemine_util import CasemineUtil

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.url = "https://portal.ct.gov/wcc/home-news/workers-compensation-news/crb-opinions-posted?language=en_US"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Host": "portal.ct.gov",
            "Priority": "u=0, i",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }

    def _download(self, request_dict={}):
        pass

    def _process_html(self):
        response = requests.get(url=self.url,headers=self.headers,proxies=self.proxies)
        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for content_div in soup.select("div.content"):
            # Each opinion is inside <li>
            for li in content_div.select("ul > li"):
                a_tag = li.select_one("a[href]")
                span = li.select_one("span")

                if not a_tag or not span:
                    continue

                title = a_tag.get_text(strip=True)
                pdf_url = a_tag["href"].strip()
                meta_text = span.get_text(" ", strip=True)
                docket , date = self.data_cleaner(meta_text)
                if not title or not pdf_url or not date or not docket:
                    raise Exception("REquired Field is missing " )
                self.cases.append({
                     "name": title,
                     "url": pdf_url,
                     "docket": docket,
                     "date": date
                })

                print({
                    "name": title,
                    "url": pdf_url,
                    "docket": docket,
                    "date":date,
                    "status":self.status
                })

    def data_cleaner(self, text: str):
        docket = None
        date = None

        # Normalize whitespace
        text = " ".join(text.split())

        # -------------------------
        # Extract docket(s)
        # Handles: Case No. / CASE NO. / Case Nos.
        # -------------------------
        docket_match = re.search(
            r"Case\s+No[s]?\.\s*([^:]+)",
            text,
            re.IGNORECASE
        )

        if docket_match:
            docket = docket_match.group(1).strip()

        # -------------------------
        # Extract date (any month casing)
        # -------------------------
        date_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            text,
            re.IGNORECASE
        )

        if date_match:
            normalized_date = date_match.group(0).title()
            date = datetime.strptime(
                normalized_date, "%B %d, %Y"
            ).strftime("%d/%m/%Y")
        else:
            # REQUIRED fallback for Juriscraper
            date = self.crawled_till

        return docket, date

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return len(self.cases)

    def get_class_name(self):
        return 'conn_work'

    def get_court_name(self):
        return "CONNECTICUT COMPENSATION REVIEW BOARDCONNECTICUT WORKERS' COMPENSATION COMMISSION"

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Connecticut'
