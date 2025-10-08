import re
from datetime import datetime

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    court_code = "S"
    division = ""
    date_regex = re.compile(r" \d\d?/\d\d?/\d\d| filed")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url = f"https://www.courts.ca.gov/cms/opinions.htm?Courts={self.court_code}"
        self.status = "Published"
        self.proxies = {
            "http": "http://104.223.126.101:8800", "https": "http://104.223.126.101:8800"}
        self.request["verify"] = False

    def _process_html(self) -> None:
        for row in self.html.xpath("//table/tr[not(th)]"):
            name = row.xpath(".//*[@class='op-title']/text()")[0]

            split = self.date_regex.split(name)[0]
            if "P. v. " in split:
                case_name = split.replace("P. ", "People ")
            else:
                case_name = split

            url = row.xpath(".//a[@class='op-link']/@href")[0]
            if not str(url).__contains__("https://www4.courts.ca.gov"):
                url = "https://www4.courts.ca.gov"+url

            date_filed = row.xpath(".//*[@class='op-date']/text()")[0]
            curr_date = datetime.strptime(date_filed, "%b %d, %Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                return
            docket = row.xpath(".//*[@class='op-case']/text()")[0]
            case = {
                "name": case_name,
                "url": url,
                "date": date_filed,
                "docket": [docket],
            }
            if self.division:
                case["division"] = self.division

            self.cases.append(case)

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return 0

    def get_court_name(self):
        return "Supreme Court of California"

    def get_state_name(self):
        return "California"

    def get_class_name(self):
        return "cal"

    def get_court_type(self):
        return "state"
