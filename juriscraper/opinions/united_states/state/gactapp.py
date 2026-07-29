# Scraper for Georgia Appeals Court
# CourtID: gactapp
# Court Short Name: gactapp
# Author: Andrei Chelaru
# Reviewer: mlr
# Date created: 25 July 2014
import os
from datetime import date, timedelta, datetime
from curl_cffi import requests
from lxml import html

from casemine.casemine_util import CasemineUtil
from juriscraper.lib.string_utils import titlecase
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"

    def download_pdf(self, data, objectId):
        MAIN_PDF_PATH = "/synology/PDFs/US/juriscraper/"
        TEMP_PDF_PATH = "/home/gaugedata/Downloads/juriscraper/"

        pdf_url = data.__getitem__('pdf_url')
        html_url = data.__getitem__('html_url')
        year = int(data.__getitem__('year'))
        court_name = data.get('court_name')
        court_type = data.get('court_type')

        if str(court_type).__eq__('Federal'):
            state_name = data.get('circuit')
        else:
            state_name = data.get('state')

        opinion_type = data.get('opinion_type')

        if str(opinion_type).__eq__("Oral Argument"):
            path = (
                MAIN_PDF_PATH
                + court_type + "/"
                + state_name + "/"
                + court_name + "/"
                + "oral arguments/"
                + str(year)
            )
        else:
            path = (
                MAIN_PDF_PATH
                + court_type + "/"
                + state_name + "/"
                + court_name + "/"
                + str(year)
            )

        obj_id = str(objectId)
        download_pdf_path = os.path.join(path, f"{obj_id}.pdf")

        if pdf_url is None or str(pdf_url).strip() == "" or str(
            pdf_url).lower() == "null":

            if html_url is None or str(html_url).strip() == "" or str(
                html_url).lower() == "null":
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
            else:
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )

            return download_pdf_path

        os.makedirs(path, exist_ok=True)

        proxy_url = self.proxies.get("https") or self.proxies.get("http")

        if not proxy_url:
            print("No proxy found")
            self.judgements_collection.update_one(
                {"_id": objectId},
                {"$set": {"processed": 2}}
            )
            return download_pdf_path

        for attempt in range(10):
            try:
                # print(f"Downloading PDF attempt {attempt + 1}: {pdf_url}")
                # print(f"Using proxy: {proxy_url}")
                cookies = {
                    "AWSALB": "pxX5HLTauUh0ib76tt/1oTMyIe+OoduWEFI614s7Xf67+C30IhrUGzAYWHWpHoP+cPlR2ayJEoKEyIvUWKm3xQ/KuJ4tEir2BYZwFRXM1qL5DHqCWNsWDY34stWZ",
                    "AWSALBCORS": "pxX5HLTauUh0ib76tt/1oTMyIe+OoduWEFI614s7Xf67+C30IhrUGzAYWHWpHoP+cPlR2ayJEoKEyIvUWKm3xQ/KuJ4tEir2BYZwFRXM1qL5DHqCWNsWDY34stWZ",
                    "aws-waf-token": "abc16cb7-c491-4b09-8e4e-18ffd4e1cf69:EgoArTcqwI+wAAAA:3wOcTlrrl10AsYjl5NvtGHwhGs99bwe0tU3Eg+Emvz1ylhN6XWt7vfpNtQU/BF/tZr5tlFBUMc0PPJgEDe14VEp27Q/I1/RugGBjtPpiFEON35ai4VI91WGLvj4VrBaSEnUvzrJIDRIYopa45gQnoMcqC3rd0jdqyo2/ZiZ+RwhrV4o2HR9mI/TaWoQMJRXfHfEh7PPkg/gJcbfLvRTx9yZXGaDXK3EszfddvpQtgNt3ZIaR1vBNIFyMUv0+3disNfw4No9Aps4ILajnonSQJGIKqIO4k8YXylIptKT1Wo7zF2SZx+2JNYskWlC/aqjtNzFLJmKqrhI=",
                }
                response = requests.get(
                    pdf_url,  # IMPORTANT: use pdf_url, not self.url
                    proxy=proxy_url,
                    cookies=cookies,
                    impersonate="chrome124",
                    verify=False,
                    timeout=60,
                    allow_redirects=True,
                )

                # print("PDF status:", response.status_code)

                if response.status_code != 200:
                    print(f"Bad PDF status: {response.status_code}")
                    continue

                content = response.content

                if not content:
                    print("Empty PDF response")
                    continue

                if not content.startswith(b"%PDF-"):
                    print("Response is not a valid PDF")
                    try:
                        print(response.text[:500])
                    except Exception:
                        pass
                    continue

                with open(download_pdf_path, "wb") as file:
                    file.write(content)

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )

                # print("PDF downloaded successfully")
                return download_pdf_path

            except Exception as e:
                print(f"PDF download failed on attempt {attempt + 1}: {e}")

        self.judgements_collection.update_one(
            {"_id": objectId},
            {"$set": {"processed": 2}}
        )

        return download_pdf_path

    def _process_html(self):
        for row in self.html.xpath("//tr")[::-1][:-1]:
            docket, name, date, disposition, _, url = row.xpath(".//td")
            self.cases.append({"docket": [docket.text_content()],
                               "name": titlecase(name.text_content()),
                               "date": date.text_content(),
                               "disposition": disposition.text_content().title(),
                               "url": url.xpath(".//a")[0].get("href"), })

    def _download(self):
        cookies = {
            "aws-waf-token":"fb4de8ec-9513-4073-8bec-027a21ce75a7:EQoAqiQrEgJcAAAA:yZemRNxDKPIjaGZyWTdbWYeBaBUInKnthuFQ/laVTdpmPp8aN2M3cVw4zJUyfADEIsTSNFCPiEeKh4ThOTz/CzXG3+9ZYlCQaPA3rbzjZus5F1KrKoy7kq8k/w74NrhWVEBFW14DEZ4VCLlFR43yxM8/Eyo5MZfhRqJaNkJuVqT83hoMAJty1JbcqTscRoRN921ZlNsm5+dYS33c9huM9DBp8STtPNW+7+l5TEYII877SVOSV+XmRehWghnGuSDpYT+Tby89rb5IL4iWbETLIwaOfEUBMQokCHD2ipFBMdPxzVf+V8IU0pJessJQ0uaWDJFvlrxq"
        }
        proxy_url = self.proxies.get("https") or self.proxies.get("http")
        try:
            response = requests.get(
                self.url,
                proxy=proxy_url,
                cookies=cookies,
                impersonate="chrome124",
                verify=False,
                timeout=30,
                allow_redirects=True,
            )
            if response.status_code == 200:
                return html.fromstring(response.text)
            else :
                print("failed!!!")
        except :
            print("Proxy failed !")


    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        start = start_date.date().strftime("%Y-%m-%d")
        end = end_date.date().strftime("%Y-%m-%d")
        self.url = f"https://www.gaappeals.gov/wp-content/themes/benjamin/docket/docketdate/results_all.php?OPstartDate={start}&OPendDate={end}&submit=Start+Opinions+Search"
        print(self.url)
        self.parse()
        return 0

    def get_court_name(self):
        return "Georgia Court of Appeals"

    def get_class_name(self):
        return "gactapp"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Georgia"
