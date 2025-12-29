import sys
import re
from datetime import datetime
from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

if sys.version_info[0] < 3:
    import urlparse
    urljoin = urlparse.urljoin
else:
    from urllib.parse import urljoin


class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"

    def _process_html(self):
        rows = self.html.xpath('//table[contains(@class,"views-table")]//tbody/tr')
        if not rows:
            return

        for row in rows:
            # -------------------------
            # Date
            # -------------------------
            date_text = ""
            curr_date = ""
            date_span = row.xpath('.//span[contains(@class,"date-display-single")]/text()')
            if date_span:
                date_text = date_span[0].strip()
                try:
                    curr_date = datetime.strptime(
                        date_text, "%m/%d/%Y"
                    ).strftime("%d/%m/%Y")
                except:
                    curr_date = ""

            if curr_date:
                try:
                    if CasemineUtil.compare_date(self.crawled_till, curr_date) == 1:
                        return "STOP"
                except:
                    pass

            # -------------------------
            # URL + Summary (TITLE FIELD)
            # -------------------------
            anchor = row.xpath('.//td[contains(@class,"views-field-title")]//a')
            if not anchor:
                continue

            anchor = anchor[0]
            url = anchor.get("href", "").strip()

            summary = " ".join(anchor.xpath('.//text()')).strip()

            # -------------------------
            # Case Name (BODY FIELD)
            # -------------------------
            name = " ".join(
                row.xpath('.//td[contains(@class,"views-field-body")]//text()')
            ).strip()
            name = re.sub(r'^In\s+Re:\s*', '', name, flags=re.I).strip()

            # -------------------------
            # Docket(s)
            # -------------------------
            docket_text = " ".join(
                row.xpath('.//td[contains(@class,"views-field-field-meta-data")]//text()')
            ).strip()

            docket = []
            if docket_text:
                docket = [d.strip() for d in docket_text.split(",") if d.strip()]

            self.cases.append({
                "name": name,
                "url": url,
                "docket": docket,
                "date": date_text,
                "judge": ["Judge Woodard"],
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.url = "https://www.msnb.uscourts.gov/opinions"
        self.parse()
        return len(self.cases)

    def get_class_name(self):
        return "bank_nd_missi_jw"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "5th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Northern District of Mississippi"

