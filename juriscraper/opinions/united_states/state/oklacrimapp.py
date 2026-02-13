# Scraper for Oklahoma Court of Criminal Appeals
# CourtID: oklacrimapp
# Court Short Name: OK
# Author: Andrei Chelaru
# Reviewer: mlr
# Date: 2014-07-05
from datetime import datetime
import pdfkit
import os
from bs4 import BeautifulSoup

from juriscraper.opinions.united_states.state import okla, oklacivapp
import requests
from typing import Tuple, Optional, List

from lxml import html
from casemine.proxy_manager import ProxyManager
from sample_caller import logger
import time
import re

class Site(oklacivapp.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKCSCR&year=2026&level=1"
        # self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKCSCR&year=2025&level=1"

        self._CASE_META_PATTERN = re.compile(
            r'^(?P<docket>\d{4}\s+OK\s+CR\s+\d+),\s+'
            r'(?:(?P<citation>\d+\s+P\.3d\s+\d+),\s+)?'
            r'(?P<date>\d{2}/\d{2}/\d{4}),\s+'
            r'(?P<name>.+)$'
        )
        self.status="Published"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }

    def _download(self, request_dict={}):

        resp = None
        for ip, port in self.US_PROXIES:
            proxy = self.make_proxy(ip, port)

            try:
                resp = requests.get(
                    self.url,
                    headers=self.headers,
                    proxies=proxy,
                    timeout=30
                )

                print(f"Trying {ip}:{port} → {resp.status_code}")

                if resp.status_code == 200:
                    # print(resp.content)
                    self.html = html.fromstring(resp.content)
                    break

            except requests.RequestException as e:
                print(f"Proxy failed {ip}:{port} → {e}")
                continue

        if not resp or resp.status_code != 200:
            raise RuntimeError("All proxies exhausted, no 200 response")

    def _process_html(self, start_date : datetime , end_date : datetime):
        base_url = "https://www.oscn.net/dockets/"
        cite_html=""
        div=""
        summary=""
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
            citation, parallel_citation, date, name = self.extract_case_metadata(case_text)


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
            if datetime.strptime(date.strip(),
                                 "%m/%d/%Y") >= start_date and datetime.strptime(
                date.strip(), "%m/%d/%Y") <= end_date:
                # docket=docket.replace("\xa0"," ")
                print(f"date of the case is {date}")

                try:
                    print(f"getting result of docket {docket}")
                    print(f"hitting url {url} for html and cite html")
                    time.sleep(4)
                    if not url.startswith("https"):
                        url = "https://www.oscn.net/applications/oscn/" + url
                        print(url)
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
                            print(f"Trying {ip}:{port} → {response_html.status_code}")
                            if response_html.status_code == 200:
                                break

                        except requests.RequestException as e:
                            print(f"Proxy failed {ip}:{port} → {e}")
                            continue

                    soup = BeautifulSoup(response_html.text, "lxml")
                    container = soup.select_one("#tmp-style")
                    link = container.find("a", href=re.compile(
                        r"GetCaseInformation\.asp"))
                    docket = ''
                    pdf_page_url = ''
                    if link:
                        docket = link.get_text(strip=True)
                        full_url = "https://www.oscn.net/dockets/GetCaseInformation.aspx?db=Appellate&number="+docket

                    # 2️⃣ Fallback: extract from plain text
                    if not docket:
                        text = soup.get_text(" ", strip=True)
                        match = re.search(r"Case Number:\s*([A-Z0-9\-]+)",
                                          text)
                        if match:
                            docket = match.group(1)
                    if not docket:
                        docket=citation    # If docket is not present we will insert citation
                    html_content = response_html.text

                    tree = html.fromstring(html_content)
                    # print(html_content)
                    cite_text = tree.xpath("//div[@class='tmp-citationizer']")
                    cite_html = html.tostring(cite_text[0], pretty_print=True).decode("utf-8")
                    summary = tree.xpath("string(//div[@class='de-writing']/p)")
                    div_content = tree.xpath("//div[@class='container-fluid sized']")
                    if div_content:
                            tmp = div_content[0].xpath(
                                ".//div[@id='opinons-navigation']")
                            if tmp:
                                tmp[0].getparent().remove(
                                    tmp[0])

                            tmp_citationizer = div_content[0].xpath(
                                ".//div[@class='tmp-citationizer']")
                            if tmp_citationizer:
                                tmp_citationizer[0].getparent().remove(
                                    tmp_citationizer[0])

                            div = html.tostring(div_content[0],pretty_print=True).decode("utf-8")

                            anchor_text = tree.xpath("//div[@id='tmp-style']//a/text()")
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
                                            extracted_number = number_match.group(1)
                                            print(f"Extracted number: {extracted_number}")
                                            # full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + extracted_number
                                    print(f"getting the content for pdf from the url {full_url}")
                                    get_pdf_html = ""
                                    for ip, port in self.US_PROXIES:
                                        proxy = self.make_proxy(ip, port)
                                        get_pdf_html = requests.get(full_url, headers=self.headers, proxies=proxy)
                                        print(f"Trying {ip}:{port} → {get_pdf_html.status_code}")
                                        if get_pdf_html.status_code == 200:
                                            break
                                    if get_pdf_html.status_code != 200:
                                        raise Exception

                                    content = get_pdf_html.text
                                    # print(content)
                                    if "OSCN Turnstile" in content or "cf-turnstile" in content:
                                        print("captcha")
                                        content=self.fetch_oscn_page_with_proxy(full_url, proxy[0], proxy[1])


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
                                                url1 = tr.xpath(".//td[3]//div[@class='description-wrapper']//a[@class='doc-pdf']/@href")[0]
                                                if dt_str == date:
                                                    print(
                                                        f"Date matches for ORDR row. PDF URL: {url1}")
                                                    pdf_url = base_url + url1

                                    else:
                                        pdf_url = ""
                                    # print(f"got the pdf url {pdf_url}")
                    else:
                        logger.info("no div with calssname container-fluid sized present")
                except Exception as e:
                    logger.info(f"inside the exception block in okla class ..... {e}")
                # print("-------------------------------------------------------------------------------------------------------------------")
                cit_arr = []
                if citation is not None:
                    cit_arr.append(citation)
                if not pdf_url.startswith("https"):
                    pdf_url="https://www.oscn.net/applications/oscn/"+pdf_url
                if date:
                    date = datetime.strptime(date, "%m/%d/%Y").strftime("%d %b , %Y")
                self.cases.append(
                    {
                        "date": date,
                        "name": name,
                        "docket": [docket],
                        "status":self.status,
                        "citation": cit_arr,
                        "url": pdf_url,
                        "cite_info_html":cite_html,
                        "html_url":url,
                        "response_html":div,
                        "summary":summary
                    }
                )
                self.proxy_usage_count +=1
                break

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
            pdf_content = self.sanitize_opinion_html_for_pdf(response_html)
            # Convert HTML → PDF using response_html as-is (NO image logic)
            try:
                os.makedirs(path, exist_ok=True)

                html_data = response_html  # No modifications

                config = pdfkit.configuration(
                    wkhtmltopdf="/usr/bin/wkhtmltopdf")

                pdfkit.from_string(
                    pdf_content,
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

                response = None
                last_exception = None

                for ip, port in self.US_PROXIES:
                    proxy = {
                        "http": f"http://{ip}:{port}",
                        "https": f"http://{ip}:{port}",
                    }

                    try:
                        response = requests.get(
                            url=pdf_url,
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
                            break  # ✅ SUCCESS

                    except requests.RequestException as e:
                        print(f"Proxy failed {ip}:{port} → {e}")
                        last_exception = e
                        continue

                # ---- FINAL VALIDATION ----
                if not response or response.status_code != 200:
                    raise RuntimeError(
                        "All proxies exhausted, no 200 response for PDF download"
                    )

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

    def make_proxy(self,ip, port):
        proxy_url = f"http://{ip}:{port}"
        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def extract_case_metadata(self, text: str) -> Tuple[
        Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extracts docket, citation (optional), date, and case name from a citation line.
        Returns (docket, citation, date, name). Missing fields are None.
        """

        if not text:
            return None, None, None, None

        try:
            match = self._CASE_META_PATTERN.match(text.strip())
            if not match:
                return None, None, None, None

            docket = match.group("docket")
            citation = match.group("citation")  # None if absent
            date = match.group("date")
            name = match.group("name").strip()

            return docket, citation, date, name

        except Exception:
            # absolutely no crashes in crawl pipeline
            return None, None, None, None

    def get_court_name(self):
        return "Okla. Crim. App."

    def get_class_name(self):
        return "oklacrimapp"
