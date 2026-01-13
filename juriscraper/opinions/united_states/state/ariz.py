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
import os
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
                # with open("/home/gaugedata/Downloads/response.html", "w",
                #           encoding="utf-8") as f:
                #     f.write(response.text)
                # print(response.text)
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
                # print(response2.text)
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
                # print(pagination_response.text)
                # print(pagination_response.status_code)
                # print(pagination_response.text[:2000])
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
                # print(pagination_response.status_code)
                # print(pagination_response.text[:2000])
                self.html = html.fromstring(pagination_response.text)
            else:
                pass

            # print(self.html.xpath("string()")[:1000])
            # print(html.tostring(self.html, pretty_print=True).decode("utf-8")[:20000])
            # print(html.tostring(self.html, pretty_print=True).decode("utf-8")[
            #           :10000000])
            rows = self.html.xpath("//table//tr")
            # print(len(rows))
            doc_path = '//div[contains(@class,"title-number")]//span[@class="field-content"]/text()'
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
                            "Cookie": ".ASPXANONYMOUS=9EyfwsJo5T4dHKU65EjYU0XykBeT9hyeZkuuFgpVSD8z8B_ueKUpUVjgeHVaMsju-aTjSAKRmoiWsnhNxdIs9lniNaNykEeevTCIsg7HeOk9t71K0; _ga_9N7TX7BQ5D=GS2.1.s1765279720$o4$g1$t1765279746$j34$l0$h0; _ga=GA1.1.300682627.1762929701; __utma=213495364.300682627.1762929701.1763028233.1765279725.3; __utmz=213495364.1763028233.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); dnn_IsMobile=False; language=en-US; LastRotate5004=0; __RequestVerificationToken=6JRxLN2dVAwY7bNlvmlk_UGcNkUqpVSLZLZuviVP6X9YFFkJdqay23iXL2HaaBCwV8586Q2; ShowAt5004=0; ASP.NET_SessionId=n24ia0lz55us33nbdudc30vk; __utmc=213495364; __cf_bm=QpYQo_uBB8zGPJM0b52BCjWGLFXEQTiPWwrMvy2zgD0-1765279751.5874143-1.0.1.1-MZf0mRg7ml1fq8clWfOrG9YOiYVn0D4HflCSuAB5.WydPpI.5XXICmfhFZ5NbmKdMGSHw7C1oF_9iwIw4H8iQiBdbxdbNPw65uE3Xhmu2jjLJaylbd7qZNvZiD3hYz5N; __utmb=213495364.2.10.1765279725; __utmt=1",
                            "Host": "www.azcourts.gov",
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

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court Of The State Of Arizona"

    def get_state_name(self):
        return "Arizona"

    def get_class_name(self):
        return "ariz"
