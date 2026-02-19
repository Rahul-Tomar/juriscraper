from datetime import datetime
from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status="Unpublished"
        self.end_year = None

    def _process_html(self):
        text = self.html[1]['data']
        tree = html.fromstring(text)
        rows = tree.xpath('//table//tbody/tr')
        for row in rows:
            date = row.xpath('./td[3]/text()')[0].strip()
            curr_date = datetime.strptime(date, "%m/%d/%Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                self.end_year = int(curr_date.split("/")[2])
                return
            title = row.xpath('./td[2]/a/text()')[0].strip()
            if str(title).__contains__("shakeout-ioappospatch1"):
                continue
            pdfurl = row.xpath('./td[2]/a/@href')[0].strip()
            case_number = row.xpath('./td[1]/a/text()')[0].strip()

            self.cases.append({
                'date': date, 'name': title, 'docket': [case_number], 'url': pdfurl})


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        page = 0
        flag=True
        while flag:
            if self.end_year is not None:
                if self.end_year < end_date.year:
                    flag=False
            self.url=f"https://www.nlrb.gov/sort-case-decisions-nbd/date_issued+desc/unpublished-board-decisions/date-issued/all/all/50?_wrapper_format=drupal_ajax&_wrapper_format=drupal_ajax&page={page}"
            self.method = "POST"
            self.parameters={
                "js": "true", "_drupal_ajax": "1", "ajax_page_statetheme]": "nlrb", "ajax_page_state[theme_token]": "", "ajax_page_state[libraries]": "eJyNUQFuwyAM_BCFJyGHuCmJwQiTtenrRwjRlk2TJiHr7mzM2YAIFuvjjK5wNk5E35kLZhswrnYgdouCa9Esehbby8AV_4GWfFzUAG6xhetJ5hu2s_yZKvgqaiB4b6bFjh3VN8nLmSOGscPEtN090UkzBy_YWYZ7R08cknIPFoxmzGsC0gfrYnU8mAPqOrVqL1YTUHt1HFAEJqw5zmgi5wDk36iq5X3cs22namKeCG2ByUw1_OQaZnhdxaAi5cHs4Qvd6tx15zu0rroZ0XnxHMX8lvQIyUIE2op38s87wrlclOPeCPIYGPJorlSHrQmJ05p6KT_j_iNiTnQrGTbVnJsWNYL4OF2k9omyScFw7HmV596jrbGTFj8BcWkCZw"
            }
            self.parse()
            page=page+1
            self.downloader_executed=False

        return 0

    def get_class_name(self):
        return "nlrb_u"

    def get_court_type(self):
        return "Special"

    def get_state_name(self):
        return "Labor"

    def get_court_name(self):
        return "National Labor Relations Board"
