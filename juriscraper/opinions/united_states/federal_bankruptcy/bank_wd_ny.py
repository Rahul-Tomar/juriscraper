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
        self.visited_urls = set()

    def _process_html(self):
        container = self.html.xpath('//div[contains(@class,"view-content")]')
        if not container:
            return

        container = container[0]
        nodes = container.xpath('./*')

        current_judge = ""

        for node in nodes:
            # --- Judge header ---
            if node.tag == "h3":
                current_judge = node.text_content().strip()
                continue

            # --- Opinion rows ---
            if "views-row" not in node.get("class", ""):
                continue

            anchor = node.xpath('.//div[contains(@class,"views-field-title")]//a')
            if not anchor:
                continue

            anchor = anchor[0]
            full_text = " ".join(anchor.xpath('.//text()')).strip()

            pdf_url = anchor.get("href", "").strip()
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = urljoin("https://www.nywb.uscourts.gov", pdf_url)

            # --- Date ---
            date_text = ""
            curr_date = ""
            date_span = anchor.xpath('.//span[contains(@class,"date-display-single")]/text()')
            if date_span:
                date_text = date_span[0].strip()
                try:
                    date_obj = datetime.strptime(date_text, "%m/%d/%Y")
                    curr_date = date_obj.strftime("%d/%m/%Y")

                    # 🔴 Skip cases older than 2025
                    if date_obj.year < 2025:
                        continue
                except:
                    continue

            # --- Clean case name ---
            name = re.sub(r'\s+\d{2}/\d{2}/\d{4}$', '', full_text)
            name = re.sub(r'\s*\(.*?\)$', '', name)
            name = name.strip(" ,")

            # --- Docket extraction (from PDF filename) ---
            docket = []
            filename = pdf_url.split("/")[-1]

            docket_matches = re.findall(r'\b\d{2}-\d{5}\b', filename)
            if docket_matches:
                docket = list(dict.fromkeys(docket_matches))  # dedupe

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": [current_judge] if current_judge else [],
                "summary": ""
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.nywb.uscourts.gov"
        next_url = "/judges-info/opinions"

        while next_url:
            full_url = urljoin(base, next_url)

            # 🛑 Stop if page already visited
            if full_url in self.visited_urls:
                break

            self.visited_urls.add(full_url)

            self.url = full_url
            self.parse()

            next_link = self.html.xpath(
                '//li[contains(@class,"pager__item--next")]/a/@href'
            )
            next_url = next_link[0] if next_link else None

        return len(self.cases)

    def get_class_name(self):
        return "bank_wd_ny"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "2d Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Western District of New York"
