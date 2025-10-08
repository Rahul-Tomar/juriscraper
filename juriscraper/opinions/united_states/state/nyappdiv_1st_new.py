from datetime import datetime
from urllib.parse import urljoin

from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.state import ny_new

class Site(ny_new.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.BASE_URL = "https://nycourts.gov/reporter/slipidx/"
        self.court_type = "aidxtable_1"
        self.CURRENT_URL = self.BASE_URL + f"{self.court_type}.shtml"
        self.ARCHIVE_URL = self.BASE_URL + "{court_type}_{year}_{month}.shtml"

    def _process_html(self):
        i=1
        current_date = None
        # Go through all rows
        for elem in self.html.xpath("//tr | //caption//b"):
            text = elem.text_content().strip()
            # Check if it's a "Cases Decided" date header
            if text.startswith("Cases Decided"):
                # Extract date part (after "Cases Decided")
                current_date = text.replace("Cases Decided", "").strip()
                continue
            # If it's a case row (must have 4 <td>)
            if elem.tag == "tr":
                cells = elem.xpath("./td")
                if len(cells) < 4:
                    continue  # skip headers
                title_el = cells[0].xpath(".//a")
                title = title_el[0].text_content().strip() if title_el else cells[0].text_content().strip()
                url = urljoin(self.BASE_URL, title_el[0].get("href")) if title_el else ""
                judge = cells[1].text_content().strip()
                docket = cells[2].text_content().strip()
                slip_op = cells[3].text_content().strip()
                # print(docket)
                # print(slip_op)
                if str(title).__eq__("Title") and str(slip_op).__eq__("Slip Opinion No.") :
                    continue

                date = datetime.strptime(current_date, "%B %d, %Y").strftime("%d/%m/%Y")
                res = CasemineUtil.compare_date(self.crawled_till, date)
                if res == 1:
                    continue

                jud_ar = []
                if not str(judge).__eq__(""):
                    jud_ar = [judge]
                self.cases.append({
                    "name": title, "date": current_date, "status": "Unknown", "url": url, "parallel_citation": [self.to_mongo_format(slip_op)], "judge": jud_ar,"docket":[]
                })
                # print(f"{i} - {current_date} || {title} || {docket} || {slip_op} || {judge}")
            i+=1

    def get_court_name(self):
        return "Appellate Division of the Supreme Court, New York"

    def get_class_name(self):
        return "nyappdiv_1st_new"