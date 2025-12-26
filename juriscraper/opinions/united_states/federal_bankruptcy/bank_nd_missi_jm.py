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
            # --------------------
            # Date
            # --------------------
            date_text = ""
            curr_date = ""

            date_span = row.xpath(
                './/span[contains(@class,"date-display-single")]/text()'
            )
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

            # --------------------
            # URL + Summary
            # (TITLE FIELD = SUMMARY)
            # --------------------
            title_anchor = row.xpath(
                './/td[contains(@class,"views-field-title")]//a'
            )
            if not title_anchor:
                continue

            anchor = title_anchor[0]
            pdf_url = anchor.get("href", "").strip()
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = urljoin("https://www.msnb.uscourts.gov", pdf_url)

            summary = " ".join(anchor.xpath('.//text()')).strip()

            # --------------------
            # Case Name
            # --------------------
            name = " ".join(
                row.xpath(
                    './/td[contains(@class,"views-field-body")]//text()'
                )
            ).strip()

            name = re.sub(r'^\s*In\s+Re:\s*', '', name, flags=re.I)
            name = name.strip(" ,")

            # --------------------
            # Docket
            # --------------------
            meta_text = " ".join(
                row.xpath(
                    './/td[contains(@class,"views-field-field-meta-data")]//text()'
                )
            ).strip()

            docket = list(dict.fromkeys(
                re.findall(r'\d{2}-\d{5}-SDM|\d{2}-\d{5}', meta_text)
            ))

            # --------------------
            # Judge (page-level)
            # --------------------
            judge = ["Judge Maddox"]

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": judge,
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.url = "https://www.msnb.uscourts.gov/sdmopinions"
        self.parse()
        return len(self.cases)

    def get_class_name(self):
        return "bank_nd_missi_jm"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "5th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Northern District of Mississippi"
