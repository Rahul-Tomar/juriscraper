"""
Scraper for the Supreme Court of Tennessee
CourtID: tenn
Court Short Name: Tenn.
"""
from datetime import datetime
import requests
import os
from typing_extensions import override

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from juriscraper.lib.html_utils import fix_links_in_lxml_tree


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.docket_value = "-SC-"
        self.proxies = {
            'http': 'http://23.236.197.227:8800',
            'https': 'http://23.236.197.227:8800',
        }
        self.request["headers"]= {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cookie": "_ga_RTSNWWBCT9=GS2.1.s1789725088$o9$g1$t1789725101$j47$l0$h0; _ga=GA1.1.1711621671.1786614449; KEY=1186973*1432001:342930508:3198168651:1; _gid=GA1.2.547824138.1789714613",
            "Host": "www.tncourts.gov",
            "Priority": "u=0, i",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }

    def _process_html(self):
        import json
        import html
        from lxml import html as lxml_html

        response = self.request.get("response")

        if response is None:
            raise Exception("Tennessee response object not found")

        try:
            raw_text = response.text
        except Exception:
            raw_text = response.content.decode("utf-8", errors="ignore")

        raw_text = raw_text.strip()

        if raw_text.lower().startswith("<textarea"):
            tree = lxml_html.fromstring(raw_text)
            textarea_data = tree.xpath("//textarea/text()")

            if not textarea_data:
                raise Exception(
                    "Textarea found but Tennessee response is empty"
                )

            raw_text = textarea_data[0]

        raw_text = html.unescape(raw_text).strip()

        try:
            ajax_data = json.loads(raw_text)
        except Exception as e:
            raise Exception(
                f"Unable to parse Tennessee Drupal AJAX response: "
                f"{raw_text[:500]}"
            ) from e

        html_data = None

        for command in ajax_data:
            if not isinstance(command, dict):
                continue

            if command.get("command") != "insert":
                continue

            data = command.get("data") or ""

            if (
                "<table" in data
                and "views-field-field-opinions-date-filed" in data
            ):
                html_data = data
                break

        if not html_data:
            raise Exception(
                "Opinion table not found in Tennessee Drupal AJAX response"
            )

        text = self._clean_text(html_data)
        html_tree = self._make_html_tree(text)

        if hasattr(html_tree, "rewrite_links"):
            html_tree.rewrite_links(
                fix_links_in_lxml_tree,
                base_href=self.request["url"]
            )

        self.html = html_tree

        for row in self.html.xpath("//tbody/tr"):
            date_nodes = row.xpath(
                ".//td[contains(@class, "
                "'views-field-field-opinions-date-filed')]"
            )

            section_nodes = row.xpath(
                ".//td[contains(@class, "
                "'views-field-field-opinions-case-number')]"
            )

            if not date_nodes or not section_nodes:
                continue

            date = date_nodes[0].text_content().strip()

            lower_court_nodes = row.xpath(
                ".//td[contains(@class, "
                "'views-field-field-opinions-county')]"
            )

            lower_court = (
                lower_court_nodes[0].text_content().strip()
                if lower_court_nodes
                else ""
            )

            section = section_nodes[0]

            anchors = section.xpath(".//a")

            if not anchors:
                continue

            anchor = anchors[0]

            name = anchor.text_content().strip()
            url = anchor.get("href") or ""

            values = [
                value.strip()
                for value in section.text_content().split("\n")
                if value.strip()
            ]

            docket = []

            for value in values:
                if self.docket_value in value:
                    docket = [value]
                    break

            judge = []

            for value in values:
                if value.lower().startswith("authoring judge:"):
                    judge_text = value.split(":", 1)[1].strip()

                    if judge_text:
                        judge = [judge_text]

                    break

            summary_nodes = section.xpath(".//p/p")

            if summary_nodes:
                summary = " ".join(
                    node.text_content().strip()
                    for node in summary_nodes
                    if node.text_content().strip()
                )
            else:
                summary = values[-1] if values else ""

            if url and not url.startswith(("http://", "https://")):
                if not url.startswith("/"):
                    url = "/" + url

                url = "https://www.tncourts.gov" + url

            self.cases.append(
                {
                    "date": date,
                    "lower_court": lower_court,
                    "url": url,
                    "name": name,
                    "docket": docket,
                    "judge": judge,
                    "summary": summary,
                }
            )

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        start_date = start_date.date().strftime('%y-%m-%d')
        end_date = end_date.date().strftime('%y-%m-%d')
        page = 0
        flag = True
        while flag:
            # self.url = f"https://www.tncourts.gov/views/ajax?_wrapper_format=drupal_ajax&view_name=opinions_apache_solr&view_display_id=block_1&view_args=27&view_path=%2Fnode%2F7163679&view_base_path=opinions&view_dom_id=d6ce5aca4e1c2a6072082eb32e6628c871ad260ba2d444aa1e4aa562bf99698d&pager_element=0&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz7Ixjbnz5RIsy7QdqXNHCL-uymFCT6EhHvuecgKFgVhXAGz-waKAiNcHrB1QBEnT9YUEuHoyqn0PzsQFk8ata1qwqzE6LAsRpZUqYboMqY3nAtsFQ_P-wFeTN6aiKGKUzIz0--gmWYu_IlNvN6GXllTWCgYS77-1G8714hNfg&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz7Ixjbnz5RIsy7QdqXNHCL-uymFCT6EhHvuecgKFgVhXAGz-waKAiNcHrB1QBEnT9YUEuHoyqn0PzsQFk8ata1qwqzE6LAsRpZUqYboMqY3nAtsFQ_P-wFeTN6aiKGKUzIz0--gmWYu_IlNvN6GXllTWCgYS77-1G8714hNfg&field_opinions_county=All&field_opinions_authoring_judge=&field_opinions_originating_judge=&field_opinions_date_filed={start_date}&field_opinions_date_filed_1={end_date}&field_opinions_case_number=&title=&search_api_fulltext=&sort_by=field_opinions_date_filed&sort_order=DESC&page={page}&_drupal_ajax=1&ajax_page_state%5Btheme%5D=tncourts&ajax_page_state%5Btheme_token%5D=&ajax_page_state%5Blibraries%5D=eJx1j9FSxCAMRX8I4ZOYFGJLTQmSsHb9-o262q6jL3A59wwEEEGNpa6YlHtIIv51lPQSn8uO4uCxXr_bVe7ChKrYI-6NBbNBsqOEDIrNRMv_KTNW7EBuYlbRDi00bnzBfiLKTFraQWKDDrOFRcIPfDqgS0BYM9hP7sHrghu6mXkmjFCBrlqSPf8LuNPNuY8G5A_iR21joiILZidXUdzCBIJOcdfYUco7hlP2X5vTmqKNiLCVOlsCHRL-gp7K9GHz6GqzEU9AVl3JFHcp-Cbhc_Wwwv4ANs6D8Ab-uLWZ"
            # self.url = f"https://www.tncourts.gov/views/ajax?_wrapper_format=drupal_ajax&view_name=opinions_apache_solr&view_display_id=block_1&view_args=27&view_path=%2Fnode%2F7163679&view_base_path=opinions&view_dom_id=d6ce5aca4e1c2a6072082eb32e6628c871ad260ba2d444aa1e4aa562bf99698d&pager_element=0&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz7Ixjbnz5RIsy7QdqXNHCL-uymFCT6EhHvuecgKFgVhXAGz-waKAiNcHrB1QBEnT9YUEuHoyqn0PzsQFk8ata1qwqzE6LAsRpZUqYboMqY3nAtsFQ_P-wFeTN6aiKGKUzIz0--gmWYu_IlNvN6GXllTWCgYS77-1G8714hNfg&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz7Ixjbnz5RIsy7QdqXNHCL-uymFCT6EhHvuecgKFgVhXAGz-waKAiNcHrB1QBEnT9YUEuHoyqn0PzsQFk8ata1qwqzE6LAsRpZUqYboMqY3nAtsFQ_P-wFeTN6aiKGKUzIz0--gmWYu_IlNvN6GXllTWCgYS77-1G8714hNfg&field_opinions_county=All&field_opinions_authoring_judge=&field_opinions_originating_judge=&field_opinions_date_filed={start_date}&field_opinions_date_filed_1={end_date}&field_opinions_case_number=&title=&search_api_fulltext=&sort_by=field_opinions_date_filed&sort_order=DESC&page={page}&_drupal_ajax=1&ajax_page_state%5Btheme%5D=tncourts&ajax_page_state%5Btheme_token%5D=&ajax_page_state%5Blibraries%5D=eJx1j9FSxCAMRX8I4ZOYFGJLTQmSsHb9-o262q6jL3A59wwEEEGNpa6YlHtIIv51lPQSn8uO4uCxXr_bVe7ChKrYI-6NBbNBsqOEDIrNRMv_KTNW7EBuYlbRDi00bnzBfiLKTFraQWKDDrOFRcIPfDqgS0BYM9hP7sHrghu6mXkmjFCBrlqSPf8LuNPNuY8G5A_iR21joiILZidXUdzCBIJOcdfYUco7hlP2X5vTmqKNiLCVOlsCHRL-gp7K9GHz6GqzEU9AVl3JFHcp-Cbhc_Wwwv4ANs6D8Ab-uLWZ"
            self.url = (
                f"https://www.tncourts.gov/views/ajax?"
                f"_wrapper_format=drupal_ajax"
                f"&view_name=opinions_apache_solr"
                f"&view_display_id=block_1"
                f"&view_args=27"
                f"&view_path=%2Fnode%2F7163679"
                f"&view_base_path=opinions"
                f"&view_dom_id=d6ce5aca4e1c2a6072082eb32e6628c871ad260ba2d444aa1e4aa562bf99698d"
                f"&pager_element=0"
                f"&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz7Ixjbnz5RIsy7QdqXNHCL-uymFCT6EhHvuecgKFgVhXAGz-waKAiNcHrB1QBEnT9YUEuHoyqn0PzsQFk8ata1qwqzE6LAsRpZUqYboMqY3nAtsFQ_P-wFeTN6aiKGKUzIz0--gmWYu_IlNvN6GXllTWCgYS77-1G8714hNfg"
                f"&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz7Ixjbnz5RIsy7QdqXNHCL-uymFCT6EhHvuecgKFgVhXAGz-waKAiNcHrB1QBEnT9YUEuHoyqn0PzsQFk8ata1qwqzE6LAsRpZUqYboMqY3nAtsFQ_P-wFeTN6aiKGKUzIz0--gmWYu_IlNvN6GXllTWCgYS77-1G8714hNfg"
                f"&field_opinions_county=All"
                f"&field_opinions_authoring_judge="
                f"&field_opinions_originating_judge="
                f"&field_opinions_date_filed={start_date}"
                f"&field_opinions_date_filed_1={end_date}"
                f"&field_opinions_case_number="
                f"&title="
                f"&search_api_fulltext="
                f"&sort_by=field_opinions_date_filed"
                f"&sort_order=DESC"
                f"&page={page}"
                f"&_drupal_ajax=1"
                f"&ajax_page_state%5Btheme%5D=tncourts"
                f"&ajax_page_state%5Btheme_token%5D="
                f"&ajax_page_state%5Blibraries%5D=eJx1j9FSxCAMRX8I4ZOYFGJLTQmSsHb9-o262q6jL3A59wwEEEGNpa6YlHtIIv51lPQSn8uO4uCxXr_bVe7ChKrYI-6NBbNBsqOEDIrNRMv_KTNW7EBuYlbRDi00bnzBfiLKTFraQWKDDrOFRcIPfDqgS0BYM9hP7sHrghu6mXkmjFCBrlqSPf8LuNPNuY8G5A_iR21joiILZidXUdzCBIJOcdfYUco7hlP2X5vTmqKNiLCVOlsCHRL-gp7K9GHz6GqzEU9AVl3JFHcp-Cbhc_Wwwv4ANs6D8Ab-uLWZ"
            )
            self.parse()
            pageination = self.html.xpath(
                "//ul[@class='pagination js-pager__items']//li/a/span/text()")
            if 'Next page' in pageination:
                page = page + 1
            else:
                flag = False
            self.downloader_executed = False
        return 0

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
                    os.makedirs(path, exist_ok=True)
                    us_proxy = CasemineUtil.get_us_proxy()
                    response = requests.get(
                        url=pdf_url,
                        headers={
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Encoding": "gzip, deflate, br, zstd",
                            "Accept-Language": "en-US,en;q=0.5",
                            "Connection": "keep-alive",
                            "Cookie": "_ga_RTSNWWBCT9=GS2.1.s1789722285$o8$g1$t1789722340$j5$l0$h0; _ga=GA1.1.1711621671.1786614449; KEY=1178851*2255717:4087119392:1498650946:1; _gid=GA1.2.547824138.1789714613; _gat_gtag_UA_23086129_1=1",
                            "Host": "www.tncourts.gov",
                            "Priority": "u=0, i",
                            "Sec-Fetch-Dest": "document",
                            "Sec-Fetch-Mode": "navigate",
                            "Sec-Fetch-Site": "none",
                            "Sec-Fetch-User": "?1",
                            "Upgrade-Insecure-Requests": "1",
                            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
                        },
                        proxies={
                            "http": f"http://{us_proxy.ip}:{us_proxy.port}",
                            "https": f"http://{us_proxy.ip}:{us_proxy.port}"
                        },
                        timeout=120
                    )
                    response.raise_for_status()
                    with open(download_pdf_path, 'wb') as file:
                        file.write(response.content)
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

    def get_state_name(self):
        return "Tennessee"

    def get_court_type(self):
        return 'state'

    def get_court_name(self):
        return "Supreme Court of Tennessee"

    def get_class_name(self):
        return 'tenn'
