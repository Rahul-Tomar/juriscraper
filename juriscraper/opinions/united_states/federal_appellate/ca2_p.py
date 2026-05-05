"""Scraper for Second Circuit
CourtID: ca2
Contact:
  Webmaster@ca2.uscourts.gov ('Calendar Team' handles updates, and is responsive)
  ecfhelpdesk@ca2.uscourts.gov
  Shane_Clouden@ca2.uscourts.gov
"""

import time
from datetime import date, timedelta, datetime

from bs4 import BeautifulSoup
from dateutil.rrule import DAILY, rrule
from lxml.etree import tostring
import requests
from typing_extensions import override

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSite import OpinionSite
from juriscraper.lib.string_utils import titlecase


class Site(OpinionSite):
    dates = []
    names = []
    statuses = []
    urls = []
    dockets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval = 30
        self.court_id = self.__module__
        # self.proxies = {
        #     "http": "http://192.126.184.28:8800", "https": "http://192.126.184.28:8800"}
        self.data=None
        self.back_scrape_iterable = [i.date() for i in
            rrule(DAILY, interval=self.interval, dtstart=date(2007, 1, 1),
                until=date(2015, 1, 1), )]

    def _get_case_names(self):
        return self.names

    def _get_download_urls(self):
        return self.urls

    def _get_case_dates(self):
        return self.dates

    def _get_docket_numbers(self):
        return self.dockets

    def _get_precedential_statuses(self):
        return self.statuses

    def _download_backwards(self, d):
        self.url = "http://www.ca2.uscourts.gov/decisions?IW_DATABASE=OPN&IW_FIELD_TEXT=*&IW_SORT=-Date&IW_BATCHSIZE=100&IW_FILTER_DATE_BEFORE={before}&IW_FILTER_DATE_After={after}".format(
            before=(d + timedelta(self.interval)).strftime("%Y%m%d"),
            after=d.strftime("%Y%m%d"), )
        self.html = self._download()
        if self.html is not None:
            # Setting status is important because it prevents the download
            # function from being run a second time by the parse method.
            self.status = 200

    @override
    def _request_url_post(self, url):
        headers = {
            "Host": "ww3.ca2.uscourts.gov", "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate, br, zstd", "Connection": "keep-alive", "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Content-Type": "application/x-www-form-urlencoded", "Priority": "u=0, i", "Pragma": "no-cache", "Cache-Control": "no-cache"}
        self.request['response'] = requests.post(
            url=url,
            headers=headers,
            proxies=self.proxies,
            data=self.parameters if self.parameters else self.data
        )
        # print(resp.status_code)
        # print(resp.text)

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.url="https://ww3.ca2.uscourts.gov/dtSearch/dtisapi6.dll"
        self.method='POST'
        # Parse the date string into a datetime object
        start_date1 = start_date.strftime('%Y/%m/%d')
        end_date1 = end_date.strftime('%Y/%m/%d')
        sdate = start_date1.split('/')
        edate = end_date1.split('/')
        self.parameters = {
            "index": "*{aa12e167958cdbcaa709fa14b9161a4a} OPN",
            "rctopin": "",
            "StartDate": f"{sdate[0]}-{sdate[1]}-{sdate[2]}",
            "EndDate": f"{edate[0]}-{edate[1]}-{edate[2]}",
            "request": "*",
            "searchType": "allwords",
            "cmd": "search",
            "SearchForm": "%%SearchForm%%",
            "dtsPdfWh": "*",
            "OrigSearchForm": "/decisions.html",
            "autoStopLimit": "5000",
            "pageSize": "25",
            "sort": "date",
            "fileConditions": f'xfilter(date "{sdate[0]}/{sdate[1]}/{sdate[2]}~~{edate[0]}/{edate[1]}/{edate[2]}")',
            "booleanConditions": ""
        }
        self.data = (
            f"index=*%7Baa12e167958cdbcaa709fa14b9161a4a%7D+OPN"
            f"&rctopin="
            f"&StartDate={sdate[0]}-{sdate[1]}-{sdate[2]}"
            f"&EndDate={edate[0]}-{edate[1]}-{edate[2]}"
            f"&request=*"
            f"&searchType=allwords"
            f"&cmd=search"
            f"&SearchForm=%25%25SearchForm%25%25"
            f"&dtsPdfWh=*"
            f"&OrigSearchForm=%2Fdecisions.html"
            f"&autoStopLimit=5000"
            f"&pageSize=25"
            f"&sort=date"
            f"&fileConditions=xfilter%28date+%22{sdate[0]}%2F{sdate[1]}%2F{sdate[2]}~~{edate[0]}%2F{edate[1]}%2F{edate[2]}%22%29"
            f"&booleanConditions="
        )
        self.parse()
        return 0

    def pagination(self):
        data = tostring(self.html).decode('utf-8')
        soup = BeautifulSoup(data, 'html.parser')

        # ---- Extract pagination info ----
        header = soup.find('p', class_='NextPrevLinks')
        if not header:
            return None

        import re
        match = re.search(r'Results\s+(\d+)\s*-\s*(\d+)\s+of\s+(\d+)',
                          header.text)
        if not match:
            return None

        first = int(match.group(1))
        last = int(match.group(2))
        total = int(match.group(3))

        # ---- 🔴 DECISION POINT ----
        if last >= total:
            return None  # ✅ NO MORE PAGES

        # ---- MULTIPLE PAGES EXIST ----
        form = soup.find('form', {'name': 'NextPageForm'})
        if not form:
            return None

        inputs = form.find_all('input')
        form_data = {}

        for inp in inputs:
            name = inp.get('name')
            value = inp.get('value', '')
            if name:
                form_data[name] = value

        # ---- Compute next page ----
        current_start = int(form_data.get('startAt', 0))
        page_size = int(form_data.get('pageSize', 25))

        next_start = current_start + page_size

        # ---- Safety check ----
        if next_start >= total:
            return None

        form_data['startAt'] = str(next_start)

        # ---- Update scraper state ----
        self.method = 'POST'
        self.url = form.get(
            'action') or "https://ww3.ca2.uscourts.gov/dtSearch/dtisapi6.dll"
        self.parameters = form_data

        return self.url

    def parse(self):
        if not self.downloader_executed:
            # Run the downloader if it hasn't been run already
            flag = True
            while flag:
                self.html = self._download()
                next_page_link = self.pagination()
                if next_page_link is None:
                    flag = False
                else:
                    self.method = 'POST'
                    self.url = next_page_link

                # Parse rows properly
                rows = self.html.xpath('//table[@class="ResultsTable"]/tr')

                for row in rows:
                    # ---- DOCKET ----
                    docket = row.xpath(
                        './/td[@class="ResultsItemLeft"]//a/text()')
                    if docket:
                        self.dockets.append([docket[0].strip()])
                    else:
                        self.dockets.append([])

                    # ---- URL ----
                    url = row.xpath('.//td[@class="ResultsItemLeft"]//a/@href')
                    if url:
                        link = url[0]
                        if not link.startswith("http"):
                            link = "https://ww3.ca2.uscourts.gov/" + link
                        self.urls.append(link)
                    else:
                        self.urls.append(None)

                    # ---- CASE NAME ----
                    name = row.xpath(
                        './/td[@class="ResultsItemRight"]//a/text()')
                    if name:
                        self.names.append(titlecase(name[0].strip()))
                    else:
                        self.names.append("")

                    # ---- DATE ----
                    date_texts = row.xpath(
                        './/td[@class="ResultsItemRight"]/text()')

                    extracted_date = None
                    for txt in date_texts:
                        txt = txt.strip()
                        if "/" in txt:
                            extracted_date = txt
                            break

                    if extracted_date:
                        try:
                            date_filed = datetime.strptime(extracted_date,
                                                           "%m/%d/%Y").date()
                            self.dates.append(date_filed)

                            date_obj = date_filed.strftime('%d/%m/%Y')
                            res = CasemineUtil.compare_date(self.crawled_till,
                                                            date_obj)
                            if res == 1:
                                self.crawled_till = date_obj
                                flag = False
                        except:
                            self.dates.append(None)
                    else:
                        self.dates.append(None)

                    # ---- STATUS ----
                    type_text = row.xpath(
                        './/td[@class="ResultsItemRight"]/text()')

                    status_val = "Unknown"
                    for t in type_text:
                        t = t.lower()
                        if "opn" in t:
                            status_val = "Published"
                            break
                        elif "sum" in t:
                            status_val = "Unpublished"
                            break

                    self.statuses.append(status_val)
                # Process the available html (optional)

        # Set the attribute to the return value from _get_foo()
        # e.g., this does self.case_names = _get_case_names()
        for attr in self._all_attrs:
            self.__setattr__(attr, getattr(self, f"_get_{attr}")())

        self._clean_attributes()
        if "case_name_shorts" in self._all_attrs:
            # This needs to be done *after* _clean_attributes() has been run.
            # The current architecture means this gets run twice. Once when we
            # iterate over _all_attrs, and again here. It's pretty cheap though.
            self.case_name_shorts = self._get_case_name_shorts()
        self._post_parse()
        self._check_sanity()
        self._date_sort()
        self._make_hash()
        return self

    def _process_html(self):
        next_page_url = self.pagination()
        self.request["url"] = next_page_url
        self.request["response"] = self.request["session"].get(next_page_url,
            headers=self.request["headers"], verify=self.request["verify"],
            proxies=self.proxies, timeout=60, **self.request["parameters"])
        self._post_process_response()
        self.html = self._return_response_text_object()

    def get_class_name(self):
        return 'ca2_p'

    def get_court_name(self):
        return 'Court of Appeals for the Second Circuit'

    def get_court_type(self):
        return 'Federal'

    def get_state_name(self):
        return "2d Circuit"
