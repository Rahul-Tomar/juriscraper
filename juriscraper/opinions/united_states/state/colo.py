"""Scraper for Colorado Supreme Court
CourtID: colo
Court Short Name: Colo.
Author: Philip Ardery
Reviewer: mlr
Date created: 2016-06-03
History:
    - 2022-01-31: Updated by William E. Palin
    - 2023-01-05: Updated by WEP
    - 2023-11-19: Drop Selenium by WEP
    - 2023-12-20: Updated with citations, judges and summaries, Palin
    - 2024-07-04: Update to new site, grossir
"""
import re
from datetime import date, datetime, timedelta
from typing import Tuple
from urllib.parse import urlencode
from juriscraper.lib.string_utils import convert_date_string
import requests

from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    base_url = "https://research.coloradojudicial.gov/search.json"
    detail_url = (
        "https://research.coloradojudicial.gov/vid/{}.json?"
        "include=abstract%2Cparent%2Cmeta%2Cformats%2Cchildren%2Cproperties_with_ids%2Clibrary%2Csource"
        "&fat=1&locale=en&hide_ct6=true&t={}"
    )
    base_html_url = "https://research.coloradojudicial.gov/en/vid/"
    days_interval = 30
    first_opinion_date = datetime(2010, 1, 1)
    api_court_code = "14024_01"
    status = "Published"


    def _fetch_duplicate(self, data):
        query_for_duplication = {
            "pdf_url": data.get("pdf_url"),
            "docket": data.get("docket"),
            "title": data.get("title"),
            "citation": data.get("citation"),
        }
        duplicate = self.judgements_collection.find_one(query_for_duplication)
        object_id = None
        if duplicate is None:
            self.judgements_collection.insert_one(data)
            updated_data = self.judgements_collection.find_one(query_for_duplication)
            object_id = updated_data.get("_id")
            self.flag = True
        else:
            processed = duplicate.get("processed")
            if processed == 10:
                raise Exception("Judgment already Exists!")
            else:
                object_id = duplicate.get("_id")
        return object_id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        print(type(self).status)
        print(type(self).api_court_code)
        self.params = {
            "product_id": "WW",
            "jurisdiction": "US",
            "content_type": "2",
            "court": self.api_court_code,
            "publication_status": type(self).status,
            "bypass_rabl": "true",
            "include": "parent,abstract,snippet,properties_with_ids",
            "per_page": "30",
            "sort": "date",
            "include_local_excluive": "true",
            "cbm": "6.0|361.0|5.0|9.0|4.0|2.0=0.01|400.0|1.0|0.001|1.5|0.2",
            "locale": "en",
            "hide_ct6": "true",
            "t": str(datetime.now().timestamp())[:10],
            "type": "document",
        }
        self.url = f"{self.base_url}?{urlencode(self.params)}"
        print(f"[INIT] Base URL initialized:\n{self.url}\n")

        self.request["headers"].update(
            {
                "X-Requested-With": "XMLHttpRequest",
                "X-Root-Account-Email": "colorado@vlex.com",
                "X-User-Email": "colorado@vlex.com",
                "X-Webapp-Seed": "9887408",
            }
        )
        self.expected_content_types = ["text/html"]
        self.make_backscrape_iterable(kwargs)

    def _process_html(self) -> None:
        search_json = self.html
        total_results = search_json.get("count", 0)
        # Create a total-counter the first time function runs
        if not hasattr(self, "processed_total"):
            self.processed_total = 0

        logger.info(
            "Number of results %s; %s in page",
            search_json.get("count"),
            len(search_json.get("results", [])),
        )
        print(f"[PROCESS_HTML] Found {search_json.get('count')} total results.")
        case_pattern = r"\b\d+[A-Z]+\d+\b"

        for i, result in enumerate(search_json.get("results", []), start=1):
            if self.processed_total >= total_results:
                print(f"🚫 Stopping — reached total_results={total_results}")
                return
            print(f"\n=== Processing case {i} ===")
            case_id = result.get("id")
            print("Case ID:", case_id)
            timestamp = str(datetime.now().timestamp())[:10]
            url = self.detail_url.format(case_id, timestamp)
            # print("Detail URL:", url)

            html_url = f"{self.base_html_url}{case_id}"
            html_content_url = f"{self.base_html_url}{case_id}/content"
            # print("Fetching HTML content:", html_content_url)
            html_res = requests.get(
                html_content_url, headers=self.request["headers"], proxies=self.proxies
            )
            # print("HTML content fetched, length:", len(html_res.text))

            if self.test_mode_enabled():
                detail_json = result["detail_json"]
            else:
                self._request_url_get(url)
                detail_json = self.request["response"].json()

            citation = parallel_citation = docket_number = case_name_full = date_filed = ""

            for p in detail_json.get("properties", []):
                label = p["property"]["label"]
                values = p.get("values", [])
                if label == "Docket Number" and values:
                    docket_number = values[0]
                elif label == "Parties" and values:
                    case_name_full = values[0]
                elif label == "Decision Date" and values:
                    date_filed = values[0]
                elif label == "Citation" and values:
                    citation = values[0]
                    parallel_citation = values[1:] if len(values) > 1 else []

            print("Raw date filed:", date_filed)
            # print("Docket number:", docket_number)
            # print("Case name:", case_name_full)
            # print("Citation:", citation)
            # print("Parallel citation:", parallel_citation)

            try:
                curr_date_obj = convert_date_string(date_filed)
                parse_date = curr_date_obj.strftime("%d/%m/%Y")
                curr_date = curr_date_obj.strftime("%Y-%m-%d")
                print("Converted date:", curr_date)
            except Exception as e:
                print(f"Error converting date '{date_filed}':", e)
                continue

            try:
                res = CasemineUtil.compare_date(self.crawled_till, parse_date)
                print(f"Date comparison: crawled_till={self.crawled_till}, case_date={curr_date}, result={res}")
            except Exception as e:
                print("Error comparing date:", e)
                continue

            if res == 1:
                print("⚠️ Case date beyond crawled_till, skipping remaining cases.")
                return

            match = re.search(case_pattern, docket_number)
            docket_match = match.group() if match else docket_number

            case = {
                "date": date_filed,
                "docket": [docket_match],
                "name": case_name_full,
                "url": f"https://research.coloradojudicial.gov/pdf/{case_id}",
                "status": type(self).status,
                "citation": [citation],
                "parallel_citation": parallel_citation,
                "html_url": html_url,
                "response_html": html_res.text,
            }
            print(f"✅ Case appended: {case['docket']} | {case['name']} | {case['date']}")
            self.cases.append(case)

    def _download_backwards(self, dates: Tuple[date]) -> None:
        logger.info("Backscraping for range %s %s", *dates)
        print(f"\n[DOWNLOAD_BACKWARDS] Start: {dates[0]}, End: {dates[1]}")
        start = dates[0].strftime("%Y-%m-%d")
        end = dates[1].strftime("%Y-%m-%d")
        timestamp = str(datetime.now().timestamp())[:10]
        params = {**self.params}
        params.update(
            {
                "date": f"{start}..{end}",
                "locale": ["en", "en"],
                "hide_ct6": ["true", "true"],
                "t": [timestamp, timestamp],
            }
        )

        page = 1
        while True:
            params["page"] = str(page)
            self.url = f"{self.base_url}?{urlencode(params)}"
            print(f"\n[PAGE {page}] Fetching URL:\n{self.url}\n")

            try:
                self.html = self._download()
                logger.info(f"Loading page {page}")

                search_json = self.html
                print(f"[PAGE {page}] Result count: {search_json.get('count', 'N/A')}")

                if not search_json.get("results"):
                    print(f"[PAGE {page}] No more results. Stopping.")
                    break

                self._process_html()
                page += 1
                if page>5:
                    return

            except Exception as e:
                logger.error(f"Error loading page {page}: {e}")
                print(f"⚠️ Error on page {page}: {e}. Skipping.")
                page += 1
        logger.info("Finished backscraping for range %s to %s", start, end)
        print(f"[DONE] Finished backscraping {start} → {end}")

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        print(f"\n[CRAWLING RANGE] From {start_date} to {end_date}")
        self._download_backwards((start_date, end_date))
        self.parse()
        # print(f"\n[SUMMARY] Total cases parsed: {len(self.cases)}")
        return len(self.cases)

    def get_class_name(self):
        return "colo"

    def get_court_name(self):
        return "Colorado Supreme Court"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Colorado"
