"""
Scraper for Massachusetts Supreme Court
CourtID: mass
Court Short Name: MS
Author: Andrei Chelaru
Court Contact: SJCReporter@sjc.state.ma.us (617) 557-1030
Reviewer: mlr
History:
 - 2014-07-12: Created.
 - 2014-08-05, mlr: Updated regex.
 - 2014-09-18, mlr: Updated regex.
 - 2016-09-19, arderyp: Updated regex.
 - 2017-11-29, arderyp: Moved from RSS source to HTML
    parsing due to website redesign
 - 2023-01-28, William Palin: Updated scraper
"""

import re
from datetime import datetime

import requests
from typing_extensions import override

from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    """
    Backscraper is implemented on `united_states_backscrapers.state.mass.py`
    """

    court_identifier = "SJC"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = "https://www.mass.gov/info-details/new-opinions"
        self.court_id = self.__module__
        self.court_identifier = "SJC"
        self.request["headers"] = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
        }
        self.proxies = {
            'http': 'http://192.126.182.41:8800', 'https': 'http://192.126.182.41:8800', }
        self.needs_special_headers = True

    def _process_html(self):
        for row in self.html.xpath(".//a/@href[contains(.,'download')]/.."):
            url = row.get("href")
            content = row.text_content()
            m = re.search(r"(.*?) \((.*?)\)( \((.*?)\))?", content)
            if not m:
                continue
            name, docket, _, date = m.groups()
            if self.court_identifier not in docket:
                continue
            if date == None:
                # Likely a new case opinion - check the header text above it
                if row.xpath(".//../../h3/text()"):
                    header_text = row.xpath(".//../../h3/text()")[0]
                    date = header_text.split("Decisions:")[1].strip()
                if not date:
                    # if no date is found skip it
                    continue

            if not str(url).__contains__("https://www.mass.gov/"):
                url="https://www.mass.gov"+url
            # print(url)
            self.cases.append(
                {
                    "name": name,
                    "status": "Published",
                    "date": date,
                    "docket": [docket],
                    "url": url,
                }
            )

    @override
    def _request_url_get(self, url):
        """Execute GET request and assign appropriate request dictionary
        values
        """
        self.request["response"] = requests.get(
            url=url,
            # headers=self.request["headers"],
            verify=self.request["verify"],
            proxies=self.proxies,
            timeout=60,
        )

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return 0

    def get_court_name(self):
        return "Supreme Judicial Court of Massachusetts"

    def get_class_name(self):
        return "mass"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Massachusetts"

