import sys
from datetime import datetime
from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

# Python 2.7 + Python 3 compatible urljoin
if sys.version_info[0] < 3:
    import urlparse
    urljoin = urlparse.urljoin
else:
    from urllib.parse import urljoin

class Site(OpinionSiteLinear):
    """
    Scraper for opinions listing on wvsd.uscourts.gov (opinions page).
    Parses the list of <div class="views-row"> entries inside the .view-content block.
    Produces self.cases entries with keys:
        - name: title of the opinion (without the date)
        - url: link to the PDF (absolute URL)
        - docket: list containing docket string
        - date: original date string as found on the page (MM/DD/YYYY)
        - judge: list containing judge name
        - summary: short description (joined paragraphs)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep same semantic as your example
        self.status = "Published"

    def _process_html(self):
        """
        Parse current page HTML and append cases to self.cases.
        This now handles ONLY parsing, not pagination.
        Pagination is handled by crawling_range().
        """
        container = self.html.xpath('//div[contains(@class,"view-content")]')
        if not container:
            return
        container = container[0]

        rows = container.xpath('.//div[contains(@class,"views-row")]')
        for row in rows:
            date_tag = row.xpath('.//div[contains(@class,"views-field-title")]//a//span[contains(@class,"date-display-single")]/text()')
            date_text = date_tag[0].strip() if date_tag else ""

            curr_date = ""
            try:
                if date_text:
                    curr_date = datetime.strptime(date_text, "%m/%d/%Y").strftime("%d/%m/%Y")
                else:
                    content_dt = row.xpath('.//span[contains(@class,"date-display-single")]/@content')
                    if content_dt:
                        parsed = datetime.fromisoformat(content_dt[0])
                        date_text = parsed.strftime("%m/%d/%Y")
                        curr_date = parsed.strftime("%d/%m/%Y")
            except:
                curr_date = ""

            if curr_date:
                try:
                    if CasemineUtil.compare_date(self.crawled_till, curr_date) == 1:
                        return "STOP"
                except:
                    pass

            title_parts = row.xpath('.//div[contains(@class,"views-field-title")]//a/text()')
            title = " ".join([t.strip() for t in title_parts if t.strip()]).strip()

            pdf_href = row.xpath('.//div[contains(@class,"views-field-title")]//a/@href')
            pdf_url = pdf_href[0].strip() if pdf_href else ""
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = urljoin("https://www.wvsd.uscourts.gov", pdf_url)

            docket_tag = row.xpath('.//div[contains(@class,"views-field-field-case-number-opinion")]//div[contains(@class,"field-content")]/text()')
            docket = docket_tag[0].strip() if docket_tag else ""

            desc_paragraphs = row.xpath('.//div[contains(@class,"views-field-body")]//p/text()')
            description = " ".join([p.strip() for p in desc_paragraphs if p.strip()])

            judge_tag = row.xpath('.//div[contains(@class,"views-field-field-judge")]//div[contains(@class,"field-content")]/text()')
            judge = judge_tag[0].strip() if judge_tag else ""

            self.cases.append({
                "name": title, "url": pdf_url, "docket": [docket] if docket else [], "date": date_text, "judge": [judge] if judge else [], "summary": description})

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.wvsd.uscourts.gov"
        next_url = "/judges-info/opinions/"

        while next_url:
            self.downloader_executed = False
            self.url = urljoin(base, next_url)

            # parse() will download AND call _process_html() once
            self.parse()

            # DO NOT call _process_html() again here

            next_link = self.html.xpath('//li[contains(@class,"pager__item--next")]/a/@href')

            next_url = next_link[0] if next_link else None

        return len(self.cases)

    def get_class_name(self):
        return "sd_wv"

    def get_court_type(self):
        return 'Federal'

    def get_state_name(self):
        return "4th Circuit"

    def get_court_name(self):
        return "Southern District of West Virginia"