import sys
from datetime import datetime
from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from urllib.parse import unquote
import re

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
        container = self.html.xpath('//div[contains(@class,"view-content")]//table')
        if not container:
            return
        table = container[0]

        rows = table.xpath('.//tbody/tr')

        for row in rows:
            # --- Date ---
            date_text = ""
            curr_date = ""
            date_tag = row.xpath('.//span[contains(@class,"date-display-single")]/text()')
            if date_tag:
                date_text = date_tag[0].strip()
                try:
                    curr_date = datetime.strptime(date_text, "%m/%d/%Y").strftime("%d/%m/%Y")
                except:
                    curr_date = ""

            if curr_date:
                try:
                    if CasemineUtil.compare_date(self.crawled_till, curr_date) == 1:
                        return "STOP"
                except:
                    pass

            # --- Title + PDF URL ---
            title_link = row.xpath('.//td[contains(@class,"views-field-title")]//a')
            full_title = ""
            pdf_url = ""
            if title_link:
                full_title = (title_link[0].text_content() or "").strip()
                href = title_link[0].get("href", "").strip()
                if href:
                    if href.startswith("http"):
                        pdf_url = href
                    else:
                        pdf_url = urljoin("https://www.mssb.uscourts.gov", href)

            # --- Case name (after the link text) ---
            tail_text_nodes = row.xpath('.//td[contains(@class,"views-field-title")]/text()')
            extra = " ".join([t.strip() for t in tail_text_nodes if t.strip()])
            name = (extra or full_title).strip()

            # --- Extract docket numbers from Case No. column ---
            docket_cell = row.xpath('.//td[contains(@class,"views-field-field-case-no")]/text()')
            docket_raw = " ".join([d.strip() for d in docket_cell if d.strip()])
            docket_list = re.findall(r'(?:BK|Adv\.?|Adv)\s*#?:?\s*\d{2}-\d{5}-[A-Z]{3}', docket_raw)

            # --- Judge ---
            judge_tag = row.xpath('.//td[contains(@class,"views-field-field-opinion-judge")]//a/text()')
            judge = judge_tag[0].strip() if judge_tag else ""

            # --- Summary (none on this court website) ---
            description = ""
            if title_link:
                description = " ".join(title_link[0].xpath('.//text()')).strip()

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket_list,
                "date": date_text,
                "judge": [judge] if judge else [],
                "summary": description
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.mssb.uscourts.gov"
        next_url = "/judges-opinions/opinions"

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
        return "bank_sd_missi"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "5th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Southern District of Mississippi"
