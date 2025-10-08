from datetime import datetime
from urllib.parse import urljoin

from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.state import nyappdiv1_motions


class Site(nyappdiv1_motions.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.link_regex = 'mots_crimleav'
        self.base_url="https://nycourts.gov/reporter/motindex/mots_crimleav_list.shtml"

    def _process_html(self):
        i = 1
        rows = self.html.xpath("//tr[td]/td/a | //td/a")  # capture <a> tags under table cells

        for anchor in rows:
            title = anchor.text_content().strip()
            url = anchor.get('href')
            url = urljoin(self.BASE_URL, url) if url else ""
            # The <a> is nested in a <td>; we navigate up to extract date and slip opinion number
            parent_td = anchor.getparent()
            row = parent_td.getparent()

            # Typically columns: [Title, Decision Date, Slip Opinion No.]
            tds = row.xpath('./td')
            date = tds[1].text_content().strip() if len(tds) > 1 else None
            slip_op = tds[2].text_content().strip() if len(tds) > 2 else None
            curr_date = datetime.strptime(date, "%B %d, %Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                continue
            self.cases.append({
                "name": title, "date": date, "status": "Unknown", "url": url, "parallel_citation": [self.to_mongo_format(slip_op)], "docket": []})
            i += 1

    def get_class_name(self):
        return "nycrim_motions"

    def get_court_name(self):
        return "New York Court of Appeals"