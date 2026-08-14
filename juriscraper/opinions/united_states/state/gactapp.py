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
                    "AWSALB": "SqAZJ8tQwk+IZOBgAqQM6JeOEBjQC+15tB4+4xHweRxPke/bdyJ8k4dLfQIBIDqk1VgIFt65yfXXRMGFn3UCC0Y81/I3ZvQS2j1o5cV2Q9QUWFQrG3e2A0bIxJq7",
                    "AWSALBCORS": "SqAZJ8tQwk+IZOBgAqQM6JeOEBjQC+15tB4+4xHweRxPke/bdyJ8k4dLfQIBIDqk1VgIFt65yfXXRMGFn3UCC0Y81/I3ZvQS2j1o5cV2Q9QUWFQrG3e2A0bIxJq7",
                    "aws-waf-token": "91132089-fc62-4632-a377-4255aba7707b:EQoAsuVFDpeHAAAA:FJzVyVhZHDZj/BuxX+0j+v0GFUngfCDBTzFHiyNY5a4h6qfNLd+Jbdx2AEA0Bq29R//AgRYXeWTBDUlXdsM7TBgP2RHsiuGGySAgydaRtDbiSqE0CHdcTYilC+S3QdH2r9xk43M3dy1iyxm5cJtOom1m9nZQprfzfBVWVc8EKr1Cg3axNoC9JssyhWIkfPrTpwM9gfJWmGE5Rbcrkld9+wXXnxup/THuZ2NPO8J6y0wmMFi5vIJhl9AvQgAJqeycnim0lEIhqRLuYry9xfuBZp1NyHJW5/KfJOuiegMsXztq/R7fGsK1KObiFP1N4JbhHXjVmIB4734=",
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
            "aws-waf-token":"91132089-fc62-4632-a377-4255aba7707b:EQoAmyNEfFfPAAAA:+PXXgSD9mNs0S/EgiSY8JbCfRIwzLHRuk9VDe8gaO2rDeIgYvEMSRDyWakSCjADl8TMalpCVjG1nCmGo149QDoO7qPULRye0h6Mc+Fu6TQrLoNozTJIfrhjOvU/YQpXkD1jjT0KR2Br+zjVIY3ka5Ogf34FI8JxusvARRitw5z6Mhsapq1d/OEb/pPJSGyBAD6cfwx7I+B2o/LvO8AfhktoVJeovdKr0gnlbCnH6/GM1fDSR/S6DD0Jr02RMdSdgGTYpFxa2Brmx+3a9N9BsVDbslT3kLAYRuNtjf+eKL0+b1oJt+bh/CEzC9rxuhm6HkJrWfwqv"
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
