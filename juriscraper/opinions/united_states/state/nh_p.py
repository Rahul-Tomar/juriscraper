"""
Scraper for New Hampshire Supreme Court
CourtID: nh_p
Court Short Name: NH
Court Contact: webmaster@courts.state.nh.us
Author: Andrei Chelaru
Reviewer: mlr
History:
    - 2014-06-27: Created
    - 2014-10-17: Updated by mlr to fix regex error.
    - 2015-06-04: Updated by bwc so regex catches comma, period, or
    whitespaces as separator. Simplified by mlr to make regexes more semantic.
    - 2016-02-20: Updated by arderyp to handle strange format where multiple
    case names and docket numbers appear in anchor text for a single case pdf
    link. Multiple case names are concatenated, and docket numbers are
    concatenated with ',' delimiter
    - 2021-12-29: Updated for new web site, by flooie and satsuki-chan
    - 2024-08-21: Implement backscraper and update headers, by grossir
"""

import re
import requests
import os
from playwright.sync_api import sync_playwright
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin
from casemine.casemine_util import CasemineUtil
from playwright.sync_api import sync_playwright
from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    # document_purpose = 1331 -> Supreme Court Opinion
    base_filter = "{}@field_document_purpose|=|1331"
    year_to_filter = {
        2026: "@field_document_subcategory|=|2721",
        2025: "@field_document_subcategory|=|2616",
        2024: "@field_document_subcategory|=|2316",
        2023: "@field_document_subcategory|=|2256",
        2022: "@field_document_subcategory|=|2091",
        2021: "@field_tags|CONTAINS|1206~field_entity_tags|CONTAINS|1206",
        2020: "@field_tags|CONTAINS|1366~field_entity_tags|CONTAINS|1366",
        2019: "@field_tags|CONTAINS|1416~field_entity_tags|CONTAINS|1416",
        2018: "@field_document_subcategory|=|1601",
        2017: "@field_document_subcategory|=|1596",
        2016: "@field_document_subcategory|=|1591",
        2015: "@field_document_subcategory|=|1586",
        2014: "@field_document_subcategory|=|1581",
    }
    filter_mode = "exclusive"
    document_type = "opinions"
    # there is data since 2002, but we would need to
    # collect all subcategory or tag values
    start_year = 2015
    end_year = datetime.today().year - 1
    cite_regex = re.compile(r"\d{4}\sN\.H\.\s\d+")
    docket_regex = re.compile(r"(?P<docket>\d{4}-\d{1,4})[\s,]*")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.base_url = "https://www.courts.nh.gov/content/api/documents"
        # self.set_request_parameters()
        self.needs_special_headers = True
        self.make_backscrape_iterable(kwargs)
        self.paginate = False
        temp_date = None
        self.proxies = {
            "http": "http://23.236.154.202:8800",
            "https": "http://23.236.154.202:8800",
        }
    def _process_html(self) -> None:
        json_response = self.html

        for case in json_response["data"]:
            fields = case["fields"]

            if fields["field_document_file"]:
                url_object = fields["field_document_file"]
            elif fields["field_document"]:
                # seen on withdrawn opinions. Ex: 2020-0268
                # Hampstead School Board & a. v. School Administrative Unit No. 5
                url_object = fields["field_document"][0]["fields"][
                    "field_document_file"
                ]
            else:
                logger.warning(
                    "Skipping row '%s', can't find document link",
                    case["title"],
                )
                continue
            url = url_object["0"]["fields"]["uri"][0].split("//")[1]

            if fields["field_date_filed"]:
                case_date = fields["field_date_filed"][0]
                print(case_date)
            elif fields["field_date_posted"]:
                # usually this is the only populated field
                case_date = fields["field_date_posted"][0]
                formatted_date = datetime.strptime(case_date,"%Y-%m-%d").strftime("%d/%m/%Y")
            else:
                logger.warning(
                    "Skipping row '%s'. No date found", case["title"]
                )
                continue
            # print(self.crawled_till)
            res = CasemineUtil.compare_date(self.crawled_till, formatted_date)
            if res == 1:
                continue

            name = case["title"]

            citation = ""
            cite_match = self.cite_regex.search(case["title"])
            if cite_match:
                citation = cite_match.group(0)
                name = re.sub(self.cite_regex, " ", name)

            docket = ", ".join(
                [
                    match.group("docket")
                    for match in self.docket_regex.finditer(case["title"])
                ]
            )
            if not docket:
                docket_str = fields["field_description"][0]["#text"]
                docket = self.docket_regex.search(docket_str).group(0)

            name = re.sub(self.docket_regex, " ", name)
            # delete traces of multiple docket numbers
            name = re.sub(r"^(and|[&,])", "", name.strip()).strip()
            # print(urljoin("https://www.courts.nh.gov/sites/g/files/ehbemt471/files/",url))
            self.cases.append(
                {
                    "date": case_date,
                    "url": urljoin(
                        "https://www.courts.nh.gov/sites/g/files/ehbemt471/files/",
                        url,
                    ),
                    "name": name,
                    "docket": [docket],
                    "citation": [citation],
                }
            )

        # This flag will be set to True by the _download_backwards method
        if not self.paginate:
            return
        self.paginate = False  # prevent recursion

        logger.info(
            "Found %s results, will paginate through", json_response["total"]
        )
        for page in range(2, json_response["last_page"] + 1):
            logger.info("Paginating to page %s", page)
            self.url = self.url.replace(f"page={page-1}", f"page={page}")
            self.html = self._download()
            self._process_html()

    def set_request_parameters(
        self, year: int
    ) -> None:
        """Each year has a unique `field_document_subcategory` key, so we must
        set it accordingly

        :param year: full year integer
        """
        params = {
            "iterate_nodes": "true",
            # Will raise a KeyError if there is no proper year key, we will
            # need to manually correct this next year
            "q": self.base_filter.format(self.year_to_filter[year]),
            "sort": "field_date_posted|desc|ALLOW_NULLS",
            "filter_mode": self.filter_mode,
            "type": "document",
            "page": "1",
            "size": "25",
        }
        self.url = f"{self.base_url}?{urlencode(params)}"
        self.request["headers"] = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Host": "www.courts.nh.gov",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Cookie": "_ga_QQQTMDJKBH=GS2.1.s1764135560$o6$g1$t1764135583$j37$l0$h0; _ga=GA1.1.1221447934.1744971169",
        }

    def _download(self, request_dict={}):
        """Download using headless browser to bypass 403"""
        self.downloader_executed = True
        logger.info(f"Downloading URL via browser: {self.url}")

        # Get proxy from self.proxies; use HTTPS if available
        proxy = None
        if getattr(self, "proxies", None):
            proxy = self.proxies.get("https") or self.proxies.get("http")

        try:
            with sync_playwright() as p:
                browser_args = {"headless": True}
                if proxy:
                    browser_args["proxy"] = {"server": proxy}  # <-- set proxy here

                browser = p.firefox.launch(**browser_args)
                page = browser.new_page()
                # Set extra headers
                page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "en-US,en;q=0.9",
                })

                page.goto(self.url, timeout=60000)
                # Get JSON response from page
                content = page.evaluate(
                    "() => document.querySelector('pre')?.innerText || document.body.innerText"
                )
                browser.close()

                import json
                data = json.loads(content)
                logger.info(f"Download successful via proxy {proxy}")
                return data

        except Exception as e:
            logger.error(
                f"Browser download failed for {self.url} via proxy {proxy}: {e}")
            return {}

    def _download_backwards(self, start: int , end : int) -> None:
        if(start == end):
            logger.info(f"start year and end year is same.....")
            self.paginate = True
            self.set_request_parameters(start)
            logger.info("Backscraping year %s", start)
            self.html = self._download()
            self._process_html()
        else:
            logger.info(f"start year is {start} and end year is {end}")
            curr_year = start
            while curr_year<= end:
                logger.info(f"calling for year {curr_year}")
                self.paginate = True
                self.set_request_parameters(curr_year)
                self.html = self._download()
                self._process_html()
                curr_year += 1

    def make_backscrape_iterable(self, kwargs: Dict) -> List[int]:
        """The API exposes no date filter, so we must query a year
        and then paginate the results.
        """
        start = int(kwargs.get("backscrape_start") or self.start_year)
        end = int(kwargs.get("backscrape_end") or self.end_year)

        if start == end:
            self.back_scrape_iterable = [start]
        else:
            self.back_scrape_iterable = range(start, end + 1)


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        start_year = start_date.year
        end_year=end_date.year
        self._download_backwards(start_year,end_year)

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

    def _fetch_duplicate(self, data):
        pdf_url = str(data.get("pdf_url"))
        title = data.get("title")
        date = data.get("date")
        docket = data.get("docket")
        html_url = data.get("html_url")
        court_name = data.get("court_name")
        object_id = None
        if pdf_url.__eq__("") or (pdf_url is None) or pdf_url.__eq__("null"):
            if html_url.__eq__("") or (html_url is None) or html_url.__eq__("null"):
                return object_id
            else:
                query1 = {"html_url":html_url}
                dup1 = self.judgements_collection.find_one(query1)
                if not dup1 is None:
                    query2 = {"court_name": court_name, "date": date, "title": title, "docket": docket}
                    dup2 = self.judgements_collection.find_one(query2)
                    if not dup2 is None:
                        # Check if the document already exists and has been processed
                        processed = dup2.get("processed")
                        if processed == 10 or processed == 0:
                            raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
                        else:
                            object_id = dup2.get("_id")

        else:
            query3 = {"pdf_url":pdf_url}
            dup = self.judgements_collection.find_one(query3)
            if dup is None:
                query4 = {"court_name":court_name,"date":date, "title":title,"docket":docket}
                dup2=self.judgements_collection.find_one(query4)
                if not dup2 is None:
                    # Check if the document already exists and has been processed
                    processed = dup2.get("processed")
                    if processed == 10 or processed == 0:
                        raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
                    else:
                        object_id = dup2.get("_id")
            else:
                query4 = {
                    "court_name": court_name, "date": date, "title": title, "docket": docket}
                dup2 = self.judgements_collection.find_one(query4)
                if not dup2 is None:
                    # Check if the document already exists and has been processed
                    processed = dup2.get("processed")
                    if processed == 10 or processed == 0:
                        raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
                    else:
                        object_id = dup2.get("_id")
        return object_id

    def _download_via_playwright(self,pdf_url: str,save_path: str,warmup_url: Optional[str] = None) -> bool:
        try:

            with sync_playwright() as p:
                playwright_proxy = {
                    "server": "http://23.236.154.202:8800"
                }
                browser = p.firefox.launch(
                    headless=True,
                    proxy=playwright_proxy
                )
                page = browser.new_page()

                # Akamai/session warmup
                if warmup_url:
                    page.goto(warmup_url, wait_until="networkidle")

                with page.expect_download() as download_info:
                    page.evaluate(f'window.location.href = "{pdf_url}"')

                download = download_info.value
                download.save_as(save_path)

                browser.close()
                return True

        except Exception as e:
            print(f"[Playwright] PDF download failed: {e}")
            return False

    def _download_via_requests(self, pdf_url: str, save_path: str) -> None:
        us_proxy = CasemineUtil.get_us_proxy()

        response = requests.get(
            url=pdf_url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
            },
            proxies={
                "http": f"http://{us_proxy.ip}:{us_proxy.port}",
                "https": f"http://{us_proxy.ip}:{us_proxy.port}"
            },
            timeout=120
        )
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

    def download_pdf(self, data, objectId):
        pdf_url = data.get("pdf_url")
        html_url = data.get("html_url")
        year = int(data.get("year"))
        court_name = data.get("court_name")
        court_type = data.get("court_type")

        state_name = data.get(
            "circuit") if court_type == "Federal" else data.get("state")
        opinion_type = data.get("opinion_type")

        if opinion_type == "Oral Argument":
            path = f"/synology/PDFs/US/juriscraper/{court_type}/{state_name}/{court_name}/oral arguments/{year}"
        else:
            path = f"/synology/PDFs/US/juriscraper/{court_type}/{state_name}/{court_name}/{year}"

        os.makedirs(path, exist_ok=True)
        download_pdf_path = os.path.join(path, f"{objectId}.pdf")

        # -----------------------------
        # No PDF URL handling
        # -----------------------------
        if not pdf_url or pdf_url == "null":
            processed = 2 if not html_url or html_url == "null" else 0
            self.judgements_collection.update_one(
                {"_id": objectId}, {"$set": {"processed": processed}}
            )
            return download_pdf_path

        # -----------------------------
        # Try REQUESTS first
        # -----------------------------
        proxy_failures = 0
        while proxy_failures <= 10:
            try:
                self._download_via_requests(pdf_url, download_pdf_path)
                self.judgements_collection.update_one(
                    {"_id": objectId}, {"$set": {"processed": 0}}
                )
                return download_pdf_path

            except requests.RequestException as e:
                if "Unable to connect to proxy" in str(e):
                    proxy_failures += 1
                    continue
                else:
                    break

        # -----------------------------
        # Fallback → PLAYWRIGHT
        # -----------------------------
        print("[Fallback] Switching to Playwright")

        success = self._download_via_playwright(
            pdf_url=pdf_url,
            save_path=download_pdf_path,
            warmup_url=html_url
        )

        if success:
            self.judgements_collection.update_one(
                {"_id": objectId}, {"$set": {"processed": 0}}
            )
        else:
            self.judgements_collection.update_one(
                {"_id": objectId}, {"$set": {"processed": 2}}
            )

        return download_pdf_path

    def get_court_name(self):
        return "Supreme Court of New Hampshire"

    def get_court_type(self):
        return "state"

    def get_class_name(self):
        return "nh_p"

    def get_state_name(self):
        return "New Hampshire"
