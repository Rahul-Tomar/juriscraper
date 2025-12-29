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
        """
        Parse current page HTML and append cases to self.cases.
        Handles Nebraska structure where docket numbers are embedded in title text.
        """
        container = self.html.xpath('//div[contains(@class,"view-content")]')
        if not container:
            return
        container = container[0]

        rows = container.xpath('.//div[contains(@class,"views-row")]')

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

            # --- Full Title ---
            title_nodes = row.xpath('.//div[contains(@class,"views-field-title")]//a/text()[not(ancestor::span[contains(@class,"date-display-single")])]')
            full_title = " ".join([t.strip() for t in title_nodes if t.strip()])

            # --- Clean case name (remove docket + date) ---
            name = full_title
            if "(" in name:
                name = name.rsplit("(", 1)[0].strip()

            # --- PDF URL ---
            pdf_href = row.xpath('.//div[contains(@class,"views-field-title")]//a/@href')
            pdf_url = pdf_href[0].strip() if pdf_href else ""
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = urljoin("https://www.neb.uscourts.gov", pdf_url)

            # --- Extract docket from PDF URL (source of truth) ---
            docket_list = []
            if pdf_url:
                try:
                    decoded_url = unquote(pdf_url)
                    # NOTE: 4 or 5 digits in the middle block
                    docket_list = re.findall(r'(?:BK|A)\d{2}-\d{4,5}-[A-Z]{3}', decoded_url)
                except Exception:
                    docket_list = []

            # --- Remove dockets from name, clean commas ---
            if docket_list:
                for d in docket_list:
                    name = name.replace(d, "")
                # normalize commas/spaces
                name = re.sub(r"\s*,\s*", ", ", name)
                name = re.sub(r",\s*,", ",", name).strip(" ,")

            # --- Judge ---
            judge_tag = row.xpath('.//div[contains(@class,"views-field-field-opinion-judge")]//div[contains(@class,"field-content")]//a/text()')
            judge = judge_tag[0].strip() if judge_tag else ""

            # --- Summary ---
            desc_paragraphs = row.xpath('.//div[contains(@class,"views-field-body")]//p//text()')
            description = " ".join([p.strip() for p in desc_paragraphs if p.strip()])

            self.cases.append({
                "name": name, "url": pdf_url, "docket": docket_list, "date": date_text, "judge": [judge] if judge else [], "summary": description})

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.neb.uscourts.gov"
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
        return "bank_d_neb"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "8th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court District of Nebraska"