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
        container = self.html.xpath('//div[contains(@class,"view-content")]')
        if not container:
            return
        container = container[0]

        rows = container.xpath('.//div[contains(@class,"views-row")]')

        current_judge = ""

        for node in container.iter():
            # --- Judge header ---
            if node.tag == "h3":
                current_judge = node.text_content().strip()
                continue

            if not isinstance(node.tag, str):
                continue

            if "views-row" not in (node.get("class") or ""):
                continue

            row = node

            # --- Title anchor ---
            anchor = row.xpath('.//div[contains(@class,"views-field-title")]//a')
            if not anchor:
                continue
            anchor = anchor[0]

            full_text = " ".join(anchor.xpath('.//text()')).strip()

            # --- Date ---
            date_text = ""
            curr_date = ""
            date_tag = anchor.xpath('.//span[contains(@class,"date-display-single")]/text()')
            if date_tag:
                date_text = date_tag[0].strip()
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

            # --- PDF URL ---
            href = anchor.get("href", "").strip()
            pdf_url = href if href.startswith("http") else urljoin(
                "https://www.moeb.uscourts.gov", href
            )

            # --- Docket (leading number pattern) ---
            docket = []
            docket_match = re.match(r'^(\d{2}-\d+)', full_text)
            if docket_match:
                docket = [docket_match.group(1)]

            # --- Case name (remove docket + date) ---
            name = full_text
            if docket:
                name = name.replace(docket[0], "").strip()
            name = re.sub(r'\s+\d{2}/\d{2}/\d{4}$', '', name)
            name = re.sub(r'\s*\d{2}/\d{2}/\d{4}\s*$', '', name)
            name = name.replace(date_text, "").strip()

            # --- Summary ---
            summary = ""

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": [current_judge] if current_judge else [],
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.moeb.uscourts.gov"
        next_url = "/judges-info/opinions"

        while next_url:
            self.downloader_executed = False
            self.url = urljoin(base, next_url)
            self.parse()

            next_link = self.html.xpath(
                '//li[contains(@class,"pager__item--next")]/a/@href'
            )
            next_url = next_link[0] if next_link else None

        return len(self.cases)

    def get_class_name(self):
        return "bank_ed_missouri"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "8th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Eastern District of Missouri"
