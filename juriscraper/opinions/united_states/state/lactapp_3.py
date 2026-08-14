import os
from datetime import datetime
import json
import requests
import re
from lxml import html as lxml_html

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.method = "Post"
        self.url="https://www.la3circuit.org/Cases/Opinions.aspx"
        now = datetime.now()
        self.month_number = now.month
        self.month_year = now.year

    def _download(self):
        self.downloader_executed = True

        base_url = "https://www.la3circuit.org/"
        opinions_url = "https://www.la3circuit.org/Cases/Opinions.aspx"

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }

        session = requests.Session()
        session.headers.update(headers)

        base_response = session.get(
            base_url,
            proxies=self.proxies,
            timeout=60
        )

        if base_response.status_code != 200:
            raise Exception(
                f"Base URL failed with status {base_response.status_code}"
            )

        opinion_response = session.get(
            opinions_url,
            headers={
                "Referer": base_url
            },
            proxies=self.proxies,
            timeout=60
        )

        if opinion_response.status_code != 200:
            raise Exception(
                f"Opinion GET failed with status "
                f"{opinion_response.status_code}"
            )

        tree = lxml_html.fromstring(
            opinion_response.text
        )

        payload = {}

        for element in tree.xpath("//input[@type='hidden']"):
            name = element.get("name")

            if not name:
                continue

            payload[name] = element.get("value") or ""

        payload.update({
            "__EVENTTARGET": "ctl00$MainPlaceHolder$btnOpinionSearch",
            "__EVENTARGUMENT": "",
            "ctl00$txtSearch": "",
            "ctl00$MainPlaceHolder$txtSmartSearch": "",
            "ctl00$MainPlaceHolder$ddlSearchCaseYear": "",
            "ctl00$MainPlaceHolder$txtSearchCaseNumber": "",
            "ctl00$MainPlaceHolder$txtSearchTitle": "",
            "ctl00$MainPlaceHolder$ddlSearchMonth": self.month_number,
            "ctl00$MainPlaceHolder$ddlSearchYear": self.month_year,
            "ctl00$MainPlaceHolder$txtSearchDate": "",
            "ctl00$MainPlaceHolder$hfUsedAdvancedSearch": "true",
            "ctl00$MainPlaceHolder$hfActiveSearchMode": "Month"
        })

        post_response = session.post(
            opinions_url,
            headers={
                "Referer": opinions_url,
                "Origin": "https://www.la3circuit.org",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=payload,
            proxies=self.proxies,
            timeout=60
        )

        if post_response.status_code != 200:
            raise Exception(
                f"Opinion POST failed with status "
                f"{post_response.status_code}"
            )

        self.request["response"] = post_response
        text = self._clean_text(
            post_response.text
        )

        html_tree = self._make_html_tree(
            text
        )

        return html_tree

    def _process_html(self):
        rows = self.html.xpath(
            "//div[@id='MainPlaceHolder_divResultsContainer']"
            "//article[contains(@class,'opinion-row')]"
        )

        for row in rows:
            title_nodes = row.xpath(
                ".//a[contains(@class,'opinion-title')]"
            )

            if not title_nodes:
                continue

            title_node = title_nodes[0]

            docket = title_node.text_content().strip()
            url = (title_node.get("href") or "").strip()

            name_nodes = row.xpath(
                ".//div[contains(@class,'opinion-description')]"
            )

            name = (
                name_nodes[0].text_content().strip()
                if name_nodes
                else ""
            )

            status_nodes = row.xpath(
                ".//span[contains(@class,'opinion-badge')]"
            )

            status = (
                status_nodes[0].text_content().strip().rstrip(".")
                if status_nodes
                else ""
            )

            fields = {}

            for field in row.xpath(
                ".//div[contains(@class,'opinion-field')]"
            ):
                label_nodes = field.xpath(
                    ".//div[contains(@class,'opinion-label')]"
                )

                value_nodes = field.xpath(
                    ".//div[contains(@class,'opinion-value')]"
                )

                if not label_nodes or not value_nodes:
                    continue

                label = label_nodes[0].text_content().strip()
                value = value_nodes[0].text_content().strip()

                fields[label] = value

            case_number = fields.get(
                "Case Number",
                docket
            )

            parish = fields.get(
                "Parish",
                ""
            )

            trial_court = fields.get(
                "Trial Court",
                ""
            )

            date_str = fields.get(
                "Opinion Date",
                ""
            )

            if not date_str:
                continue

            try:
                parsed_date = datetime.strptime(
                    date_str,
                    "%m/%d/%Y"
                )

                date = parsed_date.strftime(
                    "%B %d, %Y"
                )

                comp_date = parsed_date.strftime(
                    "%d/%m/%Y"
                )

            except ValueError:
                print(
                    f"Invalid date format: {date_str}"
                )
                continue

            res = CasemineUtil.compare_date(
                self.crawled_till,
                comp_date
            )

            if res == 1:
                continue

            self.cases.append({
                "name": name,
                "date": date,
                "status": status,
                "url": url,
                "docket": [case_number]
            })

    def download_pdf(self, data, objectId):
        pdf_url = data.get("pdf_url")
        html_url = data.get("html_url")
        year = int(data.get("year"))
        court_name = data.get("court_name")
        court_type = data.get("court_type")

        if str(court_type) == "Federal":
            state_name = data.get("circuit")
        else:
            state_name = data.get("state")

        opinion_type = data.get("opinion_type")
        MAIN_PDF_PATH = "/synology/PDFs/US/juriscraper/"
        if str(opinion_type) == "Oral Argument":


            path = (
                MAIN_PDF_PATH
                + court_type
                + "/"
                + state_name
                + "/"
                + court_name
                + "/oral arguments/"
                + str(year)
            )
        else:
            path = (
                MAIN_PDF_PATH
                + court_type
                + "/"
                + state_name
                + "/"
                + court_name
                + "/"
                + str(year)
            )

        obj_id = str(objectId)
        download_pdf_path = os.path.join(
            path,
            f"{obj_id}.pdf"
        )

        if not pdf_url or pdf_url == "null":
            if not html_url or html_url == "null":
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
            else:
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )

            return download_pdf_path

        i = 0

        while True:
            try:
                os.makedirs(
                    path,
                    exist_ok=True
                )

                us_proxy = CasemineUtil.get_us_proxy()

                proxies = {
                    "http": f"http://{us_proxy.ip}:{us_proxy.port}",
                    "https": f"http://{us_proxy.ip}:{us_proxy.port}"
                }

                if "la3circuit.org/transmit.aspx" in pdf_url.lower():
                    headers = {
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br, zstd",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Connection": "keep-alive",
                        "Priority": "u=0, i",
                        "Referer": "https://www.la3circuit.org/",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "same-site",
                        "Sec-Fetch-User": "?1",
                        "TE": "trailers",
                        "Upgrade-Insecure-Requests": "1",
                        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
                    }
                else:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
                    }

                response = requests.get(
                    url=pdf_url.strip(),
                    headers=headers,
                    proxies=proxies,
                    timeout=120,
                    allow_redirects=True
                )

                response.raise_for_status()

                if not response.content:
                    raise requests.RequestException(
                        "Empty PDF response"
                    )

                if (
                    "la3circuit.org/transmit.aspx" in pdf_url.lower()
                    and not response.content.startswith(b"%PDF")
                ):
                    content_type = response.headers.get(
                        "Content-Type",
                        ""
                    )

                    print(
                        f"Louisiana Third Circuit returned "
                        f"non-PDF response. "
                        f"Content-Type: {content_type}"
                    )

                    raise requests.RequestException(
                        "Louisiana Third Circuit response is not a PDF"
                    )

                with open(download_pdf_path, "wb") as file:
                    file.write(response.content)

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )

                break

            except requests.RequestException as e:
                if "Unable to connect to proxy" in str(e):
                    i += 1

                    if i > 10:
                        self.judgements_collection.update_one(
                            {"_id": objectId},
                            {"$set": {"processed": 2}}
                        )
                        break

                    continue

                print(
                    f"Error while downloading the PDF: {e}"
                )

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )

                break

        return download_pdf_path

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        print("[INFO] Crawling from", start_date, "to", end_date)
        self.parse()
        return 0

    def get_class_name(self):
        return 'lactapp_3'

    def get_court_name(self):
        return 'Louisiana Court of Appeal'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Louisiana'
