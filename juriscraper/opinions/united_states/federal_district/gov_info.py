import os
import re
from datetime import datetime
from typing import Dict, Any

import requests
from stem import Signal
from stem.control import Controller
from typing_extensions import override

from casemine.casemine_util import CasemineUtil
from casemine.constants import MAIN_PDF_PATH
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from juriscraper.lib.html_utils import set_response_encoding

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = "https://www.govinfo.gov/wssearch/search"
        self.court_id = self.__module__
        self.court_name = None
        self.json = {}
        # Initialize the TorProxyGenerator
        self.max_retry_attempts = 10  # Maximum number of proxy retries

    def renew_tor_ip(self):
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()  # Uses default cookie-based auth
            controller.signal(Signal.NEWNYM)
            print("[TOR] Sent NEWNYM signal to rotate IP")

    def _download(self, request_dict={}):
        """Download the latest version of Site with proxy retry mechanism"""
        retry_count = 0
        while retry_count < self.max_retry_attempts:
            try:
                # Get a new proxy from TorProxyGenerator
                # proxy = self.proxy_generator.get_proxy()
                self.proxies={
                    'http': 'socks5h://127.0.0.1:9050',
                    'https': 'socks5h://127.0.0.1:9050',
                }
                # us_proxy=CasemineUtil.get_us_proxy()
                # # Setting in proxies header
                # self.proxies = {
                #     'http': f"http://{us_proxy.ip}:{us_proxy.port}", 'https': f"http://{us_proxy.ip}:{us_proxy.port}"
                # }

                # Make the request
                # self._request_url_post(self.url)
                headers={
                    'Host': 'www.govinfo.gov',
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/json',
                }

                self.request["response"] = requests.post(url=self.url,headers=headers,data=self.parameters,proxies=self.proxies,timeout=60)

                # Process the response (will raise exception if status code is not successful)
                self._post_process_response()

                # If we reach here, request was successful
                return self._return_response_text_object()

            except Exception as ex:
                retry_count += 1
                error_message = str(ex)
                # Check if it's a proxy-related error
                if "Unable to connect to proxy" in error_message or "Forbidden for url" in error_message or "timed out" in error_message or "Connection refused" in error_message:
                    print(f"Attempt {retry_count}/{self.max_retry_attempts}: {error_message} - trying with new proxy")
                    self.renew_tor_ip()
                    continue
                else:
                    # If it's not a proxy-related error, re-raise the exception
                    raise ex

        # If we've exhausted all retry attempts
        raise Exception(f"Failed to connect after {self.max_retry_attempts} proxy attempts")

    @override
    def _request_url_post(self, url):
        """Execute POST request and assign appropriate request dictionary values"""
        self.request["response"] = requests.post(
            url=url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
            },
            verify=self.request["verify"],
            data=self.parameters,
            proxies=self.proxies,
            timeout=60,
            # **self.request["parameters"],
        )

    @override
    def _post_process_response(self):
        """Cleanup to response object"""
        self.tweak_response_object()
        self.request["response"].raise_for_status()
        # Check the status code explicitly
        if self.request["response"].status_code != 200:
            raise Exception(f"Request failed with status code: {self.request['response'].status_code}")
        set_response_encoding(self.request["response"])

    def _process_html(self) -> None:
        self.json = self.html
        if list(self.json["resultSet"]).__len__() == 0:
            return
        for row in self.json["resultSet"]:
            package_id = row["fieldMap"]["packageid"]
            docket = row["line1"].split()[0]
            date_arr = str(row['line2']).split(".")

            date_finder = date_arr[-1]
            if date_finder.__eq__(""):
                date_finder = date_arr[-2]

            date_str = date_finder.split("day, ")[1].strip(".")
            curr_date = datetime.strptime(date_str, "%B %d, %Y").strftime("%d/%m/%Y")
            res = CasemineUtil.compare_date(self.crawled_till, curr_date)
            if res == 1:
                return
            teaser = ''
            if dict(row["fieldMap"]).keys().__contains__("teaser"):
                teaser = row["fieldMap"]["teaser"]
            # print(teaser)
            # url = f"https://www.govinfo.gov/content/pkg/{package_id}/pdf/{package_id}-0.pdf"
            title = ''
            if dict(row["fieldMap"]).keys().__contains__("title"):
                title = row["fieldMap"]["title"]

            if title.__eq__(''):
                title = str(row["line2"]).split(".")[2]
            # print(title)
            self.cases.append({
                "docket": [docket], "name": title, "url": row["fieldMap"]["url"], "date": date_str, "summary": row["line2"], "status": "Unknown", "teaser": teaser})

    def extract_from_text(self, scraped_text: str) -> Dict[str, Any]:
        """Pass scraped text into function and return precedential status

        :param scraped_text: Text of scraped content
        :return: metadata
        """
        if re.findall(r"\bPUBLISHED\b", scraped_text):
            status = "Published"
        elif re.findall(r"\bUNPUBLISHED\b", scraped_text):
            status = "Unpublished"
        else:
            status = "Unknown"
        metadata = {"OpinionCluster": {"precedential_status": status, }, }
        return metadata

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.method = "POST"
        self.request["headers"] = {
            'Host': 'www.govinfo.gov', 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'Connection': 'keep-alive', 'Content-Type': 'application/json', }
        flag = True
        page = 0
        while flag:
            self.parameters = '{"historical":false,"offset":' + str(page) + ',"query":"publishdate:range(' + start_date.strftime("%Y-%m-%d") + ',' + end_date.strftime("%Y-%m-%d") + ')","facetToExpand":"governmentauthornav","facets":{"accodenav":["USCOURTS"],"governmentauthornav":["' + self.court_name + '"]},"filterOrder":["accodenav","governmentauthornav"],"sortBy":"2","pageSize":100}'
            self.parse()
            if list(self.json["resultSet"]).__len__() == 0:
                flag = False
            page += 1
        return 0

    @override
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
            path = MAIN_PDF_PATH + court_type + "/" + state_name + "/" + court_name + "/" + "oral arguments/" + str(year)
        else:
            path = MAIN_PDF_PATH + court_type + "/" + state_name + "/" + court_name + "/" + str(year)

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
                            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
                        },
                        proxies=self.proxies,
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