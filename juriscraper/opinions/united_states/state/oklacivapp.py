# Scraper for Oklahoma Court of Civil Appeals
# CourtID: oklacivapp
# Court Short Name: OK
# Author: Andrei Chelaru
# Reviewer: mlr
# Date: 2014-07-05
from datetime import datetime
import re
from typing import Tuple, Optional, List
from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.state import okla
import re
import os
import requests
from lxml import html
import pdfkit
from casemine.proxy_manager import ProxyManager
from sample_caller import logger
PDFKIT_CONFIG = pdfkit.configuration(
    wkhtmltopdf="/usr/bin/wkhtmltopdf"
)

import time

class Site(okla.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKCSCV&year={self.year}&level=1"
        # self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKCSCV&year=2025&level=1"
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
        ]
        self._opt_attrs = self._opt_attrs + ["cite_info_html"]
        self.valid_keys.update({
            "cite_info_html"
        })
        self._all_attrs = self._req_attrs + self._opt_attrs

        for attr in self._all_attrs:
            self.__setattr__(attr, None)

        self._CASE_META_PATTERN = re.compile(
            r'^(?P<docket>\d{4}\s+OK\s+CIV\s+APP\s+\d+),\s+'
            r'(?:(?P<citation>\d+\s+P\.3d\s+\d+),\s+)?'
            r'(?P<date>\d{2}/\d{2}/\d{4}),\s+'
            r'(?P<name>.+)$'
        )

    def _extract_opinion_sections(self, tree) -> str:
        # Start after the tmp-style block
        nodes = tree.xpath(
            "//*[@id='tmp-style']/following-sibling::*"
        )

        if not nodes:
            raise ValueError("Opinion body not found (tmp-style missing)")

        html_blocks = []

        for node in nodes:
            text = node.text_content().strip()

            if not text:
                continue

            # Stop before citationizer
            if "Citationizer" in text:
                break

            upper = text.upper()

            # Section headers
            if upper in {"SUMMARY", "BACKGROUND", "DISCUSSION", "FOOTNOTES"}:
                html_blocks.append(f"<div class='section'>{upper}</div>")
                continue

            # Paragraph numbering
            if text.startswith("¶"):
                para, _, rest = text.partition(" ")
                html_blocks.append(
                    f"<p><span class='para-num'>{para}</span> {rest}</p>"
                )
            else:
                html_blocks.append(f"<p>{text}</p>")

        return "\n".join(html_blocks)

    def _process_html(self, start_date : datetime , end_date : datetime):
        base_url = "https://www.oscn.net/dockets/"
        cite_html=""
        div=""

        for row in self.html.xpath(".//p[@id='document']"):
            pdf_url = ""
            # proxy_manager = ProxyManager()
            # proxy = proxy_manager.get_random_proxy()
            proxy=CasemineUtil.get_us_proxy()

            if self.proxy_usage_count >= 4:
                self.proxies = {
                    "http": f"http://{proxy.ip}:{proxy.port}",
                    "https": f"http://{proxy.ip}:{proxy.port}",
                }
                logger.info(f"updated proxy is {self.proxies}")
                self.proxy_usage_count = 0

            text = row.xpath(".//a/text()")
            # print(text)
            url = row.xpath(".//a/@href")[0]
            case = text[0]
            parts = case.split(", ")
            case_text = text[0].strip()
            docket,citation,date,name=self.extract_case_metadata(case_text)
            # if len(parts)==4:
            #     docket, citation, date, name = parts
            #     citation = citation.replace("\xa0"," ")
            #
            # elif len(parts)==3:
            #     docket, date, name = parts
            #
            # docket=docket.replace("\xa0"," ")

            if datetime.strptime(date.strip(),
                                 "%m/%d/%Y") >= start_date and datetime.strptime(
                date.strip(), "%m/%d/%Y") <= end_date:
                try:
                    print(f"getting result of docket {docket}")
                    if not url.startswith("https"):
                        url="https://www.oscn.net/applications/oscn/"+url
                    print(f"hitting url {url} for html and cite html")
                    time.sleep(4)
                    prox = {
                        'http': 'http://156.241.224.100:8800',
                        'https': 'http://156.241.224.100:8800',
                    }
                    response_html = requests.get(url,
                                                 headers=self.request["headers"],
                                                 proxies=prox)
                    if response_html.status_code == 201:
                        raise Exception(
                            f"========= HTTP {response_html.status_code} while fetching URL: {url} ========"
                        )
                    if response_html.status_code != 200:
                        raise Exception(
                            f"HTTP {response_html.status_code} while fetching URL: {url}"
                        )

                    html_content = response_html.text

                    tree = html.fromstring(html_content)

                    cite_text = tree.xpath("//div[@class='tmp-citationizer']")
                    cite_html = html.tostring(cite_text[0], pretty_print=True).decode("utf-8")
                    div_content = tree.xpath(
                        "//div[@class='container-fluid sized']")
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
                                    full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + case_number
                                    if "; " in case_number:
                                        match = re.search(r'^(\d+);', case_number)
                                        if match:
                                            number = match.group(1)
                                            full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + number


                                    if "SCBD" in case_number:
                                        number_match = re.search(r"SCBD-(\d+)",
                                                                 case_number)
                                        if number_match:
                                            extracted_number = number_match.group(1)
                                            print(f"Extracted number: {extracted_number}")
                                            full_url = base_url + "GetCaseInformation.aspx?db=Appellate&number=" + extracted_number
                                    print(f"getting the content for pdf from the url {full_url}")
                                    get_pdf_html = requests.get(full_url, headers=
                                    self.request["headers"], proxies=self.proxies)
                                    content = get_pdf_html.text
                                    if "OSCN Turnstile" in content or "cf-turnstile" in content:
                                        # print("captcha")
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
                                            if td[0] == 'COPN':
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
                    raise
                # print("-------------------------------------------------------------------------------------------------------------------")

            cit_arr = []
            if citation is not None:
                cit_arr.append(citation)

            print(docket,citation,date,name)
            self.cases.append(
                {
                    "date": date,
                    "name": name,
                    "docket": [docket],
                    "citation": cit_arr,
                    "url": pdf_url,
                    "cite_info_html":cite_html,
                    "html_url":url,
                    "response_html":div,
                }
            )
            self.proxy_usage_count +=1

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

        # --------------------------------------------------
        # Build directory path (UNCHANGED LOGIC)
        # --------------------------------------------------
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

        # --------------------------------------------------
        # CASE 1: NO PDF URL → TRY HTML → PDF
        # --------------------------------------------------
        if not pdf_url or str(pdf_url).strip() in ["", "null"]:
            if not html_url or str(html_url).strip() in ["", "null"]:
                # No pdf + no html → mark failed
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
                return None

            try:
                os.makedirs(path, exist_ok=True)

                if not response_html:
                    raise Exception("Empty response_html")
                pdf_content = self.build_pdf_content(response_html)
                pdfkit.from_string(
                    pdf_content,
                    download_pdf_path,
                    configuration=PDFKIT_CONFIG,
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

        # --------------------------------------------------
        # CASE 2: VALID PDF URL → DOWNLOAD PDF
        # --------------------------------------------------
        i = 0
        while True:
            try:
                os.makedirs(path, exist_ok=True)

                response = requests.get(
                    url=pdf_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) "
                            "Gecko/20100101 Firefox/136.0"
                        )
                    },
                    proxies={
                        "http": "http://156.241.224.100:8800",
                        "https": "http://156.241.224.100:8800"
                    },
                    timeout=120
                )

                response.raise_for_status()

                with open(download_pdf_path, "wb") as file:
                    file.write(response.content)

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )
                break

            except requests.RequestException as e:
                # Retry only for proxy failures (UNCHANGED LOGIC)
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

    def build_pdf_content(self, raw_html: str) -> str:
        tree = html.fromstring(raw_html)

        title = tree.xpath("//title/text()")
        title = title[0].strip() if title else "Attorney General Opinion"

        sections_html = self._extract_opinion_sections(tree)

        return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: "Times New Roman", serif;
                font-size: 12pt;
                line-height: 1.6;
                margin: 1in;
            }}
            .title {{
                text-align: center;
                font-weight: bold;
                font-size: 16pt;
                margin-bottom: 20px;
            }}
            .section {{
                text-align: center;
                font-weight: bold;
                margin-top: 30px;
                margin-bottom: 10px;
            }}
            p {{
                text-align: justify;
                margin: 0 0 12px 0;
            }}
            .para-num {{
                font-weight: bold;
            }}
            hr {{
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>

    <div class="title">{title}</div>

    {sections_html}

    </body>
    </html>
    """

    def get_court_name(self):
        return "Okla. Civ. App."

    def get_class_name(self):
        return "oklacivapp"
