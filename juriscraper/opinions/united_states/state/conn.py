import re
from datetime import date, datetime
from typing import Tuple
from playwright.sync_api import sync_playwright
from dateutil.parser import parse
from urllib.parse import urlparse
from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import clean_string
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
import os
import re
import requests

class Site(OpinionSiteLinear):
    court_abbv = "sup"
    start_year = 2000
    base_url = "http://www.jud.ct.gov/external/supapp/archiveARO{}{}.htm"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"

        self.current_year = int(date.today().strftime("%Y"))
        self.url = self.make_url(self.current_year)
        self.make_backscrape_iterable(kwargs)

        self.cipher = "AES256-SHA256"
        self.set_custom_adapter(self.cipher)

    @staticmethod
    def find_published_date(date_str: str) -> str:
        """
            Extracts a published date from text like:
            'To Be Published in the Connecticut Law Journal of December 16, 2025:'
            """

        pattern = re.compile(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}"
            r"|"
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"
        )

        m = pattern.search(date_str)

        if not m:
            raise ValueError(
                f"Unable to extract published date from: {date_str}")

        return m.group(0)

    def extract_dockets_and_name(self, row) -> Tuple[str, str]:

        text = " ".join(row.xpath("ancestor::li[1]//text()"))
        clean_text = re.sub(r"[\n\r\t\s]+", " ", text)
        m = re.match(
            r"(?P<dockets>[SAC0-9, ]+)(?P<op_type> [A-Z].*)? - (?P<case_name>.*)",
            clean_text,
        )
        if not m:
            # Handle bad inputs
            m = re.match(
                r"(?P<dockets>[SAC0-9, ]+)(?P<op_type> [A-Z].*)? (?P<case_name>.*)",
                clean_text,
            )
        op_type = m.group("op_type")
        name = m.group("case_name")
        if op_type:
            name = f"{name} ({op_type.strip()})"
        return m.group("dockets"), name

    def _process_html(self) -> None:
        for row in self.html.xpath(".//*[contains(@href, '.pdf')]"):
            pub = row.xpath('preceding::*[contains(., "Published")][1]/text()')
            if pub:
                date_filed_is_approximate = False
                print(pub)
                try :
                    date_filed = self.find_published_date(pub[0])
                except Exception:
                    if isinstance(pub, list):
                        pub_text = " ".join(
                            t.strip() for t in pub if t.strip())
                    else:
                        pub_text = str(pub).strip()

                    print("Normalized pub text:", pub_text)
                    date_filed = self.find_published_date(pub_text)

            else:
                date_filed = f"{self.current_year}-07-01"
                date_filed_is_approximate = True

            # curr_date = datetime.strptime(date_filed, "%m/%d/%Y").strftime("%d/%m/%Y")
            curr_date = datetime.strptime(date_filed, "%B %d, %Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                return
            dockets, name = self.extract_dockets_and_name(row)
            pdf_url = row.get("href")
            if not pdf_url.startswith('http'):
                pdf_url="https://www.jud.ct.gov/external/supapp/"+pdf_url

            import re
            clean_title = re.sub(r"[^\x00-\x7F]+", "", name).strip()
            self.cases.append(
                {
                    "url": pdf_url,
                    "name": clean_title,
                    "docket": dockets.split(', '),
                    "date": date_filed,
                    "date_filed_is_approximate": date_filed_is_approximate,
                }
            )

    def make_url(self, year: int) -> str:
        year_str = str(year % 2000).zfill(2)
        return self.base_url.format(self.court_abbv, year_str)

    def extract_from_text(self, scraped_text: str):
        metadata = {"OpinionCluster": {}}
        judges_end = 1_000_000
        regex_date = r"Argued.+officially\sreleased\s(?P<date>[JFMASOND]\w+\s\d{1,2},\s\d{4})"
        if date_match := re.search(regex_date, scraped_text):
            try:
                date_filed = parse(date_match.group("date")).date()
                metadata["OpinionCluster"].update(
                    {
                        "date_filed": date_filed,
                        "date_filed_is_approximate": False,
                    }
                )
            except ValueError:
                pass

            judges_end = date_match.start()

        ph_start_index = scraped_text.find("Procedural History")
        if ph_start_index != -1:
            end_index = scraped_text.find("Opinion", ph_start_index)
            if end_index != -1:
                procedural_history = scraped_text[
                    ph_start_index + 18 : end_index
                ]
                metadata["OpinionCluster"]["procedural_history"] = (
                    clean_extracted_text(procedural_history)
                )

            judges_end = min(judges_end, ph_start_index)

        sy_start_index = scraped_text.find("Syllabus")
        if sy_start_index != -1:
            if ph_start_index:
                syllabus = scraped_text[sy_start_index + 8 : ph_start_index]
                metadata["OpinionCluster"]["syllabus"] = clean_extracted_text(
                    syllabus
                )

            judges_end = min(judges_end, sy_start_index)
        if judges_end != 1_000_000:
            if docket_match := list(
                re.finditer(r"[AS]C\s\d{5}", scraped_text[:judges_end])
            ):
                judges = scraped_text[docket_match[-1].end() : judges_end]
                clean_judges = []
                for judge in (
                    judges.strip("\n )(").replace(" and ", ",").split(",")
                ):
                    if not judge.strip() or "Js." in judge or "C. J." in judge:
                        continue
                    clean_judges.append(judge.strip("\n "))

                metadata["OpinionCluster"]["judges"] = "; ".join(clean_judges)

        return metadata

    def _download_backwards(self, start_year: int, end_year : int) -> None:

        if start_year == end_year:
            logger.info("Backscraping for year %s", start_year)
            self.url = self.make_url(start_year)
            self.html = self._download()
            self._process_html()
        else:
            logger.info(f"Backscraping from the year {start_year} to {end_year}")
            n = end_year-start_year
            curr_year = start_year
            i=0
            while i<=n:
                self.url = self.make_url(curr_year)
                self.html = self._download()
                self._process_html()
                curr_year+=1
                i += 1

    def _download(self):
        """
        Override Juriscraper's default downloader.

        This will download the page using:
        - cloudscraper
        - proxy
        - custom headers + cookies
        """

        import cloudscraper
        from lxml import html

        # ---- PROXY ----
        proxy = "http://23.236.154.202:8800"
        proxies = {
            "http": proxy,
            "https": proxy,
        }

        # ---- HEADERS ----
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            # "Sec-Fetch-Dest": "document",
            # "Sec-Fetch-Mode": "navigate",
            # "Sec-Fetch-Site": "none",
            # "Sec-Fetch-User": "?1",
            # "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }

        # ---- COOKIES ----
        cookies = {
            "_ga": "GA1.1.454464960.1744956244",
            "_ga_B64EXBCE9P": "GS1.1.1744956243.1.1.1744956386.52.0.0",
            "_hjSessionUser_218205": "eyJpZCI6ImRjZGRiZDg2LTJmNzAtNWIyNC1iNTVlLTgyMDgyOGZkMmFmYSIsImNyZWF0ZWQiOjE3NDQ5NTYyNDQ2MzcsImV4aXN0aW5nIjp0cnVlfQ=="
        }

        scraper = cloudscraper.create_scraper()

        logger.info(f"Downloading: {self.url}")

        try:
            resp = scraper.get(
                self.url,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
                timeout=60,
            )
        except Exception as e:
            logger.error(f"Cloudscraper failed: {e}")
            raise

        if resp.status_code != 200:
            logger.error(f"Bad status {resp.status_code} for URL: {self.url}")
            raise Exception(f"Failed to download {self.url}")

        # Return parsed HTML tree exactly as Juriscraper expects
        return html.fromstring(resp.text)

    def download_pdf(self, data, objectId):
        pdf_url = data.__getitem__('pdf_url')
        html_url = data.__getitem__('html_url')
        year = int(data.__getitem__('year'))
        court_name = data.get('court_name')
        court_type = data.get('court_type')

        if str(court_type).__eq__('Federal'):
            state_name=data.get('circuit')
        else:
            state_name = data.get('state')
        opinion_type = data.get('opinion_type')

        if str(opinion_type).__eq__("Oral Argument"):
            path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + state_name + "/" + court_name + "/" + "oral arguments/" + str(year)
        else:
            path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + state_name + "/" + court_name + "/" + str(year)

        obj_id = str(objectId)
        download_pdf_path = os.path.join(path, f"{obj_id}.pdf")

        if pdf_url.__eq__("") or (pdf_url is None) or pdf_url.__eq__("null"):
            if html_url.__eq__("") or (html_url is None) or html_url.__eq__("null"):
                self.judgements_collection.update_one({"_id": objectId}, {
                    "$set": {"processed": 2}})
            else:
                self.judgements_collection.update_one({"_id": objectId}, {
                    "$set": {"processed": 0}})
        else:
            i = 0
            while True:
                try:
                    # os.makedirs(path, exist_ok=True)
                    # us_proxy = CasemineUtil.get_us_proxy()
                    # response = requests.get(
                    #     url=pdf_url,
                    #     headers={
                    #         "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
                    #     },
                    #     proxies={
                    #         "http": f"http://{us_proxy.ip}:{us_proxy.port}",
                    #         "https": f"http://{us_proxy.ip}:{us_proxy.port}"
                    #     },
                    #     timeout=120
                    # )
                    # response.raise_for_status()

                    PROXY = {
                        "server": "http://23.236.154.202:8800"
                    }

                    HEADERS = {
                        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
                        "Accept": "application/pdf,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                    }

                    with sync_playwright() as p:
                        browser = p.firefox.launch(
                            headless=True,
                            proxy=PROXY
                        )
                        context = browser.new_context(
                            extra_http_headers=HEADERS)
                        page = context.new_page()

                        # 🔥 Akamai session warm-up (important for jud.ct.gov)
                        page.goto(
                            "https://www.jud.ct.gov/external/supapp/archiveAROsup25.htm",
                            wait_until="networkidle"
                        )

                        # 🔥 Direct PDF fetch (NO expect_download)
                        response = page.request.get(pdf_url)

                        with open(download_pdf_path, 'wb') as file:
                            file.write(response.body())
                        self.judgements_collection.update_one({"_id": objectId},
                                                              {"$set": {"processed": 0}})
                    break
                except requests.RequestException as e:
                    if str(e).__contains__("Unable to connect to proxy"):
                        i+=1
                        if i>10:
                            break
                        else:
                            continue
                    else:
                        print(f"Error while downloading the PDF: {e}")
                        self.judgements_collection.update_many({"_id": objectId}, {
                        "$set": {"processed": 2}})
                        break
        return download_pdf_path

    def make_backscrape_iterable(self, kwargs: dict) -> None:
        start = kwargs.get("backscrape_start")
        end = kwargs.get("backscrape_end")

        start = int(start) if start else self.start_year
        end = int(end) + 1 if end else self.current_year

        self.back_scrape_iterable = range(start, end)

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        # start_date=datetime(2020,1,1)

        self._download_backwards(start_date.year, end_date.year)
        for attr in self._all_attrs:
            self.__setattr__(attr, getattr(self, f"_get_{attr}")())

        self._clean_attributes()
        if "case_name_shorts" in self._all_attrs:
            self.case_name_shorts = self._get_case_name_shorts()
        self._post_parse()
        self._check_sanity()
        self._date_sort()
        self._make_hash()
        return len(self.cases)

    def get_state_name(self):
        return "Connecticut"

    def get_class_name(self):
        return "conn"

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court of Connecticut"

def clean_extracted_text(text: str) -> str:

    clean_lines = []
    skip_next_line = False
    for line in text.split("\n"):
        if skip_next_line:
            skip_next_line = False
            continue
        if re.search(r"CONNECTICUT LAW JOURNAL|0\sConn\.\s(App\.\s)?1", line):
            skip_next_line = True
            # following line for one of these regexes is the case name
            continue

        clean_lines.append(line)
    return clean_string("\n".join(clean_lines))
