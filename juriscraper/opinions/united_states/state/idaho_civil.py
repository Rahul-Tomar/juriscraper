"""
Contact: Sara Velasquez, svelasquez@idcourts.net, 208-947-7501
History:
 - 2014-08-05, mlr: Updated.
 - 2015-06-19, mlr: Updated to simply the XPath expressions and to fix an OB1
   problem that was causing an InsanityError. The cause was nasty HTML in their
   page.
 - 2015-10-20, mlr: Updated due to new page in use.
 - 2015-10-23, mlr: Updated to handle annoying situation.
 - 2016-02-25 arderyp: Updated to catch "ORDER" (in addition to "Order") in download url text
"""
import json
from datetime import datetime
import re
from xmlrpc.client import DateTime

from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.lib.string_utils import clean_if_py3, convert_date_string
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_code = "ISC+Civil"
        self.court_key = "ISC"
        self.court_year = datetime.now().year
        self.url = f"https://isc.idaho.gov/api/cms-content-search?scope=documents&document_type={self.court_key}+Opinion&category={self.court_code}&tag={self.court_year}&sort_by=entry_date&sort_direction=DESC&limit=100"
        self.case_status  = "Published"
        self.court_id = self.__module__

    def _process_html(self) :
        self.cases=[]
        data = self.html
        for item in data.get("results", []):
            if item.get("result_type") == "document":
                doc_id = item.get("id")
                self.url = f"https://isc.idaho.gov/api/cms-document?id={doc_id}&locale=en"
                data = self._download()
                content = data.get("content", [])

                for block in content:
                    if block.get("component_name") == "Opinion":
                        opinion = block.get("content", {})

                        title = opinion.get("title", {}).get("value", "")
                        # print(title)
                        docket_raw = opinion.get("docket_number", {}).get(
                            "value", "")

                        if docket_raw is None:
                            docket_raw = ""

                        docket_raw = str(docket_raw)

                        docket_numbers = [
                            num.strip()
                            for num in re.split(r",|/|&|;", docket_raw)
                            if num.strip()
                        ]
                        date = opinion.get("release_date", {}).get("value", "")
                        if not date:
                            continue

                        date = str(date).strip()

                        for fmt in (
                                "%B %d, %Y",
                                "%Y/%m/%d",
                                "%Y-%m-%d",
                                "%m/%d/%Y",
                                "%d/%m/%Y",
                        ):
                            try:
                                parsed_date = datetime.strptime(date, fmt)
                                break
                            except ValueError:
                                parsed_date = None

                        if parsed_date is None:
                            print(f"Unsupported date format: {date}")
                            continue

                        case_date = parsed_date.strftime("%B %d, %Y")

                        if CasemineUtil.compare_date(
                            self.crawled_till,
                            parsed_date.strftime("%d/%m/%Y")
                        ) == 1:
                            return len(self.cases)

                        url = (
                            opinion
                            .get("opinion_file", {})
                            .get("value", {})
                            .get("url", "")
                        )
                        summary = opinion.get("summary", {}).get("value", "")
                        self.cases.append(
                            {
                                "date": case_date,
                                "docket": docket_numbers,
                                "url": url,
                                "name": title,
                                "status": self.case_status,
                                "summary":summary
                            }
                        )

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return 0

    def get_class_name(self):
        return "idaho_civil"

    def get_court_name(self):
        return "Supreme Court of Idaho"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Idaho"
