#  Scraper for Georgia Supreme Court
# CourtID: ga
# Court Short Name: ga

import re
from datetime import date, datetime, timedelta

from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import titlecase
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.back_scrape_iterable = range(2016, 2022)
        self.court="opinions"

    def _get_url(self, year: int, type: str) -> str:
        """Generate the GA URL for a given year.

        :param year: Year to scrape
        :return: URL for the given year
        """
        return f"https://www.gasupreme.us/opinions/{year}-{type}/"

    def _process_html(self) -> None:
        for link in self.html.xpath("//li/a[contains(@href, '.pdf')]"):
            url = link.get("href")
            # Expected title content:
            # - "S20A1505, S20A1506. PENDER v. THE STATE"
            # - "S21A0306. BELL v. RAFFENSPERGER"
            title = link.text_content()
            if not title:
                continue
            dockets = re.findall(r"S?\d{2}\w\d{4}", title)
            if not dockets:
                # Skip links to weekly summaries or cases without a docket
                continue
            docket = ", ".join(dockets)
            name = title.split(dockets[-1])[-1].strip("., ")
            if str(name).__eq__(''):
                continue
            # Expected summary content:
            # - "October 19, 2021—SUMMARIES for NOTEWORTHY OPINIONS"
            # - "July 7, 2021"
            # - "February 15, 2021 – SUMMARIES for NOTEWORTHY OPINIONS"
            summary_nodes = link.xpath(
                ".//parent::li/parent::ul/preceding-sibling::p[1]")

            if summary_nodes:
                summary = summary_nodes[0].text_content().strip()
            else:
                summary = ""
            # Character separator for dates from summary text could be:
            # - dash: "-"
            # - hyphen: "—"
            # - character U+2013: "–"
            date_str = self.get_date_from_link(link)
            date_summary = datetime.strptime(date_str, "%B %d, %Y")
            comp_date=date_summary.strftime("%d/%m/%Y")
            res=CasemineUtil.compare_date(self.crawled_till,comp_date)
            if res==1:
                return
            doc_arr = []
            if docket.__contains__(","):
                doc_arr = docket.split(',')
            else:
                doc_arr.append(docket)

            new_doc=[]
            for i in doc_arr:
                new_doc.append(str(i).strip())

            self.cases.append(
                {"date": date_str, "docket": new_doc, "name": titlecase(name),
                 "url": url, })

    def get_date_from_link(self, link):
        ul_nodes = link.xpath("./ancestor::ul[1]")

        if not ul_nodes:
            return ""

        node = ul_nodes[0].getprevious()

        while node is not None:
            text = (node.text_content() or "").strip()

            match = re.search(
                r"[A-Za-z]+\s+\d{1,2},\s+\d{4}",
                text
            )

            if match:
                return match.group(0).strip()

            node = node.getprevious()

        return ""

    def _download_backwards(self, year) -> None:
        self.url = self._get_url(year)
        logger.info(f"Backscraping for year {year}: {self.url}")
        self.html = self._download()

        # Setting status is important because it prevents the download
        # function from being run a second time by the parse method.
        if self.html is not None:
            self.status = 200
            self._process_html()

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        for year in range(start_date.year, end_date.year+1):
            self.url = self._get_url(year,self.court)
            self.parse()
            self.downloader_executed=False
        return 0

    def get_state_name(self):
        return "Georgia"

    def get_court_type(self):
        return "state"

    def get_class_name(self):
        return "ga"

    def get_court_name(self):
        return "Supreme Court of Georgia"
