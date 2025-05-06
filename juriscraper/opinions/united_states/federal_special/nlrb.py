from datetime import datetime
from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status="Published"
        self.end_year = None

    def _process_html(self):
        text = self.html[1]['data']
        tree = html.fromstring(text)
        rows = tree.xpath('//table//tbody/tr')
        for row in rows:
            date = row.xpath('./td[1]/text()')[0].strip()
            curr_date = datetime.strptime(date, "%m/%d/%Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                self.end_year = int(curr_date.split("/")[2])
                return
            citation = row.xpath('./td[2]/text()')[0].strip()
            title = row.xpath('./td[3]/a/text()')[0].strip()
            pdfurl = row.xpath('./td[3]/a/@href')[0].strip()
            case_number = row.xpath('./td[4]/a/text()')[0].strip()

            self.cases.append({
                'date': date, 'citation': [citation], 'name': title, 'docket': [case_number], 'url': pdfurl})


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        page = 0
        flag=True
        while flag:
            if self.end_year is not None:
                if self.end_year < end_date.year:
                    flag=False
            self.url=f"https://www.nlrb.gov/sort-case-decisions-bd/date_issued+desc/board-decisions/date-issued/-1/all/100?_wrapper_format=drupal_ajax&search_term=&volume=-1&slip_opinion_number=&page_number=&items_per_page=100&op=Apply&form_build_id=form-fuigRriFNZ72jRNDMiEgN8o2suPF3ZGJY5wThVCOPKY&form_id=board_decisions_form&url=&page={page}&_wrapper_format=drupal_ajax"
            self.method = "POST"
            self.parameters={
                "js":"true",
                "_drupal_ajax":"1",
                "ajax_page_state[theme]":"nlrb",
                "ajax_page_state[theme_token]":"",
                "ajax_page_state[libraries]":"eJyNUYGqwyAM_CFXP0miZp1rasRYuu7rn7WW0T0ePJDj7mJiTCy4yRSuJ2n74eYpyv4RKvgqyhK8N92wc0cgQkHOGDH4ThPTdg9Ep8w8B8GuMtw7W9Em5R4sGLXPSwIaDtVNQ8Hqgw5ORLUXaxNQa3U-owiMWGOcUUfOM1B4o6otU4jTWbZLNTKPhKbAqMcK33qAJ7yu5qwiZat3-LBb_bebmjauduPRBQkcRf-2Bg_JQATaSnDyzxzhXC7OkedBHpYhe32Vw7w1I3FaUr_Ka9w3Ivpkt5JhU61z3XBAkBDHi9WWKJsUnI85L7LuNdoYu2j4A7Ir46Y"
            }
            self.parse()
            page=page+1
            self.downloader_executed=False

        return 0

    def get_class_name(self):
        return "nlrb"

    def get_court_type(self):
        return "Special"

    def get_state_name(self):
        return "Labor"

    def get_court_name(self):
        return "National Labor Relations Board"