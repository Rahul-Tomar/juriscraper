# Scraper for the United States Tax Court
# CourtID: tax
# Court Short Name: Tax Ct.
# Neutral Citation Format (Tax Court opinions): 138 T.C. No. 1 (2012)
# Neutral Citation Format (Memorandum opinions): T.C. Memo 2012-1
# Neutral Citation Format (Summary opinions: T.C. Summary Opinion 2012-1
import json
import os
import shutil
import time
from datetime import date, datetime, timedelta
from typing import Tuple

import requests
from typing_extensions import override

from casemine.constants import MAIN_PDF_PATH
from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import titlecase
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    first_opinion_date = datetime(1986, 5, 1)
    days_interval = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = None
        self.set_blue_green = None
        self.base = "https://public-api-green.dawson.ustaxcourt.gov/public-api"
        self.url = f"{self.base}/opinion-search"
        self.court_id = self.__module__
        self.make_backscrape_iterable(kwargs)
        self.method = "GET"

    def _download(self, request_dict={}):
        """Download from api

        The tax court switches between blue and green deploys so we need to
        check which one is current before we continue

        :param request_dict: An empty dictionary.
        :return: None
        """
        if not self.set_blue_green and not self.test_mode_enabled():
            check = self.request["session"].get(self.url)
            if check.status_code != 200:
                self.base = (
                    "https://public-api-blue.dawson.ustaxcourt.gov/public-api"
                )
                self.url = f"{self.base}/opinion-search"
            self.set_blue_green = True
        if self.test_mode_enabled():
            with open(self.url) as file:
                self.json = json.load(file)
        else:
            self.json = (
                self.request["session"]
                .get(
                    self.url,
                    params=self.params,
                )
                .json()
            )

    def _process_html(self) -> None:
        """Process the html

        Iterate over each item on the page collecting our data.
        return: None
        """
        for case in self.json['results']:
            print(case)
            url = self._get_url(case["docketNumber"], case["docketEntryId"])
            status = (
                "Published"
                if case["documentType"] == "T.C. Opinion"
                else "Unpublished"
            )
            temp_dir = f'/home/gaugedata/Downloads/temp_dir_for_tax/'
            os.makedirs(temp_dir, exist_ok=True)
            file_name=temp_dir+f"{case['docketNumber']}.pdf"
            response = requests.get(url=url, proxies={'http': 'socks5h://127.0.0.1:9050','https': 'socks5h://127.0.0.1:9050',})
            response.raise_for_status()
            # print(f'pdf_url - {url}')
            with open(file_name, 'wb') as file:
                file.write(response.content)
            # print("pdf downloaded")
            self.cases.append(
                {
                    "judge": [case.get(
                        "signedJudgeName", case.get("judge", "")
                    )],
                    "date": case["filingDate"][:10],
                    "docket": [case["docketNumber"]],
                    "url": url,
                    "name": titlecase(case["caseCaption"]),
                    "status": status,
                }
            )

    def _get_url(self, docket_number: str, docketEntryId: str) -> str:
        """Fetch the PDF URL with AWS API key

        param docket_number: The docket number
        param docketEntryId: The docket entry id
        return: The URL to the PDF
        """
        self.url = f"{self.base}/{docket_number}/{docketEntryId}/public-document-download-url"
        if self.test_mode_enabled():
            # Don't fetch urls when running tests.  Because it requires
            # a second api request.
            return self.url
        pdf_url = super()._download()["url"]
        return pdf_url

    def _download_backwards(self, dates: Tuple[date]) -> None:
        """Make custom date range request to the API

        Note that the API returns 100 results or less, so the
        days_interval should be conservative

        :param dates: (start_date, end_date) tuple
        :return None
        """
        self.params["startDate"] = dates[0].strftime("%m/%d/%Y")
        self.params["endDate"] = dates[1].strftime("%m/%d/%Y")
        self._download()
        logger.info(
            "Backscraping for range %s %s\n%s cases found",
            *dates,
            len(self.json),
        )
        self._process_html()

        # Using time.sleep to prevent rate limiting
        # {'message': 'you are only allowed 15 requests in a 60 second window time', 'type': 'ip-limiter'}
        if len(self.json) > 0:
            logger.info("Sleeping for 61 seconds to prevent rate limit")
            # time.sleep(61)


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        # print(f"startDate {start_date.strftime('%m/%d/%Y')} -> endDate {end_date.strftime('%m/%d/%Y')}")
        self.params = {
            "dateRange": "customDates", "startDate": start_date.strftime("%m/%d/%Y"), "endDate": end_date.strftime("%m/%d/%Y"), "opinionTypes": "MOP,SOP,TCOP", }
        self.parse()
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
            try:
                # Source file
                source_path = f'/home/gaugedata/Downloads/temp_dir_for_tax/{data.__getitem__("docket")[0]}.pdf'

                # Destination path with new filename
                # destination_path = '/synology/PDFs/US/juriscraper/Special/Tax/United States Tax Court/2025/680632cea0960b94ae336600.pdf'

                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(download_pdf_path), exist_ok=True)

                # Move and rename the file
                shutil.move(source_path, download_pdf_path)
                self.judgements_collection.update_one({"_id": objectId}, {"$set": {"processed": 0}})
            except Exception as ex:
                print(f"Error while downloading the PDF: {ex}")
                self.judgements_collection.update_many({"_id": objectId}, {
                    "$set": {"processed": 2}})
        return download_pdf_path


    def get_court_type(self):
        return "Special"

    def get_court_name(self):
        return "United States Tax Court"

    def get_state_name(self):
        return "Tax"

    def get_class_name(self):
        return "tax"
