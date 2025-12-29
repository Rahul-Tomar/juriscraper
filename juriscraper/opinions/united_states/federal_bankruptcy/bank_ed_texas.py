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
        container = self.html.xpath('//div[contains(@class,"view-content")]//table')
        if not container:
            return
        table = container[0]

        rows = table.xpath('.//tbody/tr')

        for row in rows:
            # --- Year filter (skip < 2025) ---
            year_tag = row.xpath(
                './/td[contains(@class,"views-field-field-opinion-date")]//span/text()'
            )
            if not year_tag:
                continue

            try:
                year = int(year_tag[0].strip())
            except:
                continue

            if year < 2025:
                continue

            # --- Case Name ---
            name_tag = row.xpath('.//td[contains(@class,"views-field-title")]//a/text()')
            name = name_tag[0].strip() if name_tag else ""

            # --- PDF URL ---
            pdf_url = ""
            pdf_href = row.xpath('.//td[contains(@class,"views-field-field-opinion-file")]//a/@href')
            if pdf_href:
                href = pdf_href[0].strip()
                pdf_url = href if href.startswith("http") else urljoin(
                    "https://www.txeb.uscourts.gov", href
                )

            # --- Extract date from PDF filename (YYYY-MM-DD) ---
            date_text = ""
            curr_date = ""
            pdf_text = row.xpath(
                './/td[contains(@class,"views-field-field-opinion-file")]//a/text()'
            )
            if pdf_text:
                match = re.search(r'(\d{4}-\d{2}-\d{2})', pdf_text[0])
                if match:
                    try:
                        date_text = datetime.strptime(
                            match.group(1), "%Y-%m-%d"
                        ).strftime("%m/%d/%Y")
                    except:
                        date_text = ""

            if date_text:
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

            # --- Docket (split on semicolon) ---
            citation_tag = row.xpath(
                './/td[contains(@class,"views-field-field-opinion-citation")]/text()'
            )

            docket = []
            if citation_tag:
                raw = citation_tag[0].strip()
                docket = [d.strip() for d in raw.split(";") if d.strip()]

            # --- Summary (use issue only) ---
            issue_tag = row.xpath(
                './/td[contains(@class,"views-field-field-opinion-issue")]/text()'
            )
            summary = issue_tag[0].strip() if issue_tag else ""

            # --- Judge ---
            judge_tag = row.xpath(
                './/td[contains(@class,"views-field-field-judge")]//a/text()'
            )
            judge = judge_tag[0].strip() if judge_tag else ""

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": [judge] if judge else [],
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.txeb.uscourts.gov"
        next_url = "/judges-info/opinions/"

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
        return "bank_ed_texas"

    def get_court_type(self):
        return "Bankruptcy"

    def get_state_name(self):
        return "5th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Eastern District of Texas"
