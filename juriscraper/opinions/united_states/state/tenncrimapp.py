"""
Scraper for the Tennessee Court of Criminal Appeals
CourtID: tennctcrimapp
Court Short Name: Tenn. Ct. Crim. App.
"""
from datetime import datetime

from juriscraper.opinions.united_states.state import tenn


class Site(tenn.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.request["headers"] = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cookie": "_ga_RTSNWWBCT9=GS2.1.s1764148111$o8$g0$t1764148111$j60$l0$h0; _ga=GA1.2.2060124310.1745220238; _gid=GA1.2.650419508.1764148112; _gat_gtag_UA_23086129_1=1",
            "Host": "www.tncourts.gov",
            "Referer": "https://www.tncourts.gov/courts/supreme-court/opinions",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "X-Requested-With": "XMLHttpRequest",
        }

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        start_date = start_date.date().strftime('%y-%m-%d')
        end_date = end_date.date().strftime('%y-%m-%d')
        page = 0
        flag = True
        while flag:
            self.url = f"https://www.tncourts.gov/views/ajax?_wrapper_format=drupal_ajax&view_name=opinions_apache_solr&view_display_id=block_1&view_args=29&view_path=%2Fnode%2F7163676&view_base_path=opinions&view_dom_id=af772c421a6b9335ec8b78c86a42cf12a6651ee37d7e4f6ce4205a97be8fbd80&pager_element=0&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz4Mt4H6MyXS2AXarrSZQ8R_X0phgg8h4Z57HrKDRUGYdsDsPoGiwAT9CEcHFHH2ZE0hEY6uXEr_swNh8aRR26omzEqMDstmZEuVaoguY3rBtcBW8TA-TrAweWsihirOyaxM35NmWrnwOzbx_hx6ZU1hoWAs-frT7fgB2KRNgA&viewsreference%5Bcompressed%5D=eJxdj9EKgzAMRf8lzz4Mt4H6MyXS2AXarrSZQ8R_X0phgg8h4Z57HrKDRUGYdsDsPoGiwAT9CEcHFHH2ZE0hEY6uXEr_swNh8aRR26omzEqMDstmZEuVaoguY3rBtcBW8TA-TrAweWsihirOyaxM35NmWrnwOzbx_hx6ZU1hoWAs-frT7fgB2KRNgA&field_opinions_county=All&field_opinions_authoring_judge=&field_opinions_originating_judge=&field_opinions_date_filed={start_date}&field_opinions_date_filed_1={end_date}&field_opinions_case_number=&title=&search_api_fulltext=&sort_by=field_opinions_date_filed&sort_order=DESC&page={page}&_drupal_ajax=1&ajax_page_state%5Btheme%5D=tncourts&ajax_page_state%5Btheme_token%5D=&ajax_page_state%5Blibraries%5D=eJx1j9FSxCAMRX8I4ZOYFGJLTQmSsHb9-o262q6jL3A59wwEEEGNpa6YlHtIIv51lPQSn8uO4uCxXr_bVe7ChKrYI-6NBbNBsqOEDIrNRMv_KTNW7EBuYlbRDi00bnzBfiLKTFraQWKDDrOFRcIPfDqgS0BYM9hP7sHrghu6mXkmjFCBrlqSPf8LuNPNuY8G5A_iR21joiILZidXUdzCBIJOcdfYUco7hlP2X5vTmqKNiLCVOlsCHRL-gp7K9GHz6GqzEU9AVl3JFHcp-Cbhc_Wwwv4ANs6D8Ab-uLWZ"
            self.parse()
            pageination = self.html.xpath(
                "//ul[@class='pagination js-pager__items']//li/a/span/text()")
            if 'Next page' in pageination:
                page = page + 1
            else:
                flag = False
            self.downloader_executed = False
        return 0

    def get_court_name(self):
        return "Tennessee Court of Criminal Appeals"

    def get_class_name(self):
        return 'tenncrimapp'
