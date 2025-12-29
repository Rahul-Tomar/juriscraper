from datetime import datetime
import json
import requests
import re

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.method = "POST"
        self.url = "https://lafcca.hosted2.civiclive.com/portal/svc/ContentItemSvc.asmx/GetItemList"
        temp_date = None
        # Request payload
        self.parameters = {
            "parentId": "283468",
            "Params": json.dumps({
                "ContextId": 283467,
                "OneLink": "/cms/One.aspx",
                "RawUrl": "/cms/One.aspx?portalId=161585&pageId=283465",
                "Extension": "23741",
                "ClientId": "ctl00_ContentPlaceHolder1_ctl10",
                "Place": "cms",
                "ThisRequest": "https://lafcca.hosted2.civiclive.com:443/cms/One.aspx?portalId=161585&pageId=283465",
                "Link": "/cms/One.aspx?portalId=161585&pageId=283465&objectId.23741=283468&contextId.23741=283467&parentId.23741=283467",
                "PortalId": "161585",
                "PageId": "283465",
                "HideDescription": True,
                "ShowDispSettings": False,
                "ShowSecurity": False,
                "ShowActivity": False,
                "ShowSubscription": True,
                "id": 5,
                "csFolder.html": "/Common/controls/ContentItemModern/Controls/csFolder.html",
                "csFile.html": "/Common/controls/ContentItemModern/Controls/csFile.html",
                "csLink.html": "/Common/controls/ContentItemModern/Controls/csLink.html",
                "csMove.html": "/Common/controls/ContentItemModern/Controls/csMove.html",
                "csDisplaySettings.html": "/Common/controls/ContentItemModern/Controls/csDisplaySettings.html",
                "csFileProps.html": "/Common/controls/ContentItemModern/Controls/csFileProps.html",
                "csContentActivity.html": "/Common/controls/ContentItemModern/Controls/csContentActivity.html",
                "csContentAlert.html": "/Common/controls/ContentItemModern/Controls/csContentAlert.html",
                "searchVal": "",
                "Segment": "https://lafcca.hosted2.civiclive.com/cms/One.aspx",
                "InstanceId": "23741"
            })
        }

        # Headers
        self.request["headers"] = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://lafcca.hosted2.civiclive.com/cms/One.aspx?portalId=161585&pageId=283465",
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://lafcca.hosted2.civiclive.com"
        }

    def _download(self):
        """Execute POST request and parse JSON"""
        self.downloader_executed = True
        self._request_url_post(self.url)

    def _request_url_post(self, url):
        """Perform POST request and save response"""
        self.request["url"] = url
        try:
            resp = requests.post(
                url,
                headers=self.request["headers"],
                json=self.parameters,
                verify=False,
                timeout=60
            )
            self.request["response"] = resp
            print(f"[DEBUG] HTTP {resp.status_code} from {url}")
        except Exception as e:
            print("[ERROR] POST request failed:", e)
            self.request["response"] = None

    def _process_html(self):
        """Process JSON response"""
        resp = self.request.get("response")
        if not resp:
            print("[WARN] No response to process")
            return

        try:
            data = resp.json()
            self.html = data

            print("[INFO] JSON data received with keys:", list(data.keys()))
            items = data.get("d", {}).get("DataObject", [])
            print(f"[INFO] Total items: {len(items)}")

            for item in items:
                i=1
                full_title = item.get("Title", "")
                date_str = item.get("CreationDateString", "")
                url = item.get("DownloadLink", "")

                # Convert "06 October, 2025" -> "06/10/2025"
                date = datetime.strptime(date_str, "%d %B, %Y").strftime("%Y-%m-%d")
                # print(date)

                # Extract docket at start of title and remove from title
                match = re.match(r"^(\d{4}\s+[A-Z]{2}\s+\d+)\s+(.*)",
                                 full_title)
                if match:
                    docket = [match.group(1)]
                    name = match.group(2)
                else:
                    raise ValueError(
                        f"Title does not start with a docket number: {full_title}")

                res = CasemineUtil.compare_date(self.crawled_till, date)
                if res==1:
                    continue

                self.cases.append({
                    "docket": docket, "name": name, "url": url,
                    "date": date_str})
                # print(f"📅 Date: {date_str} | 🧾 Docket: {docket} | Title: {name} | PDF: {url}")

        except Exception as e:
            print("[ERROR] Failed to parse JSON:", e)
            print(resp.text[:500])
            self.html = None

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        print("[INFO] Crawling from", start_date, "to", end_date)
        self.parse()
        # Return number of items
        items = self.html.get("d", {}).get("DataObject", []) if self.html else []
        return 0

    def get_class_name(self):
        return 'lactapp_new'

    def get_court_name(self):
        return 'Louisiana Court of Appeal'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Louisiana'
