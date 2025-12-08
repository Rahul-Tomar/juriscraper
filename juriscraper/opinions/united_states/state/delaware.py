"""Scraper for the Supreme Court of Delaware
CourtID: del

Creator: Andrei Chelaru
Reviewer: mlr
"""
from datetime import datetime
import requests
from fontTools.misc.plistlib import end_date
from lxml import html

from juriscraper.lib.string_utils import convert_date_string
from juriscraper.OpinionSite import OpinionSite


class Site(OpinionSite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court = "Supreme Court"
        self.dates = []
        self.urls = []
        self.names = []
        self.dockets = []
        self.status = []
        self.judges = []
        self.court_id = "juriscraper.opinions.united_states.state.del"
        self.proxies = {
            'http': 'http://192.126.184.28:8800',
            'https': 'http://192.126.184.28:8800',
        }

    def _get_case_dates(self):
        return self.dates

    def _get_download_urls(self):
        return self.urls

    def _get_case_names(self):
        return self.names

    def _get_docket_numbers(self):
        return self.dockets

    def _get_precedential_statuses(self):
        return ["Published"] * len(self.dates)

    def _get_judges(self):
        return self.judges

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        session = requests.Session()
        URL = "https://courts.delaware.gov/opinions/list.aspx"

        # Initial GET with proxies
        r = session.get(URL, proxies=self.proxies)
        tree = html.fromstring(r.text)
        viewstate = tree.xpath('//input[@id="__VIEWSTATE"]/@value')[0]
        viewstategen = tree.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')[0]

        if not viewstate or not viewstategen:
            raise Exception(
                "Cannot find __VIEWSTATE or __VIEWSTATEGENERATOR on initial page"
            )

        page = 1
        self.url = 'https://courts.delaware.gov/opinions/'
        self.method = 'POST'

        while True:
            print(f"[INFO] Processing page {page}")

            payload = {
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategen,
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "ctlOpinions1selAgencies": self.court,
                "ctlOpinions1selPeriods": "2025",
                "ctlOpinions1txtSearchText": "",
                "ctlOpinions1selResults": "25",
                "ctlOpinions1hdnAgency": self.court,
                "ctlOpinions1hdnCaseType": "",
                "ctlOpinions1hdnDivision": "",
                "ctlOpinions1hdnSortBy": "",
                "ctlOpinions1hdnSortOrder": "0",
                "ctlOpinions1hdnSortByNew": "",
                "ctlOpinions1hdnPageNo": str(page),
            }

            response = session.post(URL, data=payload, proxies=self.proxies)
            tree = html.fromstring(response.text)

            rows = tree.xpath("//table[contains(@class,'table')]/tbody/tr")
            if not rows:
                print(f"[INFO] No rows found on page {page}. Stopping.")
                break

            print(f"[INFO] Found {len(rows)} rows on page {page}")

            for row in rows:
                # Title
                title = row.xpath(".//td[1]/a/span/text()")
                self.names.append(title[0].strip() if title else "")
                print("Title:", self.names[-1])

                # URL
                url = row.xpath(".//td[1]/a/@href")
                if url:
                    href = url[0].strip()
                    if not href.startswith("https://courts.delaware.gov"):
                        href = "https://courts.delaware.gov" + href
                    self.urls.append(href)
                    # print(href)
                else:
                    self.urls.append("")
                # Date
                date = row.xpath(".//td[2]/text()")
                self.dates.append(convert_date_string(date[0].strip()) if date else "")
                # print(date)
                # Docket
                docket = row.xpath(".//td[3]/a/span/text()")
                # print(docket)
                if docket:
                    doc = docket[0].strip()
                    if "/" in doc:
                        doc_arr = doc.split("/")
                    elif "&" in doc:
                        doc_arr = doc.split("&")
                    else:
                        doc_arr = [doc]
                    new_doc = [i.strip() for i in doc_arr]
                    self.dockets.append(new_doc)
                else:
                    self.dockets.append([])

                # Judges
                judge = row.xpath(".//td[6]//text()")
                judge_clean = " ".join([j.strip() for j in judge if j.strip()])
                self.judges.append([judge_clean])

            next_viewstate = tree.xpath('//input[@id="__VIEWSTATE"]/@value')
            if not next_viewstate or next_viewstate[0] == viewstate:
                print("[INFO] No new __VIEWSTATE found — finished.")
                break

            viewstate = next_viewstate[0]
            page += 1
            if page>2:
                break

        # Finalize attributes for Juriscraper
        for attr in self._all_attrs:
            self.__setattr__(attr, getattr(self, f"_get_{attr}")())
        self._clean_attributes()
        if "case_name_shorts" in self._all_attrs:
            self.case_name_shorts = self._get_case_name_shorts()
        self._post_parse()
        self._check_sanity()
        self._date_sort()
        self._make_hash()
        return 0

    def get_state_name(self):
        return "Delaware"

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court of Delaware"

    def get_class_name(self):
        return "delaware"
