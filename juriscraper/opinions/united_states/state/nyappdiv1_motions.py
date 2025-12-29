from datetime import datetime
from urllib.parse import urljoin

import cloudscraper
from lxml import html

from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.state import ny_new


class Site(ny_new.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.base_url="https://nycourts.gov/reporter/motindex/mots_ad1_list.shtml"
        self.link_regex='mots_ad1_'
        self.proxies = {
            # 'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050',
            "http": "http://23.236.154.202:8800",
            "https": "http://23.236.154.202:8800"
        }
        self.scraper = cloudscraper.create_scraper()

    def _process_html(self):
        i = 1
        current_date = None
        for elem in self.html.xpath("//tr | //caption//b"):
            text = elem.text_content().strip()
            if text.startswith("Motions Decided"):
                current_date = text.replace("Motions Decided", "").strip()
                if '.' in current_date:
                    current_date = current_date.replace(".",",")

                # parse_date = datetime.strptime(current_date, "%d %B, %Y").strftime("%Y-%m-%d")
                continue
            if elem.tag == "tr":
                cells = elem.xpath("./td")
                if len(cells) < 3:
                    continue
                title_el = cells[0].xpath(".//a")
                title = title_el[0].text_content().strip() if title_el else cells[0].text_content().strip()
                url = urljoin(self.BASE_URL, title_el[0].get("href")) if title_el else ""
                doc_str=cells[1].text_content().strip()
                docket = (str(doc_str).replace(" SCR","-SCR").replace(" CR","-CR").replace(" WC","-WC")
                          .replace(" ROC", "-ROC").replace(" NCR", "-NCR").replace(" NC", "-NC")
                          .replace(" SC", "-SC").replace(" SCR", "-SCR").replace(" ORCR", "-ORCR").replace(" ORC", "-ORC")
                          .replace(" WCR","-WCR").replace(" RICR","-RICR").replace(" KC","-KC")
                          .replace(" QCR","-QCR").replace(" QC","-QC").replace(" RIC","-RIC")
                          .replace("CAF ","CAF-").replace("TP ","TP-").replace("CA ","CA-").replace(" KCR","-KCR")
                          .replace("KA ","KA-").replace("KAH ","KAH-").replace("/"," ")
                          .replace(", "," ").replace(" AND "," ").replace(" and "," ").split(" "))
                slip_op = cells[2].text_content().strip()
                if str(title).__eq__("Title") and str(doc_str).__eq__("Motion No."):
                    continue

                date = datetime.strptime(current_date, "%B %d, %Y").strftime("%d/%m/%Y")
                res = CasemineUtil.compare_date(self.crawled_till, date)
                if res == 1:
                    continue
                # print(title)
                # print(current_date)

                self.cases.append({
                    "name": title, "date": current_date, "status": "Unknown", "url": url, "parallel_citation": [self.to_mongo_format(slip_op)], "docket": docket})  # print(f"{i} - {current_date} || {title} || {docket} || {slip_op} || {judge}")
            i += 1

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        response = self.scraper.get(self.base_url, proxies=self.proxies, timeout=60)
        if response.status_code==200:
            link_xpath = html.fromstring(response.text)
            links = link_xpath.xpath(f"//a[starts-with(@href, {self.link_regex}) and contains(@href, '-{end_date.year}')]/@href")
            for link in links:
                self.url = f"https://nycourts.gov/reporter/motindex/{link}"
                self.parse()
        return 0

    def get_court_name(self):
        return "Appellate Division of the Supreme Court, New York"

    def get_class_name(self):
        return "nyappdiv1_motions"
