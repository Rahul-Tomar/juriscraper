"""Scraper for the Texas Attorney General
CourtID: texag
Court Short Name: Texas Attorney General
History:
    2017-02-04: Created by Ardery
    2018-10-13: Retired by Ardery
    2023-01-28: Updated by William E. Palin
"""
from datetime import datetime
import re
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url = "https://texasattorneygeneral.gov/opinions"
        self.expected_content_types = ["application/pdf"]

    def _process_html(self):
        cases = self.html.xpath("//div[@class='sidebar-ag-opinion-content']")

        ####################################################
        ####################  DATE #########################
        ####################  NOT  #########################
        #################### FOUND #########################


        for case in cases:
            docket = case.xpath(".//h4")[0].text_content().strip()
            summary = case.xpath(".//p")[0].text_content().strip()
            url = case.xpath(".//a[contains(@href, '.pdf')]/@href")[0]
            if url and not url.startswith("https"):
                url="https://texasattorneygeneral.gov"+url
            name = f"Untitled Texas Attorney General Opinion: {docket}"
            print(name)
            date = case.xpath(
                ".//div[@class='sidebar-ag-opinion-casedate']/text()"
            )[0].strip()
            if not docket:
                DOCKET_PATTERN = re.compile(r"\bKP-\d{4}\b")

                text = name

                match = DOCKET_PATTERN.search(text)
                if match:
                    docket = match.group()
                    print(docket)

            if not docket:
                raise Exception("Docket is missing or empty")

            self.cases.append(
                {
                    "name": name,
                    "docket": docket,
                    "date": date,
                    "url": url,
                    "summary": summary,
                    "status": "Published",
                }
            )
    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return 0

    def get_class_name(self):
        return "texag"

    def get_court_name(self):
        return "Attorney General of Texas — Opinion"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Texas"
