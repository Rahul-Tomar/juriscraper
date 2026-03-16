"""Scraper for the D.C. Court of Appeals
CourtID: dc
Court Short Name: D.C.
Author: V. David Zvenyach
Date created:2014-02-21
"""
import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlencode, urljoin

from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.baseurl = "https://www.dccourts.gov/court-of-appeals/opinions-and-memorandum-of-judgments"
        self.page=0
        self.nextPage=True
        self.status = "Published"

    def _process_html(self) -> None:

        empty = self.html.xpath("//div[@class='view-empty']")
        if empty:
            self.nextPage = False
            return

        rows = self.html.xpath(
            "//div[@class='table-wrapper']//table[@class='cols-5']//tbody/tr")

        for row in rows:

            # -------- docket + url --------
            anchor = row.xpath(".//td[1]//a")

            if anchor:
                docket = anchor[0].xpath("text()")[0].strip()
                url = anchor[0].xpath("@href")[0]
            else:
                docket = row.xpath(".//td[1]/text()")[0].strip()
                url = "null"

            # make absolute url
            if url and not url.startswith("http"):
                url = "https://www.dccourts.gov" + url

            # -------- case name --------
            name = row.xpath(".//td[2]/text()")
            name = name[0].strip() if name else ""

            # -------- date --------
            date_str = row.xpath(".//td[3]/text()")[0].strip()

            curr_date = datetime.strptime(date_str, "%b %d, %Y").strftime(
                "%d/%m/%Y")

            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                return

            # -------- disposition --------
            disposition = row.xpath(".//td[4]/text()")
            disposition = disposition[0].strip() if disposition else ""

            # -------- judge --------
            judge_text = row.xpath(".//td[5]/text()")
            judge_text = judge_text[0].strip() if judge_text else ""

            if judge_text == "Per Curiam":
                judge = ""
            else:
                judge = judge_text

            # -------- docket split --------
            result = re.split(r"[,&]\s*", docket)
            cleaned_list = [item.strip() for item in result]

            # -------- append case --------
            self.cases.append(
                {
                    "date": date_str,
                    "url": url,
                    "name": name,
                    "docket": cleaned_list,
                    "judge": [judge],
                    "disposition": disposition,
                    "status":"Published"
                }
            )

    def set_url(self, start: Optional[date] = None,
                end: Optional[date] = None) -> None:

        if not start:
            start = datetime.today() - timedelta(days=15)
            end = datetime.today()

        start = start.strftime("%m/%d/%Y")
        end = end.strftime("%m/%d/%Y")

        params = {
            "date": start,
            "date_range": end,
            "type": "Opinions"
        }

        self.url = f"{self.baseurl}?{urlencode(params)}"

    def _download_backwards(self, dates: Tuple[date]) -> None:
        logger.info("Backscraping for range %s %s", *dates)
        while self.nextPage:
            self.set_url(*dates)
            self.url = f"{self.url}&page={self.page}"
            print(self.url)
            self.html = self._download()
            cases_before = len(self.cases)
            self._process_html()
            cases_after = len(self.cases)
            # if cases_after == cases_before:
            #     logger.info("No more cases found. Stopping pagination.")
            #     break

            self.page += 1


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        print(f"start date is {start_date} and end date is {end_date}")
        self._download_backwards((start_date, end_date))

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

    def get_class_name(self):
        return "dc"

    def get_court_name(self):
        return "District of Columbia Court of Appeals"

    def get_state_name(self):
        return "District Of Columbia"

    def get_court_type(self):
        return "state"
