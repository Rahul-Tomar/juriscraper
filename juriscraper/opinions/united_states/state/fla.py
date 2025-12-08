# Scraper for Florida Supreme Court
# CourtID: fla
# Court Short Name: fla

from datetime import date, datetime, timedelta
from typing import Optional, Tuple
import requests

from bs4 import BeautifulSoup
from lxml import html

from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    # make a backscrape request every `days_interval` range
    days_interval = 20
    first_opinion_date = datetime(1999, 9, 23)
    flag = True
    fl_court = "supreme_court"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"

        self.proxy = {
            "http": "http://192.126.184.28:8800",
            "https": "http://192.126.184.28:8800",
        }

        self.data = None
        self.make_backscrape_iterable(kwargs)

    # ----------------------------------------------------------------------
    # CUSTOM DOWNLOADER
    # ----------------------------------------------------------------------
    def _download(self, request_dict={}):
        """Download JSON with proxy"""
        response = requests.get(
            self.url,
            headers={"User-Agent": "Mozilla/5.0"},
            proxies=self.proxy,
            timeout=60
        )
        response.raise_for_status()
        self.data = response.json()
        return self.data     # ← MUST return JSON object

    # ----------------------------------------------------------------------
    # PARSER
    # ----------------------------------------------------------------------
    def _process_html(self) -> None:
        """Convert JSON into case dictionaries"""

        results = self.data.get("searchResults", [])
        total = self.data.get("total", 0)

        print(f"[INFO] Results on this page: {len(results)} / Total: {total}")

        for item in results:
            fields = item.get("content", {}).get("fields", {})

            raw_docket = fields.get("case_number", "")
            docket = self.normalize_docket(raw_docket)

            title = fields.get("case_style", "")
            disposition = fields.get("note", "")

            pdf_path = fields.get("opinion", {}).get("uri", "")
            pdf_url = f"https://supremecourt.flcourts.gov{pdf_path}" if pdf_path else ""

            # ---- DATE HANDLING ----
            raw_date = fields.get("disposition_date", {}).get("date", {}).get("date", "")
            parsed_date = None

            if raw_date:
                try:
                    parsed = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S.%f")
                    parsed_date = parsed.date()
                except:
                    try:
                        parsed = datetime.strptime(raw_date, "%Y-%m-%d")
                        parsed_date = parsed.date()
                    except Exception as e:
                        print(f"[WARN] Could not parse date: {raw_date}, error: {e}")

            # Juriscraper REQUIRES date STRING
            formatted_date = parsed_date.strftime("%Y-%m-%d") if parsed_date else ""
            self.cases.append({
                "docket": docket,
                "name": title,
                "disposition":disposition,
                "date": formatted_date,
                "url": pdf_url,
                "status": self.status,
            })

            # -------- PRINT DEBUG INFO --------
            print("-------------------------------")
            print(f"Title      : {title}")
            print(f"Docket     : {docket}")
            print(f"Date       : {formatted_date}")
            print(f"Disposition: {disposition}")
            print(f"PDF URL    : {pdf_url}")
            print("-------------------------------")


    def normalize_docket(self,docket_field):
        # Case 1: Already a list
        if isinstance(docket_field, list):
            return [d.strip() for d in docket_field if d.strip()]

        # Case 2: It's a single string
        if isinstance(docket_field, str):
            # Check if multiple dockets using "&"
            if "&" in docket_field:
                parts = docket_field.split("&")
                return [p.strip() for p in parts if p.strip()]
            else:
                return [docket_field.strip()]

        return []  # fallback


    # ----------------------------------------------------------------------
    # BACKSCRAPING
    # ----------------------------------------------------------------------
    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        """Main pagination loop"""

        limit = 100
        offset = 0
        flag = True

        sdate = start_date.strftime("%Y%m%d")
        # end_dat = datetime(2025, 10, 15)
        edate = end_date.strftime("%Y%m%d")
        # edate = end_dat.strftime("%Y%m%d")

        print(f"[INFO] Crawling from {sdate} to {edate}")

        while flag:

            self.url = (
                f"https://flcourts-media.flcourts.gov/_search/opinions?"
                f"query=&siteaccess=supreme2&searchtype=opinions"
                f"&startdate={sdate}&enddate={edate}"
                f"&limit={limit}&offset={offset}"
                f"&type=written&scopes[]={(type(self).fl_court)}"
            )

            print(f"[FETCH] {self.url}")

            self.parse()  # runs _download() and _process_html()

            # Pagination logic based on JSON
            result_count = len(self.data.get("searchResults", []))
            total = self.data.get("total", 0)

            if offset + limit >= total:
                flag = False
            else:
                offset += limit

        return 0

    # ----------------------------------------------------------------------

    def set_url(self, start: Optional[date] = None, end: Optional[date] = None):
        pass

    def get_state_name(self):
        return "Florida"

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court of Florida"

    def get_class_name(self):
        return "fla"
