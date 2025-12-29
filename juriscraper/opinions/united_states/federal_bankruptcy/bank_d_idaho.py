import sys
import re
from datetime import datetime
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
        table = self.html.xpath('//table')[0]
        rows = table.xpath('.//tr')[1:]  # skip header row

        for row in rows:
            cells = row.xpath('./td')
            if len(cells) < 5:
                continue

            # --- Date ---
            date_text = cells[0].text_content().strip()
            try:
                date_obj = datetime.strptime(date_text, "%m/%d/%y")
            except:
                continue

            # --- Year filter (>= 2025 only) ---
            if date_obj.year < 2025:
                continue

            curr_date = date_obj.strftime("%d/%m/%Y")
            try:
                if CasemineUtil.compare_date(self.crawled_till, curr_date) == 1:
                    return "STOP"
            except:
                pass

            # --- Docket ---
            docket_text = cells[1].text_content().strip()
            docket = [docket_text] if docket_text else []

            # --- Judge ---
            judge = cells[2].text_content().strip()

            # --- Title + PDF ---
            title_cell = cells[3]
            anchor = title_cell.xpath('.//a[last()]')
            if not anchor:
                continue
            anchor = anchor[0]

            name = anchor.text_content().strip()

            href = anchor.get("href", "").strip()
            pdf_url = href if href.startswith("http") else urljoin(
                "https://www.id.uscourts.gov", href
            )

            # --- Summary (Decision Type) ---
            summary = ""

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": [judge] if judge else [],
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.url = "https://www.id.uscourts.gov/bankruptcy/judges/Written_Decisions.cfm"
        self.parse()
        return len(self.cases)

    def get_class_name(self):
        return "bank_d_idaho"

    def get_court_type(self):
        return "Bankruptcy"

    def get_state_name(self):
        return "9th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court District of Idaho"
