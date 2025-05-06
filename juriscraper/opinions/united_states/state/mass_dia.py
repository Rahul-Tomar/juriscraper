from datetime import datetime
from idlelib.run import manage_socket

from lxml import html
import requests
from typing_extensions import override

from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.current_year = None

    @override
    def _request_url_get(self, url):
        self.request["response"] = requests.get(
            url=url,
            proxies=self.proxies,
            timeout=60,
        )

    def _process_html(self):
        content = self.html.xpath('//div[contains(@class,"ma__stacked-row")]')[0]
        sections = content.xpath('./section')
        for section in sections:
            head_month = section.xpath('.//h2[contains(@class,"ma__comp-heading")]/text()')[0].strip()
            if str(head_month).__contains__("No Decisions") or str(head_month).__contains__("No decisions"):
                continue
            main_content = section.xpath(".//div[contains(@class,'main-content')]")[0]
            links = main_content.xpath(".//div[contains(@class,'ma__download-link')]")
            for link in links:
                href = str(link.xpath(".//a[contains(@class,'js-clickable-link')]/@href")[0])
                if not href.__contains__("https://www.mass.gov/"):
                    href = "https://www.mass.gov/"+href
                response = requests.get(url=href, proxies=self.proxies, timeout=60)
                inner_html = self._make_html_tree(response.text)
                title_text = inner_html.xpath('//h1[@class="ma__page-header__title"]/text()')

                # Clean and join text nodes
                title = ' '.join(t.strip() for t in title_text if t.strip())

                date_text = inner_html.xpath('//tr[th[text()="Date:"]]/td/span/text()')
                date = date_text[0].strip() if date_text else ''

                doc_text = inner_html.xpath('//tr[th[text()="Docket Number:"]]/td/span/text()')
                doc = doc_text[0].strip() if doc_text else ''
                docket_list = [item.strip() for item in str(doc).replace(":","").replace("DIA No.","").replace("DIA Board No.","").replace("DIA Board Nos.","").split(',')]

                # Extract judge name (e.g., O’LEARY, J.)
                judge_name = inner_html.xpath('//div[contains(@class, "ma__rich-text")]//p/strong//text()')
                judge_name = ''.join(judge_name).strip() if judge_name else ''

                pdf_url = inner_html.xpath('//a[contains(@class, "ma__download-link__file-link")]/@href')
                pdf_url = pdf_url[0] if pdf_url else ''
                self.cases.append({
                    "name":title,
                    "date":date,
                    "docket":docket_list,
                    "judge":[judge_name],
                    "url":pdf_url
                })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        for year in range(start_date.year, end_date.year+1):
            self.url=f'https://www.mass.gov/lists/{year}-dia-reviewing-board-decisions'
            self.parse()
            self.downloader_executed=False
        return 0

    def get_class_name(self):
        return "mass_dia"

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return "Massachusetts"

    def get_court_name(self):
        return "Massachusetts Department of Industrial Accidents"