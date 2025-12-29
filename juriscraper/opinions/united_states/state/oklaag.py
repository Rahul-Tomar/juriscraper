# Scraper for Oklahoma Attorney General Opinions
# CourtID: oklaag
# Court Short Name: OK
# Author: Andrei Chelaru
# Reviewer: mlr
# Date: 2014-07-05

from datetime import datetime

import requests
from lxml import html, etree
import pdfkit
import os
from casemine.proxy_manager import ProxyManager
from juriscraper.opinions.united_states.state import okla
from sample_caller import logger
PDFKIT_CONFIG = pdfkit.configuration(
    wkhtmltopdf="/usr/bin/wkhtmltopdf"
)

class Site(okla.Site):
    # Inherit cleanup_content from Okla
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        year = datetime.today().year
        self.url = f"https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKAG&year={year}&level=1"
        # self.url="https://www.oscn.net/applications/oscn/Index.asp?ftdb=STOKAG&year=2025&level=1"
        self.status = "Published"
        self.expected_content_types = ["text/html"]
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

    def _process_html(self , start_date : datetime , end_date : datetime):

        proxy_manager = ProxyManager()
        proxy = proxy_manager.get_random_proxy()
        cite_html=""
        div=""

        if self.proxy_usage_count >= 4:
            self.proxies = {
                "http": f"http://{proxy[0]}:{proxy[1]}",
                "https": f"http://{proxy[0]}:{proxy[1]}",
            }
            logger.info(f"updated proxy is {self.proxies}")
            self.proxy_usage_count = 0
        for row in self.html.xpath("//div/p['@class=document']")[::-1]:
            if "OK" not in row.text_content() or "EMAIL" in row.text_content():
                continue
            docket, date, name = row.text_content().split(",", 2)
            docket = docket.replace("\xa0"," ")
            url = row.xpath(".//a/@href")[0]
            if not url.startswith("https"):
                url = "https://www.oscn.net/applications/oscn/"+url
            if datetime.strptime(date.strip(),
                                 "%m/%d/%Y") >= start_date and datetime.strptime(
                date.strip(), "%m/%d/%Y") <= end_date:
                try:
                    # print(f"hitting url : {url}")
                    response_html = requests.get(url,
                                                 headers=self.request["headers"],
                                                 proxies=self.proxies)

                    html_content = response_html.text
                    # print(html_content)
                    # print("__________________________________________")
                    # pdf_content = self.build_pdf_content(html_content)
                    # print(pdf_content)
                    tree = html.fromstring(html_content)
                    cite_text = tree.xpath("//div[@class='tmp-citationizer']")
                    cite_html = html.tostring(cite_text[0], pretty_print=True).decode(
                        "utf-8")
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

                            div = html.tostring(div_content[0],
                                                pretty_print=True).decode("utf-8")

                except Exception as e:
                    logger.info(f"inside the exception block .......{e}")


                self.cases.append(
                    {
                        "date": date,
                        "name": name,
                        "docket": [docket],
                        "url": "",
                        "citation": "",
                        "html_url": url,
                        "response_html": div,
                        "cite_info_html": cite_html,
                    }
                )

                # self.revision_status.append(0)
                self.proxy_usage_count +=1
                # print("------------------------------------------------------------------------")

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

    def get_court_name(self):
        return "Opinions of Atty. Gen."

    def get_class_name(self):
        return "oklaag"
