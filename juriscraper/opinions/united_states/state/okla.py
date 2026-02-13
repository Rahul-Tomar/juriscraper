import re
import os
import requests
from fontTools.misc.plistlib import end_date
from lxml import html
from datetime import datetime
from bs4 import BeautifulSoup
from pdfkit import pdfkit
from selenium.webdriver.support.wait import WebDriverWait

from casemine.casemine_util import CasemineUtil
from casemine.proxy_manager import ProxyManager
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from sample_caller import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        # self.url = "https://www.oscn.net/decisions/ok/90"
        self.year = datetime.today().year
        self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKCSSC&year={self.year}&level=1"
        self.status = "Published"
        self.expected_content_types = ["text/html"]
        self.case_base_url = "https://www.oscn.net/dockets/GetCaseInformation.aspx?db=Appellate&number="
        self.proxies= {
            "http": "http://156.241.224.100:8800",
            "https": "http://156.241.224.100:8800"
        }
        self.proxy_usage_count = 0
        self._opt_attrs = [
            "adversary_numbers",
            "causes",
            "dispositions",
            "divisions",
            "docket_attachment_numbers",
            "docket_document_numbers",
            "docket_numbers",
            "judges",
            "lower_courts",
            "lower_court_judges",
            "lower_court_numbers",
            "nature_of_suit",
            "citations",
            "parallel_citations",
            "summaries",
            "case_name_shorts",
            "child_courts",
            "authors",
            "joined_by",
            "per_curiam",
            "types",
            "other_dates",
            "html_urls",
            "response_htmls",
            "opinion_types",
            "teasers",
            "revision_status"
        ]
        self._opt_attrs = self._opt_attrs + ["cite_info_html"]
        self.valid_keys.update({
            "cite_info_html"
        })
        self._all_attrs = self._req_attrs + self._opt_attrs

        for attr in self._all_attrs:
            self.__setattr__(attr, None)

    def _get_cite_info_html(self):
        return self._get_optional_field_by_id("cite_info_html")

    def fetch_oscn_page_with_proxy(self, url, proxy_host, proxy_port):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            f"--proxy-server={proxy_host}:{proxy_port}")
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches",
                                               ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # ❌ Do NOT use headless when CAPTCHA might appear
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            print(f"Opening page with proxy {proxy_host}:{proxy_port}: {url}")
            driver.get(url)

            print("\n🔒 If CAPTCHA appears, please click 'Verify'.")
            print("Waiting for successful page load after verification...")

            try:
                # Wait until the page changes title or the main element appears
                WebDriverWait(driver, 180).until(
                    lambda d: "Turnstile" not in d.title
                              and "Why am I seeing this?" not in d.title
                              and d.find_elements(By.XPATH,
                                                  "//p[@id='document']")
                )
            except Exception:
                print(
                    "⚠️ Timed out waiting for CAPTCHA verification or page load.")

            # Ensure the HTML is from the verified page
            time.sleep(3)
            page_source = driver.page_source

            if "Turnstile" in page_source or "Why am I seeing this?" in page_source:
                print("❌ Still stuck on CAPTCHA page.")
            else:
                print("✅ CAPTCHA verification successful — page loaded!")

            file_path = "/home/gaugedata/Downloads/oscn_verified_page.html"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_source)
            print(f"📄 Saved verified page to: {file_path}")

            return page_source

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

        finally:
            time.sleep(5)
            driver.quit()

    def _process_html(self, start_date: datetime, end_date: datetime):
        base_url = "https://www.oscn.net/dockets/"
        cite_html = ""
        div = ""

        # First, check if self.html contains a CAPTCHA
        page_title = self.html.xpath('//title/text()')
        if page_title and (
            "Turnstile" in page_title[0] or "Why am I seeing this?" in
            page_title[0]):
            print("CAPTCHA detected. Fetching page via Selenium with proxy...")
            proxy_manager = ProxyManager()
            proxy = proxy_manager.get_random_proxy()
            page_content = self.fetch_oscn_page_with_proxy(self.url, proxy[0],
                                                           proxy[1])
            if not page_content:
                print("Failed to bypass CAPTCHA. Exiting _process_html.")
                return
            self.html = html.fromstring(page_content)

        # Convert HTML to string and print
        html_str = html.tostring(self.html, pretty_print=True,
                                 encoding="unicode")
        print("=== HTML CONTENT START ===")
        # print(html_str)
        print("=== HTML CONTENT END ===")

        # Iterate over case rows
        for row in self.html.xpath(".//p[@id='document']"):
            self.revision_status = 0
            pdf_url = ""
            proxy_manager = ProxyManager()
            proxy = proxy_manager.get_random_proxy()

            if self.proxy_usage_count >= 4:
                self.proxies = {
                    "http": f"http://{proxy[0]}:{proxy[1]}",
                    "https": f"http://{proxy[0]}:{proxy[1]}",
                }
                logger.info(f"Updated proxy is {self.proxies}")
                self.proxy_usage_count = 0

            text = row.xpath(".//a/text()")
            url = row.xpath(".//a/@href")[0]
            case = text[0]

            try:
                docket, citation, date, name = self.parse_oklahoma_case(case)
            except Exception:
                docket, citation, date, name = None, None, None, None

            print("Docket:", docket)

            if date and start_date < datetime.strptime(date.strip(),"%m/%d/%Y") < end_date:
            # a,b = 5,10
            # if a<b:
                docket = docket.replace("\xa0", " ")
                print(f"Date of the case: {date}")

                # Fetch individual case page
                try:
                    full_url = "https://www.oscn.net/applications/oscn/" + url
                    time.sleep(4)
                    response_html = requests.get(full_url,
                                                 headers=self.request[
                                                     "headers"],
                                                 proxies=self.proxies)
                    html_content = response_html.text
                    print("#############")
                    # print(html_content)
                    print("#############")
                    curr_status = self.detect_publication_status(html_content)
                    if curr_status=="Published":
                        status="Published"
                        revision_status=0
                    elif curr_status=="Unpublished":
                        status="Unpublished"
                        revision_status=0
                    else:
                        status = "Unknown"
                        revision_status = 1

                    case_inner_url , case_number = self.extract_case_href_and_number(html_content)

                    if case_inner_url and case_number:
                        case_hit_url = self.case_base_url+case_number
                        case_html_content = self.fetch_html_with_proxy(case_hit_url,"192.126.184.28","8800")
                        # print(case_html_content)
                        pdf_link = self.extract_opin_ordr_pdf(case_html_content)
                        if pdf_link:
                            pdf_url = "https://www.oscn.net/dockets/" + pdf_link
                            # print(f"Got the pdf url :- {pdf_url}")

                    # Check for CAPTCHA again
                    if "OSCN Turnstile" in html_content or "cf-turnstile" in html_content:
                        print(
                            "CAPTCHA detected on case page. Using Selenium...")
                        html_content = self.fetch_oscn_page_with_proxy(
                            full_url, proxy[0], proxy[1])

                    tree = html.fromstring(html_content)
                    cite_text = tree.xpath("//div[@class='tmp-citationizer']")
                    if cite_text:
                        cite_html = html.tostring(cite_text[0],
                                                  pretty_print=True).decode(
                            "utf-8")

                    div_content = tree.xpath(
                        "//div[@class='container-fluid sized']")
                    if div_content:
                        div = html.tostring(div_content[0],pretty_print=True).decode("utf-8")

                    # PDF URL extraction (same as your original logic)
                    table = tree.xpath("//table[@class='docketlist ocis']")
                    if table:
                        for tr in table[0].xpath(".//tbody//tr"):
                            td = tr.xpath(".//td[2]//nobr/text()")
                            dt = tr.xpath(".//td[1]//nobr/text()")
                            dt_str = str(dt[0]).strip()
                            if td[0] in ["OPIN", "ORDR"]:
                                url1 = tr.xpath(
                                    ".//td[3]//div[@class='description-wrapper']//a[@class='doc-pdf']/@href")[
                                    0]
                                if td[0] == 'ORDR':
                                    dt_str = dt_str.replace("-", "/")
                                    if dt_str != date:
                                        continue
                                pdf_url = base_url + url1
                                print(f"Got PDF URL: {pdf_url}")

                except Exception as e:
                    logger.info(f"Error fetching case details: {e}")

                cit_arr = [citation] if citation else []
                print(div)
                self.cases.append({
                    "date": date,
                    "name": name,
                    "docket": [docket],
                    "citation": cit_arr,
                    "url": pdf_url,
                    "cite_info_html": cite_html,
                    "html_url": full_url,
                    "response_html": div,
                    "status":status,
                    "revision_status":revision_status
                })
                self.proxy_usage_count += 1
                break

    def detect_publication_status(self,html_content: str) -> str:
        """
        Detects the publication status of an Oklahoma case based on HTML content.

        Args:
            html_content (str): The HTML content of the case page.

        Returns:
            str: One of 'Published', 'Semi-Published', 'Unpublished'.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all <p align="center"> tags
        p_tags = soup.find_all("p", align="center")

        for p in p_tags:
            font = p.find("font", color="#ff0000")
            if font:
                text = font.get_text(strip=True).upper()

                if "NOTICE: THIS OPINION HAS NOT BEEN RELEASED FOR PUBLICATION. UNTIL RELEASED, IT IS SUBJECT TO REVISION OR WITHDRAWAL." in text:
                    return "Unknown"
                elif "FOR PUBLICATION IN OBJ ONLY. NOT FOR OFFICIAL PUBLICATION" in text:
                    return "Unpublished"

        # If neither of the above tags are present, assume Published
        return "Published"

    def extract_opin_ordr_pdf(self,case_html_content):
        """
        Parses the case HTML content and finds the PDF link for docket entries
        with code 'OPIN' or 'ORDR'.

        Returns:
            pdf_links (list): List of PDF URLs found
        """
        soup = BeautifulSoup(case_html_content, "html.parser")
        pdf_links = []

        # Find all rows in docket table
        rows = soup.select("table.docketlist tr.docketRow")

        for row in rows:
            code_tag = row.select_one("td font.docket_code nobr")
            if not code_tag:
                continue

            code_text = code_tag.get_text(strip=True).upper()

            # Check if code is OPIN or ORDR
            if code_text in ("OPIN", "ORDR"):
                # Find PDF link
                pdf_tag = row.select_one("a.doc-pdf")
                if pdf_tag and pdf_tag.has_attr("href"):
                    return pdf_tag["href"]

        return None

    def parse_oklahoma_case(self, line: str):
        """
        Handles all formats like:
        2025 OK 1, 562 P.3d 612, 01/13/2025, STATE ex rel. OBA v. JONES
        2025 OK 12, 02/25/2025, CONNER v. STATE
        2025 OK 14, 03/03/2025, RE SUSPENSION OF CERTIFICATES ...
        """
        pattern = re.compile(
            r'^(?P<year>\d{4})\s+OK\s+(?P<case_no>\d+),?\s*'
            r'(?:(?P<volume>\d+)\s+P\.3d\s+(?P<page>\d+),\s*)?'
            r'(?P<date>\d{2}/\d{2}/\d{4}),\s*'
            r'(?P<title>.+)$'
        )

        match = pattern.match(line.strip())
        if not match:
            return None, None, None, None

        data = match.groupdict()

        docket = f"{data['year']} OK {data['case_no']}"
        citation = f"{data['volume']} P.3d {data['page']}" if data[
                                                                  'volume'] and \
                                                              data[
                                                                  'page'] else None
        date = data['date']
        name = data['title'].strip()

        return docket, citation, date, name

    @staticmethod
    def cleanup_content(content):
        tree = html.fromstring(content)
        core_element = tree.xpath("//*[@id='oscn-content']")[0]
        return html.tostring(
            core_element, pretty_print=True, encoding="unicode"
        ).encode("utf-8")

    def fetch_html_with_proxy(self,url, proxy_host, proxy_port):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            f"--proxy-server={proxy_host}:{proxy_port}")
        chrome_options.add_experimental_option("excludeSwitches",
                                               ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            print(f"[+] Opening: {url}")
            driver.get(url)
            time.sleep(3)

            if "Turnstile" in driver.page_source:
                print("⚠ CAPTCHA detected. Solve manually & press Enter.")
                input()

            return driver.page_source

        finally:
            driver.quit()

    def _get_revision_status(self):
        return str(self.revision_status) if self.revision_status is not None else ""

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        if not self.downloader_executed:
            self.html = self._download()
            self._process_html(start_date , end_date)


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

    def extract_case_href_and_number(self,html_content):
        soup = BeautifulSoup(html_content, "html.parser")

        p_tag = soup.find("p", align="CENTER")
        if not p_tag:
            print("⚠ No <p align='CENTER'> found")
            return None, None

        a_tag = p_tag.find("a")
        href = a_tag["href"] if a_tag and a_tag.has_attr("href") else None

        case_number = None
        if href:
            match = re.search(r'number=(\d+)', href)
            if match:
                case_number = match.group(1)

        return href, case_number

    def _process_opinion(self, data) -> bool:
        self.flag = False
        obj_id = None
        try:
            duplicate_id = self._fetch_duplicate(data)
            obj_id = self.update_insert_meta(data, duplicate_id)
        except Exception as ex:
            if not str(ex).__eq__("Judgment already Exists!"):
                raise Exception(ex)
        if obj_id is not None:
            content_pdf = self.download_pdf(data, obj_id)
        # flag = saveContent(judId, contentPdf)
        return self.flag

    def sanitize_opinion_html_for_pdf(self, div_html: str) -> str:
        """
        Returns clean, court-style HTML BODY content only.
        No <html>, <head>, or <body> nesting.
        Safe for direct PDF rendering.
        """
        if not div_html:
            return ""

        # Remove OSCN junk markers
        div_html = re.sub(r'BEGIN DOCUMENT', '', div_html, flags=re.I)

        soup = BeautifulSoup(div_html, "lxml")

        # Remove html/head/body if present
        for tag in soup.find_all(["html", "head", "body"]):
            tag.unwrap()

        # Remove scripts and non-printable elements
        for tag in soup(
            ["script", "style", "iframe", "object", "embed", "noscript"]):
            tag.decompose()

        # Remove hyperlinks but keep text
        for a in soup.find_all("a"):
            a.unwrap()

        # Remove raw URLs from visible text
        for node in soup.find_all(string=True):
            cleaned = re.sub(r'https?://\S+', '', node)
            cleaned = re.sub(r'www\.\S+', '', cleaned)
            node.replace_with(cleaned)

        # Strip unwanted attributes
        for tag in soup.find_all(True):
            for attr in ("href", "onclick", "id", "class", "style", "name"):
                tag.attrs.pop(attr, None)

        # Replace <br> with line breaks
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # --- Court-style CSS (INLINE, BODY-SAFE) ---
        css = """
    <style>
    body {
        font-family: "Times New Roman", Georgia, serif;
        font-size: 12pt;
        line-height: 1.6;
        margin: 1.25in 1in;
        color: #000;
    }

    p {
        margin: 0 0 12px 0;
        text-align: justify;
    }

    blockquote {
        margin: 12px 36px;
        font-style: italic;
    }

    hr {
        border: none;
        border-top: 1px solid #000;
        margin: 18px 0;
    }

    center {
        text-align: center;
        margin: 12px 0;
    }

    strong { font-weight: bold; }
    em { font-style: italic; }

    sup {
        font-size: 9pt;
        vertical-align: super;
    }

    .page-break {
        page-break-before: always;
    }
    </style>
    """

        # Return BODY CONTENT ONLY (NO <html><body>)
        return css + str(soup)


    def download_pdf(self, data, objectId):
        pdf_url = data.get('pdf_url')
        html_url = data.get('html_url')
        response_html = data.get('response_html')

        year = int(data.get('year'))
        court_name = data.get('court_name')
        court_type = data.get('court_type')

        if str(court_type) == 'Federal':
            state_name = data.get('circuit')
        else:
            state_name = data.get('state')

        opinion_type = data.get('opinion_type')

        # Build directory path
        if str(opinion_type) == "Oral Argument":
            path = (
                "/synology/PDFs/US/juriscraper/" + court_type + "/" +
                state_name + "/" +
                court_name + "/" +
                "oral arguments/" +
                str(year)
            )
        else:
            path = (
                "/synology/PDFs/US/juriscraper/" + court_type + "/" +
                state_name + "/" +
                court_name + "/" +
                str(year)
            )

        obj_id = str(objectId)
        download_pdf_path = os.path.join(path, f"{obj_id}.pdf")

        # ----------------------------
        # CASE 1: NO PDF URL → TRY HTML
        # ----------------------------
        if not pdf_url or str(pdf_url).strip() in ["", "null"]:
            if not html_url or str(html_url).strip() in ["", "null"]:
                # No pdf + No html
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
                return None

            # Convert HTML → PDF using response_html as-is (NO image logic)
            try:
                os.makedirs(path, exist_ok=True)

                html_data = response_html  # No modifications

                config = pdfkit.configuration(
                    wkhtmltopdf="/usr/bin/wkhtmltopdf")

                pdfkit.from_string(
                    html_data,
                    download_pdf_path,
                    configuration=config,
                    options={
                        "page-size": "Letter",
                        "encoding": "UTF-8",
                        "quiet": ""
                    }
                )

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )
                return download_pdf_path

            except Exception as e:
                print("HTML → PDF Error:", e)
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
                return None

        # -------------------------------------
        # CASE 2: VALID PDF URL → DOWNLOAD PDF
        # -------------------------------------
        i = 0
        while True:
            try:
                os.makedirs(path, exist_ok=True)

                # us_proxy = CasemineUtil.get_us_proxy()

                response = requests.get(
                    url=pdf_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) "
                            "Gecko/20100101 Firefox/136.0"
                        )
                    },
                    proxies={
                        # "http": f"http://{us_proxy.ip}:{us_proxy.port}",
                        # "https": f"http://{us_proxy.ip}:{us_proxy.port}"
                        "http": "http://156.241.224.100:8800",
                        "https": "http://156.241.224.100:8800"
                    },
                    timeout=120
                )

                response.raise_for_status()

                with open(download_pdf_path, 'wb') as file:
                    file.write(response.content)

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )
                break

            except requests.RequestException as e:
                # Retry only for proxy failures
                if "Unable to connect to proxy" in str(e):
                    i += 1
                    if i > 10:
                        break
                    continue
                else:
                    print(f"Error while downloading the PDF: {e}")
                    self.judgements_collection.update_one(
                        {"_id": objectId},
                        {"$set": {"processed": 2}}
                    )
                    break

        return download_pdf_path

    def update_insert_meta(self, data, existing_id):
        if existing_id is None:
            inserted_doc = self.judgements_collection.insert_one(data)
            object_id = inserted_doc.inserted_id
            self.flag = True
            return object_id
        else:
            self.judgements_collection.update_one({'_id': existing_id}, {'$set': data})
            return existing_id

    def get_court_name(self):
        return "Supreme Court of Oklahoma"

    def get_state_name(self):
        return "Oklahoma"

    def get_class_name(self):
        return "okla"

    def get_court_type(self):
        return "state"
