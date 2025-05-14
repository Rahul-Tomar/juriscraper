from datetime import datetime

import requests
from typing_extensions import override

from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status="Published"
        self.end_year = None

    def get_party_name(self, data):
        return data.get('applicantMarkGoodService') or data.get('opposerMarkGoodService') or "Unknown"

    def get_judge_name(self, data):
        return data.get('panelMember') or ''

    def _process_html(self):
        data_list = list(self.html['results'])
        if data_list.__len__()==0:
            return
        else:
            for data in data_list:
                # print(data)
                docket = data['proceedingNumber']
                pdf_url_code = data['documentId']
                pdf_url = f"https://ttab-reading-room.uspto.gov/cms/rest/{pdf_url_code}"
                title = data['partyName']

                summary = self.get_party_name(data).replace("\n"," ").replace("\t"," ")
                date = data['issueDateStr']
                judges = self.get_judge_name(data)
                if judges.__eq__(''):
                    judges=[]
                else:
                    judges=judges.split(";")
                self.cases.append({
                    "date":date,
                    "docket":[str(docket)],
                    "summary":summary,
                    "url":pdf_url,
                    "name":title,
                    "judge":judges
                })
                # print(f'{date} || {docket} || {title} || {pdf_url} || {cite} || {summary}')


    @override
    def _request_url_post(self, url):
        headers={
            "Host": "ttab-reading-room.uspto.gov",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "Origin": "https://ttab-reading-room.uspto.gov",
            "Connection": "keep-alive",
            "Referer": "https://ttab-reading-room.uspto.gov/efoia/efoia-ui/",
            "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "Priority": "u=0", "Pragma": "no-cache", "Cache-Control": "no-cache",
        }
        new_url = str(url).split("||")[0]
        data = str(url).split("||")[1]
        self.request["response"] = requests.post(url=new_url, headers=headers, verify=self.request["verify"], data=data, proxies=self.proxies, timeout=60)

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.url='https://ttab-reading-room.uspto.gov/ttab-efoia-api/decision/search'
        self.method="POST"
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")
        page=0
        while True:
            self.url = self.url.split("||")[0]
            self.url=self.url+'||{"dateRangeData":{"decisionDate":{"from":"'+from_date+'","to":"'+to_date+'"}},"facetData":{},"parameterData":{},"recordTotalQuantity":100,"searchText":"","sortDataBag":[{"issueDate":"desc"}],"recordStartNumber":'+str(page)+'}'
            self.parameters={}
            self.parse()
            self.downloader_executed=False
            page+=100
            if list(self.html["results"]).__len__()==0:
                break
        return 0

    def get_class_name(self):
        return "ttab"

    def get_court_type(self):
        return "Special"

    def get_state_name(self):
        return "Trial and Appeal Board"

    def get_court_name(self):
        return "Trademark Trial and Appeal Board"