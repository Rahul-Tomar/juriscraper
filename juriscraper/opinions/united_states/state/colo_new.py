from datetime import datetime
import requests

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from bs4 import BeautifulSoup, NavigableString, Tag
import re
from urllib.parse import urljoin
class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.url = "https://www.coloradojudicial.gov/supreme-court/opinions"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Host": "www.coloradojudicial.gov",
            "Referer": "https://www.google.com/",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",

        }

    def _download(self, request_dict={}):
        pass

    def _process_html(self):
        response = requests.get(url=self.url, headers=self.headers, proxies=self.proxies)
        # print(response.status_code)
        BASE_URL = "https://www.coloradojudicial.gov"
        CASE_RE = re.compile(r"\d{2}\s*\d{2}\s*CO")
        soup = BeautifulSoup(response.text, "html.parser")
        article = soup.find("article", attrs={"data-history-node-id": "13564"})
        if not article:
            raise Exception("Article not found")

        # 2. Locate the main content div
        content_div = article.select_one(
            "div.field--name-field-text.field--type-text-long"
        )
        if not content_div:
            raise Exception("Content div not found")

        # 3. Split content into blocks by <hr>
        blocks = []
        current_block = []

        for el in content_div.children:
            if isinstance(el, Tag) and el.name == "hr":
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                if isinstance(el, Tag):
                    current_block.append(el)

        if current_block:
            blocks.append(current_block)

        for block in blocks:

            # ---- DATE (anywhere in block) ----
            block_text = " ".join(
                el.get_text(" ", strip=True)
                for el in block
            )

            date_match = re.search(
                r"([A-Z][a-z]+ \d{1,2}, \d{4})", block_text
            )
            if not date_match:
                continue

            date = self.normalize_date_or_fail(date_match.group(1))
            res = CasemineUtil.compare_date(self.crawled_till, date)
            if res == 1:
                continue
            # ---- CASES ----
            for el in block:
                if el.name != "p":
                    continue

                for a in el.find_all("a", href=True):

                    # Normalize case number (fixes 20<span>25 CO 58</span>)
                    citation_number = re.sub(r"\s+", " ",
                                         a.get_text(" ", strip=True))
                    # Normalize split year: "20 25 CO 58" → "2025 CO 58"
                    citation_number = re.sub(r"(\d{2})\s+(\d{2})\s*(CO)",
                                         r"\1\2 \3",
                                         citation_number)

                    # HARD FILTER: real cases only
                    if not CASE_RE.search(citation_number):
                        continue

                    href = a.get("href")
                    if not href:
                        continue

                    url = urljoin(BASE_URL, href)

                    title , dockets  = self.extract_title_and_dockets_from_anchor(a)

                    if not title:
                        continue

                    inner_response = requests.get(url=url, headers=self.headers,
                                                  proxies=self.proxies)
                    # print(inner_response.status_code)
                    # https://www.coloradojudicial.gov/system/files/opinions-2025-12/24SA276_24SA308_24SA309.pdf
                    inner_soup = BeautifulSoup(inner_response.text,
                                               "html.parser")

                    pdf_tag = inner_soup.select_one(
                        "span.file--application-pdf a[href$='.pdf']"
                    )

                    if pdf_tag:
                        pdf_url = urljoin(BASE_URL, pdf_tag["href"])
                    else:
                        pdf_url = None
                    if not pdf_url:
                        pdf_url=url
                    case = {
                        "date": date,
                        "citation": citation_number,
                        "docket": dockets,
                        "name": title,
                        "url": pdf_url,
                    }
                    print(case)
                    if not self.validate_case(case):
                        raise Exception(f"Invalid case data: {case}")
                       # 8 Dec data  directly have pdf_url
                    self.cases.append({
                        "date": date,
                        "citation": citation_number,
                        "docket":dockets,
                        "name": title,
                        "url": pdf_url,
                        "status":self.status
                    })

    def validate_case(self, case: dict) -> bool:
        try:
            # ---- DATE ----
            datetime.strptime(case["date"], "%d/%m/%Y")

            # ---- CITATION ----
            if not re.fullmatch(r"\d{4}\s+CO\s+\d+[A-Z]?", case["citation"]):
                return False

            # ---- DOCKETS ----
            if not isinstance(case["docket"], list) or not case["docket"]:
                return False

            for d in case["docket"]:
                if not re.fullmatch(r"\d{2}(SA|SC)\d+", d):
                    return False

            # ---- TITLE ----
            if not case["name"].strip():
                return False

            if re.search(r"\b\d{2}(SA|SC)\d+\b", case["name"]):
                return False

            # ---- PDF URL ----
            # if case["url"] is not None:
            #     if not case["url"].startswith("http") or not case[
            #         "url"].endswith(".pdf"):
            #         return False

            return True

        except Exception:
            return False

    def normalize_date_or_fail(self,date_str: str) -> str:
        DATE_INPUT_RE = re.compile(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$")
        if not date_str or not DATE_INPUT_RE.match(date_str):
            raise ValueError(f"Invalid date format: '{date_str}'")

        try:
            dt = datetime.strptime(date_str, "%B %d, %Y")
        except ValueError:
            raise ValueError(f"Unparseable date: '{date_str}'")

        return dt.strftime("%d/%m/%Y")

    def extract_title_and_dockets_from_anchor(self, a):
        parts = []
        DOCKET_RE = re.compile(r"\b\d{2}(?:SA|SC)\d+\b")
        for sib in a.next_siblings:

            # Stop at next case
            if isinstance(sib, Tag) and sib.name == "a":
                break

            # Stop on <br><br>
            if isinstance(sib, Tag) and sib.name == "br":
                nxt = sib.next_sibling
                if isinstance(nxt, Tag) and nxt.name == "br":
                    break
                continue

            if isinstance(sib, NavigableString):
                parts.append(sib.strip())
            elif isinstance(sib, Tag):
                parts.append(sib.get_text(" ", strip=True))

        raw_text = " ".join(parts)
        raw_text = re.sub(r"\s+", " ", raw_text).strip()

        dockets = DOCKET_RE.findall(raw_text)

        seen = set()
        dockets = [d for d in dockets if not (d in seen or seen.add(d))]

        title = DOCKET_RE.sub("", raw_text)
        title = re.sub(r"\s*&\s*", " ", title)
        title = re.sub(r"\s+", " ", title).strip(" ,")

        # ---- VALIDATION (CRITICAL) ----
        if DOCKET_RE.search(title):
            raise ValueError(
                f"Title still contains docket after cleaning: '{title}'"
            )

        return title, dockets

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return len(self.cases)

    def get_class_name(self):
        return "colo_new"

    def get_court_name(self):
        return "Colorado Supreme Court"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Colorado"
