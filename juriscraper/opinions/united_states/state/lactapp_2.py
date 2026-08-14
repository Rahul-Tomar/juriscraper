from datetime import datetime
import json
import requests
import re

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url="https://www.la2nd.org/opinions/"

    def _process_html(self):
        for row in self.html.xpath(
            "//table[@id='datatable']//tbody/tr[contains(@class,'opinion-row')]"
        ):
            cells = row.xpath("./td")

            if len(cells) < 8:
                continue

            comp_date = None

            date_str = cells[0].text_content().strip()
            docket = cells[1].text_content().strip()
            name = cells[2].text_content().strip()
            judge = cells[3].text_content().strip()
            disposition = cells[4].text_content().strip()
            lower_court = cells[5].text_content().strip()
            status = cells[6].text_content().strip().replace(".","")

            links = cells[7].xpath(".//a/@href")

            url = links[0].strip() if links else ""

            if not date_str:
                continue

            try:
                parsed_date = datetime.strptime(
                    date_str,
                    "%m/%d/%Y"
                )

                date = parsed_date.strftime("%B %d, %Y")
                comp_date = parsed_date.strftime("%d/%m/%Y")

            except ValueError:
                print(f"Invalid date format: {date_str}")
                continue

            res = CasemineUtil.compare_date(
                self.crawled_till,
                comp_date
            )

            if res >= 0:
                continue

            judge_array = []

            if judge:
                judge_array = [judge]

            self.cases.append({
                "name": name,
                "date": date,
                "docket": [docket],
                "url": url,
                "judge": judge_array,
                "disposition": disposition,
                "status": status
            })


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        print("[INFO] Crawling from", start_date, "to", end_date)
        self.parse()
        return 0

    def get_class_name(self):
        return 'lactapp_2'

    def get_court_name(self):
        return 'Louisiana Court of Appeal'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Louisiana'
