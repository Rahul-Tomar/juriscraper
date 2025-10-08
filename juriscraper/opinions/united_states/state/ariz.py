"""
Author: Michael Lissner
Date created: 2013-04-05
Revised by Taliah Mirmalek on 2014-02-07
Scraper for the Supreme Court of Arizona
CourtID: ariz
Court Short Name: Ariz.
"""

import time
from datetime import date, datetime

from lxml import html
import requests

from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import titlecase
from juriscraper.OpinionSite import OpinionSite


class Site(OpinionSite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls=[]
        self.names=[]
        self.dates=[]
        self.status=[]
        self.dockets=[]
        self.court_id = self.__module__

    def _get_download_urls(self):
        # path = '//a[contains(@id , "hypCaseNum")]/@href'
        # return [t for t in self.html.xpath(path)]
        return self.urls

    def _get_case_names(self):
        # path = '//span[contains(@id , "lblTitle")]//text()'
        # return [titlecase(t.upper()) for t in self.html.xpath(path)]
        return self.names

    def _get_case_dates(self):
        # path = '//span[contains(@id , "FilingDate")]//text()'
        # return [date.fromtimestamp(
        #     time.mktime(time.strptime(date_string, "%m/%d/%Y"))) for
        #     date_string in self.html.xpath(path)]
        return self.dates

    def _get_precedential_statuses(self):
        # statuses = []
        # path = '//*[contains(@id, "DecType")]/text()'
        # for s in self.html.xpath(path):
        #     if "OPINION" in s:
        #         statuses.append("Published")
        #     elif "MEMORANDUM" in s:
        #         statuses.append("Unpublished")
        #     else:
        #         statuses.append("Unknown")
        # return statuses
        return self.status

    def _get_docket_numbers(self):
        # path = '//a[contains(@id , "hypCaseNum")]//text()'
        # return [t for t in self.html.xpath(path)]
        return self.dockets

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        page = 1
        flag=True
        while flag:
            self.method="POST"
            if self.get_class_name().__eq__('ariz'):
                self.url = "https://opinions.azcourts.gov/SearchOpinionsMemoDecs.aspx?year=2025&court=999"
                response = requests.get(url=self.url, proxies=self.proxies)
                tree = html.fromstring(response.text)
                viewstate_value = tree.xpath('//input[@id="__VIEWSTATE"]/@value')[0]
                viewstate_generator_value = tree.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')[0]
                start_date.strftime("%m/%d/%Y")
                self.parameters = {
                    "__LASTFOCUS": "",
                    "KB_JSTester_JSEnabled": "1",
                    "KB_JSTester_JQueryVsn": "3.7.1",
                    "__EVENTTARGET": "",
                    "__EVENTARGUMENT": "",
                    "__VIEWSTATE": f"{viewstate_value}",
                    "__VIEWSTATEGENERATOR": f"{viewstate_generator_value}",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlDecType": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtDateFrom":  start_date.strftime("%m/%d/%Y"),
                    "dnn$ctr9904$ViewAOC_Opinions$txtDateTo": end_date.strftime("%m/%d/%Y"),
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCourt": "999",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCaseType": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCaseSubType": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCaseNum": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtCaseNum1": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtCaseNum2": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtCaseTitle": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlJudge": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlJudgeSave": "584",
                    "dnn$ctr9904$ViewAOC_Opinions$txtJudge": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlDispo": "0",
                    "dnn$ctr9904$ViewAOC_Opinions$btnSubmit": "Submit",
                    "translate": "",
                    "ScrollTop": "342",
                    "__dnnVariable": "`{`__scdoff`:`1`}"
                }
                response2 = requests.post(url=self.url, proxies=self.proxies, data=self.parameters)
                pagination_param={
                    "KB_JSTester_JSEnabled": "1",
                    "KB_JSTester_JQueryVsn": "3.7.1",
                    "__EVENTTARGET": "dnn$ctr9904$ViewAOC_Opinions$gvList",
                    "__EVENTARGUMENT": f"Page${page}",
                    "__VIEWSTATE": f"{viewstate_value}",
                    "__VIEWSTATEGENERATOR": f"{viewstate_generator_value}",
                    "translate": "", "ScrollTop": "114", "__dnnVariable": "{\"__scdoff\":\"1\"}"
                }
                logger.info(f"{self.url}&page={page}")
                pagination_response = requests.post(url=self.url, proxies=self.proxies, data=pagination_param)

                self.html = html.fromstring(pagination_response.text)
                # print(html.tostring(self.html, pretty_print=True).decode("utf-8"))
            elif self.get_class_name().__eq__('arizctapp_div_1'):
                response = requests.get(url=self.url, proxies=self.proxies)
                tree = html.fromstring(response.text)
                viewstate_value = tree.xpath('//input[@id="__VIEWSTATE"]/@value')[0]
                viewstate_generator_value = tree.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')[0]
                self.parameters = {
                    "__LASTFOCUS": "",
                    "KB_JSTester_JSEnabled": "1",
                    "KB_JSTester_JQueryVsn": "3.7.1",
                    "__EVENTTARGET": "",
                    "__EVENTARGUMENT": "",
                    "__VIEWSTATE": f"{viewstate_value}",
                    "__VIEWSTATEGENERATOR": f"{viewstate_generator_value}",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlDecType": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtDateFrom":  start_date.strftime("%m/%d/%Y"),
                    "dnn$ctr9904$ViewAOC_Opinions$txtDateTo": end_date.strftime("%m/%d/%Y"),
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCourt": "998",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCaseType": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCaseSubType": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlCaseNum": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtCaseNum1": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtCaseNum2": "",
                    "dnn$ctr9904$ViewAOC_Opinions$txtCaseTitle": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlJudge": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlJudgeSave": "325",
                    "dnn$ctr9904$ViewAOC_Opinions$txtJudge": "",
                    "dnn$ctr9904$ViewAOC_Opinions$ddlDispo": "0",
                    "dnn$ctr9904$ViewAOC_Opinions$btnSubmit": "Submit",
                    "translate": "",
                    "ScrollTop": "342",
                    "__dnnVariable": "`{`__scdoff`:`1`}"
                }
                response2 = requests.post(url=self.url, proxies=self.proxies, data=self.parameters)
                pagination_param = {
                  "KB_JSTester_JSEnabled": "1",
                  "KB_JSTester_JQueryVsn": "3.7.1",
                  "__EVENTTARGET": "dnn$ctr9904$ViewAOC_Opinions$gvList",
                  "__EVENTARGUMENT": f"Page${page}",
                  "__VIEWSTATE": f"{viewstate_value}",
                  "__VIEWSTATEGENERATOR": f"{viewstate_generator_value}",
                  "translate": "",
                  "ScrollTop": "1139",
                  "__dnnVariable": {
                    "__scdoff": "1"
                  }
                }
                logger.info(f"{self.url}&page={page}")
                pagination_response = requests.post(url=self.url, proxies=self.proxies, data=pagination_param)
                self.html = html.fromstring(pagination_response.text)
            else:
                pass

            doc_path = '//a[contains(@id , "hypCaseNum")]//text()'
            for t in self.html.xpath(doc_path):
                self.dockets.append([t])

            status_path = '//*[contains(@id, "DecType")]/text()'
            for s in self.html.xpath(status_path):
                if "OPINION" in s:
                    self.status.append("Published")
                elif "MEMORANDUM" in s:
                    self.status.append("Unpublished")
                else:
                    self.status.append("Unknown")

            date_path = '//span[contains(@id , "FilingDate")]//text()'
            for date_string in self.html.xpath(date_path):
                date_obj = datetime.strptime(date_string,"%m/%d/%Y")
                last_date = date_obj.strftime("%d/%m/%Y")
                res = CasemineUtil.compare_date(last_date,self.crawled_till)
                if res==-1:
                    flag=False
                self.dates.append(date.fromtimestamp(time.mktime(time.strptime(date_string, "%m/%d/%Y"))))

            name_path = '//span[contains(@id , "lblTitle")]//text()'
            for t in self.html.xpath(name_path):
                casename=titlecase(t.upper())
                self.names.append(casename)

            url_path = '//a[contains(@id , "hypCaseNum")]/@href'
            for t in self.html.xpath(url_path):
                if not str(t).__contains__("https://opinions.azcourts.gov"):
                    self.urls.append("https://opinions.azcourts.gov"+t)
                else:
                    self.urls.append(t)

            target_tr = self.html.xpath('//tr[@align]')
            if target_tr:
                td_elements = target_tr[0].xpath('.//td//td')
                td_values = [td.text_content().strip() for td in td_elements]
                last_td = td_elements[-1]
                a_tag = last_td.xpath('.//a[@href]')
                print(html.tostring(a_tag[0],pretty_print=True).decode("utf-8"))
                if list(a_tag).__len__()==0:
                    flag=False
            else:
                flag=False

            page = page + 1
            self.downloader_executed = False

        for attr in self._all_attrs:
            self.__setattr__(attr, getattr(self, f"_get_{attr}")())
        self._clean_attributes()
        if "case_name_shorts" in self._all_attrs:
            self.case_name_shorts = self._get_case_name_shorts()
        self._post_parse()
        self._check_sanity()
        self._date_sort()
        self._make_hash()
        return 0

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court Of The State Of Arizona"

    def get_state_name(self):
        return "Arizona"

    def get_class_name(self):
        return "ariz"
