from datetime import datetime
import html

from lxml import html
import requests

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.current_year = None

    def _process_html(self):
        rows = self.html.xpath('//table//tr')
        i = 0
        for row in rows:
            if i==0:
                i+=1
                continue
            opinion = row.xpath('./td[1]//a/text()')
            link = row.xpath('./td[1]//a/@href')
            date = row.xpath('string(./td[2])').replace("\n","")
            new_date = f"{date}, {self.current_year}"
            curr_date = datetime.strptime(new_date, "%b %d, %Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                return

            topic = row.xpath('./td[3]//text()')
            summary = row.xpath('./td[4]/text()')
            # print(f"{date}, {self.current_year}")
            self.cases.append({
                'date': new_date,
                "docket":opinion,
                'name': ' '.join([t.strip() for t in topic if t.strip()]),
                "url":link[0] if link else '',
                "summary":summary[0].strip() if summary else ''
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        for year in range(start_date.year, end_date.year + 1):
            self.current_year=year
            self.url = f"https://ago.mo.gov/other-resources/ag-opinions/2020-opinions/{year}-opinions/"
            self.parse()
            self.downloader_executed = False
        return 0

    def get_class_name(self):
        return "mo_ag"

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return "Missouri"

    def get_court_name(self):
        return "Opinions of the Missouri Attorney General"