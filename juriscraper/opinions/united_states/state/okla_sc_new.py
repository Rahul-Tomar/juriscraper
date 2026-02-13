from datetime import datetime
from xmlrpc.client import boolean
import pdfkit
import os
import requests
from lxml import html as lxml_html
from lxml import etree
from casemine.proxy_manager import ProxyManager
from sample_caller import logger
import re
from bs4 import BeautifulSoup
from juriscraper.opinions.united_states.state import okla, oklacrimapp
from lxml import html

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from playwright.sync_api import sync_playwright

class Site(oklacrimapp.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.year = datetime.today().year
        self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKCSSC&year=2026&level=1"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }
        self.US_PROXIES = [
            # ("23.236.154.202", 8800),
            # ("23.236.154.249", 8800),
            # ("23.236.197.155", 8800),
            # ("23.236.197.227", 8800),
            # ("23.236.197.153", 8800),
            # ("156.241.221.148", 8800),
            ("156.241.216.136", 8800),
            ("156.241.216.8", 8800),
            ("156.241.216.194", 8800),
            ("156.241.221.92", 8800),
            ("156.241.216.136", 8800),
            ("156.241.216.8", 8800),
            ("156.241.216.194", 8800),
            ("156.241.221.92", 8800),
            ("23.236.154.202", 8800),
            ("23.236.154.249", 8800),
            ("23.236.197.155", 8800),
            ("23.236.197.227", 8800),
            ("23.236.197.153", 8800),
            ("156.241.221.148", 8800),
        ]

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
        self._CASE_META_PATTERN = re.compile(
            r'^(?P<docket>\d{4}\s+OK\s+CR\s+\d+),\s+'
            r'(?:(?P<citation>\d+\s+P\.3d\s+\d+),\s+)?'
            r'(?P<date>\d{2}/\d{2}/\d{4}),\s+'
            r'(?P<name>.+)$'
        )
        self._opt_attrs = self._opt_attrs + ["cite_info_html"]
        self._all_attrs = self._req_attrs + self._opt_attrs

        for attr in self._all_attrs:
            self.__setattr__(attr, None)


    def _process_html(self, start_date : datetime , end_date : datetime):
        base_url = "https://www.oscn.net/dockets/"
        cite_html = ""
        div = ""
        summary = ""
        if self.html is None:
            self._download()

        for row in self.html.xpath(".//p[@id='document']"):
            pdf_url = ""
            proxy_manager = ProxyManager()
            proxy = proxy_manager.get_random_proxy()

            if self.proxy_usage_count >= 4:
                self.proxies = {
                    "http": f"http://{proxy[0]}:{proxy[1]}",
                    "https": f"http://{proxy[0]}:{proxy[1]}",
                }
                logger.info(f"updated proxy is {self.proxies}")
                self.proxy_usage_count = 0

            text = row.xpath(".//a/text()")
            print(text)
            url = row.xpath(".//a/@href")[0]
            case = text[0]
            parts = case.split(", ")

            docket, citation, date, name = None, None, None, None
            case_text = text[0].replace("\xa0", " ").strip()
            citation, parallel_citation, date, name = self.parse_oklahoma_case(case_text)
            content = ''
            # if len(parts)==2:
            #     docket , name = parts
            #     date = "01/01/2024"
            # elif len(parts)==4:
            #     docket, citation, date, name = parts
            #     citation = citation.replace("\xa0"," ")
            #
            # elif len(parts)==3:
            #     if "/" in parts[1]:
            #         docket, date, name = parts
            #     else:
            #         docket, citation, name = parts
            #         date = "01/01/2024"
            # if name=='OKLAHOMA ex rel. STATE BOARD OF EXAMINERS OF CERTIFIED COURTROOM INTERPRETERS v. ALVARADO':

            parsed_date = datetime.strptime(date.strip(), "%m/%d/%Y")

            # if parsed_date.month == 9:
            if datetime.strptime(date.strip(),
                                 "%m/%d/%Y") >= start_date and datetime.strptime(
                date.strip(), "%m/%d/%Y") <= end_date:
                # docket=docket.replace("\xa0"," ")
                print(f"date of the case is {date}")

                try:
                    # print(f"getting result of docket {docket}")
                    # print(f"hitting url {url} for html and cite html")
                    # time.sleep(4)
                    if not url.startswith("https"):
                        url = "https://www.oscn.net/applications/oscn/" + url
                        print(url)

                    response_html=''
                    for ip, port in self.US_PROXIES:
                        proxy = self.make_proxy(ip, port)

                        try:
                            headers = {
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                "Accept-Encoding": "gzip, deflate, br, zstd",
                                "Accept-Language": "en-US,en;q=0.5",

                            }
                            response_html = requests.get(url,
                                                         headers=headers,
                                                         proxies=proxy)
                            print(
                                f"Trying {ip}:{port} → {response_html.status_code}")
                            if response_html.status_code == 200:
                                break

                        except requests.RequestException as e:
                            print(f"Proxy failed {ip}:{port} → {e}")
                            continue

                    soup = BeautifulSoup(response_html.text, "lxml")
                    content = str(soup)
                    container = soup.select_one("#tmp-style")
                    link = container.find("a", href=re.compile(
                        r"GetCaseInformation\.asp"))
                    docket = ''
                    pdf_page_url = ''
                    if link:
                        docket = link.get_text(strip=True)
                        full_url = "https://www.oscn.net/dockets/GetCaseInformation.aspx?db=Appellate&number=" + docket

                    # 2️⃣ Fallback: extract from plain text
                    if not docket:
                        text = soup.get_text(" ", strip=True)
                        match = re.search(r"Case Number:\s*([A-Z0-9\-]+)",
                                          text)
                        if match:
                            docket = match.group(1)
                    if not docket:
                        docket = citation  # If docket is not present we will insert citation
                    html_content = response_html.text

                    tree = html.fromstring(html_content)
                    # print(html_content)
                    cite_text = tree.xpath("//div[@class='tmp-citationizer']")
                    cite_html = html.tostring(cite_text[0],
                                              pretty_print=True).decode(
                        "utf-8")
                    summary = tree.xpath(
                        "string(//div[@class='de-writing']/p)")
                    div_content = tree.xpath(
                        "//div[@class='container-fluid sized']")
                    if div_content:
                        tmp = div_content[0].xpath(".//div[@id='opinions-navigation']")

                        if tmp:
                            tmp[0].getparent().remove(
                                tmp[0])

                        tmp_citationizer = div_content[0].xpath(
                            ".//div[@class='tmp-citationizer']")
                        if tmp_citationizer:
                            tmp_citationizer[0].getparent().remove(
                                tmp_citationizer[0])

                        raw_html = html.tostring(div_content[0],
                                                 pretty_print=True).decode(
                            "utf-8")
                        soup = BeautifulSoup(raw_html, "lxml")

                        # Remove navigation bar
                        nav = soup.find(id="opinions-navigation")
                        if nav:
                            nav.decompose()

                        # Remove scripts and styles
                        for tag in soup(["script", "style"]):
                            tag.decompose()

                        div = soup.prettify()

                        anchor_text = tree.xpath(
                            "//div[@id='tmp-style']//a/text()")
                        if anchor_text:
                            case_number = anchor_text[0]
                            if case_number:
                                print(f"got the case number {case_number}")
                                # full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + case_number
                                if "; " in case_number:
                                    match = re.search(r'^(\d+);', case_number)
                                    if match:
                                        number = match.group(1)
                                        # full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + number

                                if "SCBD" in case_number:
                                    number_match = re.search(r"SCBD-(\d+)",
                                                             case_number)
                                    if number_match:
                                        extracted_number = number_match.group(
                                            1)
                                        print(
                                            f"Extracted number: {extracted_number}")
                                        # full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + extracted_number
                                print(
                                    f"getting the content for pdf from the url {full_url}")
                                get_pdf_html = ""
                                for ip, port in self.US_PROXIES:
                                    proxy = self.make_proxy(ip, port)
                                    get_pdf_html = requests.get(full_url,
                                                                headers=self.headers,
                                                                proxies=proxy)
                                    print(
                                        f"Trying {ip}:{port} → {get_pdf_html.status_code}")
                                    if get_pdf_html.status_code == 200:
                                        break
                                if get_pdf_html.status_code != 200:
                                    raise Exception

                                content = get_pdf_html.text
                                # print(content)
                                if "OSCN Turnstile" in content or "cf-turnstile" in content:
                                    print("captcha")
                                    content = self.fetch_oscn_page_with_proxy(
                                        full_url, proxy[0], proxy[1])

                                content1 = html.fromstring(content)
                                table = content1.xpath(
                                    "//table[@class='docketlist ocis']")
                                if table:
                                    trow = table[0].xpath(".//tbody//tr")
                                    for tr in trow:
                                        td = tr.xpath(".//td[2]//nobr/text()")
                                        dt = tr.xpath(".//td[1]//nobr/text()")
                                        dt_str = str(dt[0]).strip()
                                        if td[0] == 'OPIN':
                                            url1 = tr.xpath(
                                                ".//td[3]//div[@class='description-wrapper']//a[@class='doc-pdf']/@href")[
                                                0]
                                            pdf_url = base_url + url1
                                        elif td[0] == 'ORDR':
                                            dt_str = dt_str.replace("-", "/")
                                            url1 = tr.xpath(
                                                ".//td[3]//div[@class='description-wrapper']//a[@class='doc-pdf']/@href")[
                                                0]
                                            if dt_str == date:
                                                print(
                                                    f"Date matches for ORDR row. PDF URL: {url1}")
                                                pdf_url = base_url + url1

                                else:
                                    pdf_url = ""
                                # print(f"got the pdf url {pdf_url}")
                    else:
                        logger.info(
                            "no div with calssname container-fluid sized present")
                except Exception as e:
                    logger.info(
                        f"inside the exception block in okla class ..... {e}")
                # print("-------------------------------------------------------------------------------------------------------------------")
                cit_arr = []
                if citation is not None:
                    cit_arr.append(citation)
                if pdf_url:
                    if not pdf_url.startswith("https"):
                        pdf_url = "https://www.oscn.net/applications/oscn/" + pdf_url
                if date:
                    date = datetime.strptime(date, "%m/%d/%Y").strftime(
                        "%d %b , %Y")
                status = self.detect_publication_status(div)
                revision_status = 0  # by default for published
                if status == "Unpublished":
                    revision_status = 0
                elif status == "Unknown":
                    revision_status = 1

                # div = self.extract_opinion_html(content)
                # if date:
                #     date = datetime.strptime(date, "%m/%d/%Y").strftime("%d %b , %Y")
                self.cases.append(
                    {
                        "date": date,
                        "name": name,
                        "docket": [docket],
                        "status":status,
                        "revision_status":revision_status,
                        "citation": cit_arr,
                        "url": pdf_url,
                        "cite_info_html": cite_html,
                        "html_url": url,
                        "response_html": div,
                        "summary": summary
                    }
                )
                self.proxy_usage_count += 1
                # break

    def extract_opinion_html(self, html: str) -> str:
        """
        Extracts ALL OSCN document blocks and concatenates them.
        This handles multi-section opinions correctly.
        """

        blocks = re.findall(
            r"<!--\s*BEGIN DOCUMENT\s*-->(.*?)<!--\s*END DOCUMENT\s*-->",
            html,
            flags=re.I | re.S
        )

        if not blocks:
            raise ValueError("BEGIN/END DOCUMENT markers not found")

        combined_html = "\n".join(blocks)

        soup = BeautifulSoup(combined_html, "lxml")

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        return soup.prettify()

    def download_pdf(self, data, objectId):
        import os
        import requests
        import pdfkit
        from bs4 import BeautifulSoup

        pdf_url = data.get("pdf_url")
        response_html = data.get("response_html")

        year = int(data.get("year"))
        court_name = data.get("court_name")
        court_type = data.get("court_type")

        if str(court_type) == "Federal":
            state_name = data.get("circuit")
        else:
            state_name = data.get("state")

        opinion_type = data.get("opinion_type")

        # -------- BUILD PATH --------
        if str(opinion_type) == "Oral Argument":
            path = (
                "/synology/PDFs/US/juriscraper/"
                + court_type + "/"
                + state_name + "/"
                + court_name + "/oral arguments/"
                + str(year)
            )
        else:
            path = (
                "/synology/PDFs/US/juriscraper/"
                + court_type + "/"
                + state_name + "/"
                + court_name + "/"
                + str(year)
            )

        obj_id = str(objectId)
        download_pdf_path = os.path.join(path, f"{obj_id}.pdf")

        os.makedirs(path, exist_ok=True)

        # ==========================================================
        # CASE 1: NO PDF URL → GENERATE PDF FROM CLEANED HTML
        # ==========================================================
        if not pdf_url or str(pdf_url).strip().lower() in ["", "null"]:

            if not response_html:
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
                return None

            try:
                soup = BeautifulSoup(response_html, "lxml")

                # Remove images
                for img in soup.find_all("img"):
                    img.decompose()

                # Remove links (keep text)
                for a in soup.find_all("a"):
                    a.unwrap()

                # Remove scripts/styles
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()

                clean_html = soup.prettify()

                config = pdfkit.configuration(
                    wkhtmltopdf="/usr/bin/wkhtmltopdf"
                )

                pdfkit.from_string(
                    clean_html,
                    download_pdf_path,
                    configuration=config,
                    options={
                        "page-size": "Letter",
                        "encoding": "UTF-8",
                        "quiet": "",
                        "disable-javascript": "",
                        "disable-external-links": "",
                        "disable-internal-links": "",
                        "disable-local-file-access": "",
                        "load-error-handling": "ignore",
                        "load-media-error-handling": "ignore",
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

        # ==========================================================
        # CASE 2: PDF URL EXISTS → DOWNLOAD PDF (PROXY LOOP)
        # ==========================================================
        response = None

        for ip, port in self.US_PROXIES:
            proxy = {
                "http": f"http://{ip}:{port}",
                "https": f"http://{ip}:{port}",
            }

            try:
                response = requests.get(
                    pdf_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) "
                            "Gecko/20100101 Firefox/136.0"
                        )
                    },
                    proxies=proxy,
                    timeout=120
                )

                print(f"Trying {ip}:{port} → {response.status_code}")

                if response.status_code == 200:
                    break

            except requests.RequestException as e:
                print(f"Proxy failed {ip}:{port} → {e}")
                continue

        if not response or response.status_code != 200:
            print("All proxies failed for PDF download")
            self.judgements_collection.update_one(
                {"_id": objectId},
                {"$set": {"processed": 2}}
            )
            return None

        with open(download_pdf_path, "wb") as f:
            f.write(response.content)

        self.judgements_collection.update_one(
            {"_id": objectId},
            {"$set": {"processed": 0}}
        )

        return download_pdf_path

    def _get_revision_status(self):
        return [case.get("revision_status", "") for case in self.cases]

    def get_court_name(self):
        return "Supreme Court of Oklahoma"

    def get_state_name(self):
        return "Oklahoma"

    def get_class_name(self):
        return "okla_sc_new"

    def get_court_type(self):
        return "state"
