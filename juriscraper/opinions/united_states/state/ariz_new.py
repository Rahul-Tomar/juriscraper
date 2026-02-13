from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        curr_year = str(datetime.now().year)
        self.url = f"https://opinions.azcourts.gov/SearchOpinionsMemoDecs.aspx?year={curr_year}&court=999"
        self.status = "Published"


    def _download(self, request_dict={}):
        pass

    def _process_html(self):
        PROXY = {
            "server": "http://23.236.197.155:8800"
        }
        with sync_playwright() as p:
            browser = p.firefox.launch(
                headless=True,
                proxy=PROXY
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0)",
                locale="en-US"
            )

            page = context.new_page()

            page.goto(self.url, wait_until="networkidle", timeout=60000)

            page.wait_for_selector("div.opinion-listing", timeout=30000)

            html = page.content()

            soup = BeautifulSoup(html, "lxml")
            ul = soup.select_one("ul.opinion-listing--list")
            if not ul:
                raise Exception("opinion-listing--list not found")

            opinions = []

            for li in ul.select("li.opinion"):
                # ---- Date ----
                time_el = li.select_one("time")
                formatted_date = datetime.strptime(time_el.text.strip(),"%m/%d/%Y").strftime("%d/%m/%Y")
                date = datetime.strptime(
                    time_el.text.strip(),
                    "%m/%d/%Y"
                ).strftime("%b %d , %Y")
                print(formatted_date)

                res = CasemineUtil.compare_date(self.crawled_till, formatted_date)
                if res == 1:
                    continue

                # ---- Case Number ----
                case_el = li.select_one("h4.opinion--case-number a")
                case_number = case_el.get_text(strip=True) if case_el else None

                # ---- Title ----
                title_el = li.select_one("h3.opinion--title a")
                title = title_el.get_text(strip=True) if title_el else None

                # ---- PDF URL ----
                pdf_url = (
                    urljoin("https://www.azcourts.gov", case_el["href"])
                    if case_el and case_el.has_attr("href")
                    else None
                )
                self.cases.append({
                    'date':date,
                    'docket':case_number,
                    'name':title,
                    'url':pdf_url,
                    'status':self.status,
                })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return(len(self.cases))

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court Of The State Of Arizona"

    def get_state_name(self):
        return "Arizona"

    def get_class_name(self):
        return "ariz_new"
