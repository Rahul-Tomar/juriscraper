from datetime import datetime

from bs4 import BeautifulSoup
import requests
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.url = "https://www.txcourts.gov/about-texas-courts/multi-district-litigation-panel/available-multidistrict-litigation-cases/"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Host": "www.txcourts.gov",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }
        self.headers_case = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Host": "search.txcourts.gov",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
}


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return len(self.cases)

    def _download(self, request_dict={}):
        pass

    def _process_html(self):
        response = response = requests.get(url=self.url,headers=self.headers,proxies=self.proxies)
        soup = BeautifulSoup(response.content, "lxml")
        table = soup.select_one("table.tjb-data-table.tjb-wide-table.sortable")
        if not table:
            raise Exception("Target table not found")

        rows = table.select("tbody tr")

        results = []

        for row in rows:
            case_link = row.select_one("th a")
            style_td = row.select_one("td")
            date_td = row.select("td")[-1]

            case_number = case_link.text.strip()
            case_url = case_link["href"].strip()
            name = style_td.text.strip()
            date_filed = date_td.text.strip()
            date = datetime.strptime(date_filed, "%m/%d/%Y").strftime("%d/%m/%Y")
            response = requests.get(url=case_url,headers=self.headers_case,proxies=self.proxies)
            if(response.status_code==200):
                soup = BeautifulSoup(response.content,"html.parser")
                keywords = ("denied", "granted","Filing granted")
                table = soup.select_one(
                    "div#ctl00_ContentPlaceHolder1_grdEvents table.rgMasterTable"
                )
                if not table:
                    raise Exception("Events table not found")

                rows = table.select("tbody tr")
                matched_row = None

                for row in rows:
                    cols = row.find_all("td")
                    # print(len(cols))
                    if len(cols) < 5:
                        continue


                    disposition_text = cols[2].get_text(strip=True).lower()

                    if any(k in disposition_text for k in keywords):
                        pdf_link = cols[4].select_one(
                            "a[href*='SearchMedia.aspx']")

                        if pdf_link:
                            href = pdf_link["href"]
                            if not href.startswith("https"):
                                href = "https://search.txcourts.gov/"+href
                                # print(href)
                            self.cases.append({
                                "date": date,
                                "name": name,
                                "disposition": disposition_text,
                                "url": href,
                                "docket": case_number,
                                "status":self.status
                            })
                            break
            print({
                "case_number": case_number,
                "style": name,
                "date_filed": date,
            })


    def get_class_name(self):
        return 'tex_jpml'

    def get_court_name(self):
        return 'Texas Judicial Panel on Multidistrict Litigation.'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Texas'
