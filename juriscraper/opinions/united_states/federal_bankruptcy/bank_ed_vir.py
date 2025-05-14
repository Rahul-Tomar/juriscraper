import json
import os
import re
from datetime import datetime

import requests

from casemine.casemine_util import CasemineUtil
from casemine.constants import MAIN_PDF_PATH
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def download_pdf(self, data, objectId):
        year = int(data.__getitem__('year'))
        court_name = data.get('court_name')
        court_type = data.get('court_type')
        state_name = data.get('state')
        docket = data.get('docket')[0]

        path = MAIN_PDF_PATH + court_type + "/" + state_name + "/" + court_name + "/" + str(year)

        obj_id = str(objectId)
        old_file_path = os.path.join(path, f"{docket}.pdf")
        new_file_path = os.path.join(path, f"{obj_id}.pdf")

        if os.path.exists(old_file_path):
            print(f"Renaming: {old_file_path} → {new_file_path}")
            os.rename(old_file_path, new_file_path)
            self.judgements_collection.update_one({"_id": objectId}, {
                         "$set": {"processed": 0}})
        else:
            print(f"No file to rename for docket: {docket}")
            self.judgements_collection.update_one({"_id": objectId}, {
                         "$set": {"processed": 2}})

        return new_file_path

    def download(self,docket,year,node, uiId,csrfToken,count):
        year = year
        court_name = self.get_court_name()
        court_type = self.get_court_type()
        state_name = self.get_state_name()

        resp = self.get_pdf_url(uiId,csrfToken,node,count)
        url = f"https://www-a.vaeb.uscourts.gov/opinions/{resp}"


        path = MAIN_PDF_PATH + court_type + "/" + state_name + "/" + court_name + "/" + f"20{year.split('/')[-1]}"

        download_pdf_path = os.path.join(path, f"{docket}.pdf")
        try:
            os.makedirs(path, exist_ok=True)
            response = self.session.get(url,headers=self.request['headers'],proxies=self.proxies,verify=False)
            response.raise_for_status()
            with open(download_pdf_path, 'wb') as file:
                file.write(response.content)

        except requests.RequestException as e:
            print(f"Error while downloading the PDF: {e}")

    def get_pdf_url(self, uiId, scrfToken,node,count):
        url = f"{self.base}{uiId}"
        body = {
                "csrfToken":scrfToken,
                "rpc":[
                    {
                        "type":"event",
                        "node": node,
                        "event":"click",
                        "data":{
                            "event.shiftKey":False,
                            "event.metaKey":False,
                            "event.detail":False,
                            "event.ctrlKey":False,
                            "event.clientX":False,
                            "event.clientY":False,
                            "event.altKey":False,
                            "event.button":False,
                            "event.screenY":False,
                            "event.screenX":False
                        }
                    }],
                "syncId":count,
                "clientId":count
            }

        resp = self.session.post(url, json=body,proxies=self.proxies,verify=False)
        raw = resp.text[len("for(;;);"):]
        rec = json.loads(raw)[0]
        return rec['execute'][0][0]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.base = "https://www-a.vaeb.uscourts.gov/opinions/?v-r=uidl&v-uiId="
        self.session = requests.session()
        self.base_pdf ="https://www-a.vaeb.uscourts.gov/opinions/VAADIN/dynamic/resource"
        self.proxies = {
            "http": "http://23.226.137.155:8800",
            "https": "http://23.226.137.155:8800"
        }

    def extract_case_title(self,summary: str) -> str:
        clean_text = re.sub(r'\s+', ' ', summary)

        match = re.search(
            r'(In re:\s+.*?)(?=\s+(Case\s+No\.|Chapter\s+\d+|Misc\. Proc\. No\.|United States|Debtor[s]*\.?|Reorganized Debtor))',
            clean_text,
            re.IGNORECASE
        )
        if match:
            title = match.group(1).strip()

            title = re.sub(r'[\(\)]', '', title)  # remove all ( and )
            title = re.sub(r'\s{2,}', ' ',
                           title)
            title = title.rstrip(',')

            return title

        return ""

    def process_html(self, start: datetime, end: datetime ,uiId,csrfToken) -> None:
        print("inside process html")
        innerHTML_values = [item['value'] for item in self.html if item.get('key') == 'innerHTML']
        html_values = [item['value'] for item in self.html if
                            item.get('key') == 'htmlValue']
        pdf_nodes = [item['node'] for item in self.html if
                       item.get('key') == 'click']

        n = len(html_values)
        nodes = []
        j=1
        while j<len(pdf_nodes):
            nodes.append(pdf_nodes[j])
            j+=2

        idx = 0
        i = 0
        count = 2
        while i < n :
            text = innerHTML_values[idx]
            idx += 1
            docket = innerHTML_values[idx]
            idx += 1
            patterns = {
                "Judge": r"Judge:\s*(.*?)\s*(Chapter:|Type:)",
                "Chapter": r"Chapter:\s*(.*?)\s*Type:",
                "Type": r"Type:\s*(.*?)\s*Division:",
                "Division": r"Division:\s*(.*?)\s*Court:",
                "Court": r"Court:\s*(.*?)\s*Date:",
                "Date": r"Date:\s*(.*)"
            }
            record = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    record[key] = match.group(1).strip()

            date = record['Date'].replace("<b> ","")
            date = date.replace(" </b>","")
            date_obj = datetime.strptime(date, "%m/%d/%y")
            if date_obj < start:
                break
            judge = record['Judge'].replace("<b> ","")
            judge = judge.replace(" </b>","")

            type = record['Type'].replace("<b> ","")
            type = type.replace(" </b>", "")

            division = record['Division'].replace("<b> ","")
            division = division.replace(" </b>", "")

            url = f"{self.base_pdf}/{docket}.pdf"

            summary = html_values[i]
            title = self.extract_case_title(summary)
            self.download(docket,date,nodes[i],uiId,csrfToken,count)
            count += 1

            self.cases.append({
                "date": date,
                "url": url,
                "name": title,
                "judge":[judge],
                "division":division,
                "summary":summary,
                "docket": [docket],
                "type":type
            })


            i += 1


    def create_session(self,uiId , csrfToken):
        session_url = f"{self.base}{uiId}"
        body = {
            "csrfToken":csrfToken,
            "rpc":[
                {
                    "type":"event",
                    "node":1,
                    "event":"ui-navigate",
                    "data":
                        {
                            "route":"/",
                            "query":"",
                            "appShellTitle":"",
                            "historyState":
                                {"idx":0},
                            "trigger":""
                        }
                }],
            "syncId":0,
            "clientId":0
        }
        resp = self.session.post(session_url,json=body,proxies=self.proxies,verify=False)
        return resp

    def get_data(self, uiId, scrfToken):
        print("inside get data")
        url = f"{self.base}{uiId}"
        body = {
            "csrfToken":scrfToken
            ,"rpc":[{
                "type":"publishedEventHandler",
                "node":33,
                "templateEventMethodName":"updateSelectedTab",
                "templateEventMethodArgs":[True],
                "promise":0
            },
                {
                    "type":"publishedEventHandler",
                    "node":15,
                    "templateEventMethodName":"updateSelectedTab"
                    ,"templateEventMethodArgs":[True]
                    ,"promise":0
                },
                {
                    "type":"publishedEventHandler",
                    "node":7,
                    "templateEventMethodName":"setRequestedRange",
                    "templateEventMethodArgs":[0,23],
                    "promise":0
                }
            ],
            "syncId":1,
            "clientId":1
        }
        resp = self.session.post(url, json=body,proxies=self.proxies,verify=False)
        return resp.text

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:

        url ="https://www-a.vaeb.uscourts.gov/opinions/?v-r=init&location=&query="
        self.session.cookies.set("JSESSIONID", "92559844B2BD769E7849B56CC47A7CDD")
        self.session.cookies.set("csrfToken","38cd82d6-f628-4734-ac69-999533d6d2f7")
        token_json =self.session.get(url,headers=self.request['headers'],proxies=self.proxies,verify=False).json()# requests.get(url,headers=self.request['headers'],proxies=self.proxies,verify=False,cookies=cookies).json()
        appconfig = token_json['appConfig']
        uiId = appconfig['v-uiId']
        csrfToken = appconfig['uidl']['Vaadin-Security-Key']
        session_resp = self.create_session(uiId,csrfToken)
        #hit for the data
        html = self.get_data(uiId,csrfToken)
        raw = html[len("for(;;);"):]
        self.html = json.loads(raw)[0]['changes']

        self.process_html(start_date,end_date,uiId,csrfToken)


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

    def get_class_name(self):
        return "bank_ed_vir"

    def get_court_type(self):
        return "Bankruptcy"

    def get_state_name(self):
        return "4th Circuit"

    def get_court_name(self):
        return "Bankruptcy Court Eastern District of Virginia"
