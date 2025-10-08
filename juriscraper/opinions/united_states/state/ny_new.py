from datetime import datetime
import os
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import cloudscraper
import pdfkit
from typing_extensions import override

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.BASE_URL = "https://nycourts.gov/reporter/slipidx/"
        self.court_type="cidxtable"
        self.CURRENT_URL = self.BASE_URL + f"{self.court_type}.shtml"
        self.ARCHIVE_URL = self.BASE_URL + "{court_type}_{year}_{month}.shtml"
        self.proxies = {
            'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050',
        }
        self.scraper = cloudscraper.create_scraper()

    def get_url(self, year: int, month: str) -> str:
        month = month.lower()
        now = datetime.now()
        current_month = now.strftime("%B").lower()  # e.g. "august"
        current_year = now.year

        if year == current_year and month == current_month:
            return self.CURRENT_URL
        return self.ARCHIVE_URL.format(court_type=self.court_type, year=year, month=month)

    def extract_text(self, row, path):
        result = row.xpath(path)
        return result[0].strip() if result else ""

    def to_mongo_format(self, text: str) -> str:
        text=text.replace("NY Slip Op","NYSlipOp")
        return re.sub(r' ', '\u00A0', text.strip())

    def _process_html(self):
        i=1
        current_date = None
        # Go through all rows
        for elem in self.html.xpath("//tr | //caption//b"):
            text = elem.text_content().strip()
            # Check if it's a "Cases Decided" date header
            if text.startswith("Cases Decided"):
                # Extract date part (after "Cases Decided")
                current_date = text.replace("Cases Decided", "").strip()
                continue
            # If it's a case row (must have 4 <td>)
            if elem.tag == "tr":
                cells = elem.xpath("./td")
                if len(cells) < 4:
                    continue  # skip headers
                title_el = cells[0].xpath(".//a")
                title = title_el[0].text_content().strip() if title_el else cells[0].text_content().strip()
                url = urljoin(self.BASE_URL, title_el[0].get("href")) if title_el else ""
                judge = cells[1].text_content().strip()
                docket = cells[2].text_content().strip()
                slip_op = cells[3].text_content().strip()
                # print(docket)
                # print(slip_op)
                if str(title).__eq__("Title") and str(slip_op).__eq__("Slip Opinion No.") :
                    continue

                date = datetime.strptime(current_date, "%B %d, %Y").strftime("%d/%m/%Y")
                res = CasemineUtil.compare_date(self.crawled_till, date)
                if res == 1:
                    continue

                jud_ar=[]
                if not str(judge).__eq__(""):
                    jud_ar = [judge]
                self.cases.append({
                    "name": title, "date": current_date, "status": "Unknown", "url": url, "parallel_citation": [self.to_mongo_format(slip_op)], "judge": jud_ar,"docket":[docket]
                })
                # print(f"{i} - {current_date} || {title} || {docket} || {slip_op} || {judge}")
            i+=1

    @override
    def _request_url_get(self, url):
        self.request["response"]  = self.scraper.get(url, proxies=self.proxies,timeout=60)

    @override
    def _download(self, request_dict={}):
        self._request_url_get(self.url)
        self._post_process_response()
        return self._return_response_text_object()

    def get_state_name(self):
        return "New York"

    def get_class_name(self):
        return "ny_new"

    def get_court_name(self):
        return "New York Court of Appeals"

    def get_court_type(self):
        return "state"

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        for year in range(start_date.year,end_date.year+1):
            for month in months:
                self.url=self.get_url(year,month)
                print(self.url)
                self.parse()
        return 0

    @override
    def _fetch_duplicate(self, data):
        pdf_url = str(data.get("pdf_url")).split("/reporter")[1]
        title = data.get("title")
        date = data.get("date")
        parallel_citation = data.get("parallel_citation")
        court_name = data.get("court_name")
        object_id = None
        query3 = {"pdf_url":{'$regex':pdf_url}}
        dup = self.judgements_collection.find_one(query3)
        if dup is None:
            query4 = {"date":date, "title":title,"parallel_citation":parallel_citation}
            dup2=self.judgements_collection.find_one(query4)
            if not dup2 is None:
                # Check if the document already exists and has been processed
                processed = dup2.get("processed")
                if processed == 10:
                    raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
                else:
                    object_id = dup2.get("_id")
        else:
            processed = dup.get("processed")
            if processed == 10:
                raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
            else:
                object_id = dup.get("_id")
        return object_id

    @override
    def download_pdf(self, data, objectId):
        pdf_url = str(data.__getitem__('pdf_url'))
        year = int(data.__getitem__('year'))

        court_name = data.get('court_name')
        court_type = data.get('court_type')
        state_name = data.get('state')

        if str(court_type).__eq__('state'):
            path = "/synology/PDFs/US/juriscraper/"+court_type+"/"+state_name+"/"+court_name+"/"+str(year)
        else:
            path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + court_name + "/" + str(year)

        obj_id = str(objectId)
        download_pdf_path = os.path.join(path, f"{obj_id}.pdf")
        os.makedirs(path, exist_ok=True)
        update_query={}
        try:
            proxies = {
                'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050', }
            scraper = cloudscraper.create_scraper()  # This handles Cloudflare challenges
            response = scraper.get(pdf_url, proxies=proxies)
            if pdf_url.endswith('.html') or pdf_url.endswith('.htm'):
                # if pdf url contains html then refine it and convert html to pdf and also save modified html
                soup = BeautifulSoup(response.text, 'html.parser')
                # print(soup.text)
                center_divs = soup.find_all('div', align='center')
                for div in center_divs:
                    if div and div.find('input',{'value': 'Return to Decision List'}):
                        div.decompose()
                # Find all anchor tags and remove the href attribute
                for tag in soup.find_all('a'):
                    del tag['href']
                for script in soup.find_all('script'):
                    script.decompose()
                # Find all <p> tags and remove the ones that are empty
                for p in soup.find_all('p'):
                    if not p.get_text(strip=True):  # Check if the <p> tag is empty or contains only whitespace
                        p.decompose()  # Remove the <p> tag
                # Print the modified HTML
                modified_html = soup.prettify()
                pdfkit.from_string(modified_html, download_pdf_path)
                update_query.__setitem__("response_html", modified_html)
            elif pdf_url.endswith(".pdf"):
                with open(download_pdf_path, 'wb') as file:
                    file.write(response.content)
            else:
                with open(download_pdf_path, 'wb') as file:
                    file.write(response.content)

            # if pdf has been downloaded successfully mark processed as 0 and update the record
            update_query.__setitem__("processed", 0)
            self.judgements_collection.update_one({"_id": objectId}, {"$set": update_query})
        except Exception as e:
            # if any error occur during downloading the pdf print the error and mark the record as processed 2
            print(f"Error while downloading the PDF: {e}")
            update_query.__setitem__("processed", 2)
            self.judgements_collection.update_one({"_id": objectId}, {"$set": update_query})
        return download_pdf_path