from datetime import datetime

import requests
from lxml import html as lxml_html
from urllib.parse import urljoin

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.court_id = self.__module__
        self.method = "Post"
        self.url = "https://www.la4th.org/Search.aspx"

        now = datetime.now()

        self.search_month = now.strftime("%B")
        self.search_year = str(now.year)

    def _download(self):
        self.downloader_executed = True

        search_url = "https://www.la4th.org/Search.aspx"

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Priority": "u=0, i",
            "Referer": search_url,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }

        session = requests.Session()

        get_response = session.get(
            search_url,
            headers=headers,
            proxies=self.proxies,
            timeout=60
        )

        if get_response.status_code != 200:
            raise Exception(
                f"Louisiana Fourth Circuit GET failed with status "
                f"{get_response.status_code}"
            )

        tree = lxml_html.fromstring(
            get_response.text
        )

        form_nodes = tree.xpath("//form")

        if not form_nodes:
            raise Exception(
                "Louisiana Fourth Circuit form not found"
            )

        form = form_nodes[0]

        payload = {}

        for element in form.xpath(".//input[@name]"):
            name = element.get("name")

            if not name:
                continue

            input_type = (
                element.get("type") or "text"
            ).lower()

            if input_type in (
                "submit",
                "button",
                "image",
                "reset",
                "file"
            ):
                continue

            if input_type in (
                "checkbox",
                "radio"
            ):
                if element.get("checked") is None:
                    continue

            payload[name] = (
                element.get("value") or ""
            )

        for element in form.xpath(
            ".//textarea[@name]"
        ):
            name = element.get("name")

            if not name:
                continue

            payload[name] = (
                element.text or ""
            )

        for element in form.xpath(
            ".//select[@name]"
        ):
            name = element.get("name")

            if not name:
                continue

            selected = element.xpath(
                ".//option[@selected]"
            )

            if not selected:
                selected = element.xpath(
                    ".//option[1]"
                )

            if selected:
                payload[name] = (
                    selected[0].get("value")
                    or ""
                )

        payload.update({
            "__EVENTTARGET": "ctl00$Main$btnOpMonthYearSearch",
            "__EVENTARGUMENT": "",
            "ctl00$Main$ddlOpMonth": self.search_month,
            "ctl00$Main$ddlOpYear": self.search_year
        })

        post_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.la4th.org",
            "Priority": "u=0, i",
            "Referer": search_url,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
        }

        post_response = session.post(
            search_url,
            headers=post_headers,
            data=payload,
            proxies=self.proxies,
            timeout=60
        )

        if post_response.status_code != 200:
            raise Exception(
                f"Louisiana Fourth Circuit POST failed with status "
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
            "//div[contains("
            "concat(' ', normalize-space(@class), ' '), "
            "' opinion-result ')]"
        )

        for row in rows:

            docket_nodes = row.xpath(
                "./p[1]/strong"
            )

            docket = (
                docket_nodes[0].text_content().strip()
                if docket_nodes
                else ""
            )

            if not docket:
                continue

            name = ""

            parties_nodes = row.xpath(
                "./p[strong[normalize-space()='Parties:']]"
            )

            if parties_nodes:
                text_parts = parties_nodes[0].xpath(
                    ".//text()["
                    "not(ancestor::strong) "
                    "and not(ancestor::span[contains("
                    "concat(' ', normalize-space(@class), ' '), "
                    "' sr-only ')])"
                    "]"
                )

                name = " ".join(
                    " ".join(text_parts).split()
                )

            disposition = ""

            decree_nodes = row.xpath(
                "./p[strong[normalize-space()='Decree:']]"
            )

            if decree_nodes:
                decree_text = " ".join(
                    decree_nodes[0]
                    .text_content()
                    .split()
                )

                disposition = decree_text.replace(
                    "Decree:",
                    "",
                    1
                ).strip()

            date_str = ""

            date_nodes = row.xpath(
                "./p[strong[normalize-space()='Opinion Date:']]"
            )

            if date_nodes:
                date_text = " ".join(
                    date_nodes[0]
                    .text_content()
                    .split()
                )

                date_str = date_text.replace(
                    "Opinion Date:",
                    "",
                    1
                ).strip()

            if not date_str:
                continue

            pdf_nodes = row.xpath(
                "./p[strong[normalize-space()='Document:']]"
                "//a/@href"
            )

            url = (
                pdf_nodes[0].strip()
                if pdf_nodes
                else ""
            )

            if url:
                url = urljoin(
                    "https://www.la4th.org/",
                    url
                )

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

            if res >= 0:
                continue

            self.cases.append({
                "name": name,
                "date": date,
                "docket": [docket],
                "url": url,
                "disposition": disposition,
                "status":"Published"
            })

    def crawling_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> int:

        print(
            "[INFO] Crawling from",
            start_date,
            "to",
            end_date
        )

        self.parse()

        return 0

    def get_class_name(self):
        return "lactapp_4"

    def get_court_name(self):
        return "Louisiana Court of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Louisiana"
