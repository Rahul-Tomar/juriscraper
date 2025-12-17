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
        self.status = "Unpublished"

    def _process_html(self):
        table = self.html.xpath('//table')
        if not table:
            return
        table = table[0]

        rows = table.xpath('.//tr')[1:]  # skip header

        for row in rows:
            cells = row.xpath('./td')
            if len(cells) < 3:
                continue

            # --- Date ---
            date_text = cells[0].text_content().strip()
            try:
                date_obj = datetime.strptime(date_text, "%m/%d/%Y")
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

            # --- Case info cell ---
            info_cell = cells[1]

            # Anchor
            anchor = info_cell.xpath('.//a')
            if not anchor:
                continue
            anchor = anchor[0]

            # PDF URL
            href = anchor.get("href", "").strip()
            pdf_url = href if href.startswith("http") else urljoin(
                "https://www.nvb.uscourts.gov", href
            )

            # Anchor text: case name + docket
            anchor_text = " ".join(anchor.xpath('.//text()')).strip()

            # --- Docket (pattern: 23-01015-mkn, 25-10411-mkn, etc.) ---
            docket = re.findall(r'\d{2}-\d{5}-[a-z]{3}', anchor_text, flags=re.I)

            # --- Case name (remove docket) ---
            name = anchor_text
            for d in docket:
                name = name.replace(d, "")
            name = name.rstrip(" ,").strip()

            # --- Summary (text after <br>) ---
            summary_parts = info_cell.xpath('./text()')
            summary = " ".join(t.strip() for t in summary_parts if t.strip())

            # --- Judge ---
            judge = cells[2].text_content().strip()

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": [judge] if judge else [],
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.nvb.uscourts.gov"
        next_url = "/judges/opinions/unpublished-opinions/"

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
        return "bank_d_nevada_u"

    def get_court_type(self):
        return "Bankruptcy"

    def get_state_name(self):
        return "9th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court District of Nevada"
