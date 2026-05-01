from datetime import datetime

from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from casemine.casemine_util import CasemineUtil
from playwright.sync_api import sync_playwright
import requests
import os

class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.url = "https://www.jud.ct.gov/LegalResources/MOD"

    def _download(self, request_dict={}):
        pass

    def _process_html(self):
        print(f"Downloading cases from {self.url}")

        PROXY = "http://23.236.197.155:8800"

        with sync_playwright() as p:
            browser = p.firefox.launch(
                headless=True,
                proxy={"server": PROXY}
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
            )

            page = context.new_page()

            # STEP 1: warm session
            page.goto("https://jud.ct.gov/", wait_until="domcontentloaded",
                      timeout=60000)

            # STEP 2: MOD page
            page.goto(
                "https://www.jud.ct.gov/LegalResources/MOD",
                wait_until="domcontentloaded",
                timeout=60000
            )

            # STEP 3: expand all accordions
            page.evaluate("""
                document.querySelectorAll('.accordion-button').forEach(btn => {
                    if (btn.classList.contains('collapsed')) {
                        btn.click();
                    }
                });
            """)

            page.wait_for_timeout(2000)

            # STEP 4: get expanded sections
            sections = page.query_selector_all(".accordion-collapse.show")

            for section in sections:

                # ✅ Extract week text
                week = section.evaluate(
                    "el => el.previousElementSibling.querySelector('button').innerText"
                ).strip()

                # ✅ FIXED date extraction
                date_part = week.split(":")[-1].strip()  # <-- IMPORTANT FIX

                dt = datetime.strptime(date_part, "%m-%d-%Y")

                formatted_date = dt.strftime("%d/%m/%Y")
                date = dt.strftime("%d %b, %Y")

                # optional filter
                res = CasemineUtil.compare_date(self.crawled_till,
                                                formatted_date)
                if res == 1:
                    continue

                # ✅ FIXED selector (NEW DOM STRUCTURE)
                cases = section.query_selector_all(".accordion-body .row")

                for case in cases:
                    docket_el = case.query_selector(".col-3 span")
                    name_el = case.query_selector(".col-5 span")
                    link_el = case.query_selector("a.pdf-link")

                    if not (docket_el and name_el and link_el):
                        continue

                    docket = docket_el.inner_text().strip()
                    if not docket:
                        raise Exception("Docket cannot be null or blank")
                    case_name = name_el.inner_text().strip()
                    url = link_el.get_attribute("href")

                    # normalize URL
                    if url and url.startswith("/"):
                        url = "https://jud.ct.gov" + url

                    if url=="https://www.jud.ct.gov/LegalResources/MOD/DocumentPreview?RandomKey=01C0CC34-9829-4D39-A25E-63BEC34BAF16" and docket=="TSRCV194009799S":
                        break # becuase after this record it moved to a new link

                    self.cases.append({
                        "date": date,
                        "docket": docket,
                        "name": case_name,
                        "url": url,
                        "status": self.status
                    })

                    print({
                        "date": date,
                        "docket": docket,
                        "name": case_name,
                        "doc_url": url,
                        "status": self.status
                    })

            browser.close()


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
                    PROXY = {
                        "server": "http://23.236.154.202:8800"
                    }
                    HEADERS = {
                        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
                        "Accept": "application/pdf,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                    }

                    with sync_playwright() as p:
                        browser = p.firefox.launch(
                            headless=True,
                            proxy=PROXY
                        )
                        context = browser.new_context(
                            extra_http_headers=HEADERS)
                        page = context.new_page()

                        # 🔥 Akamai session warm-up (important for jud.ct.gov)
                        page.goto(
                            "https://www.jud.ct.gov/external/supapp/archiveAROsup25.htm",
                            wait_until="networkidle"
                        )

                        # 🔥 Direct PDF fetch (NO expect_download)
                        response = page.request.get(pdf_url)

                        with open(download_pdf_path, 'wb') as file:
                            file.write(response.body())
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

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return len(self.cases)

    #Fetch duplicate is changed as per changes in title because it is moved to new link and got some difference in title in v and vs and also now we are getting docket also
    def _fetch_duplicate(self, data):
        pdf_url = str(data.get("pdf_url"))
        title = data.get("title")
        date = data.get("date")
        docket = data.get("docket")
        html_url = data.get("html_url")
        court_name = data.get("court_name")
        object_id = None
        if pdf_url.__eq__("") or (pdf_url is None) or pdf_url.__eq__("null"):
            if html_url.__eq__("") or (html_url is None) or html_url.__eq__("null"):
                return object_id
            else:
                query1 = {"html_url":html_url}
                dup1 = self.judgements_collection.find_one(query1)
                if not dup1 is None:
                    query2 = {"court_name": court_name, "date": date}
                    dup2 = self.judgements_collection.find_one(query2)
                    if not dup2 is None:
                        # Check if the document already exists and has been processed
                        processed = dup2.get("processed")
                        if processed == 10:
                            raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
                        else:
                            object_id = dup2.get("_id")

        else:
            query3 = {"pdf_url":pdf_url}
            dup = self.judgements_collection.find_one(query3)
            if dup is None:
                query4 = {"court_name":court_name,"date":date}
                dup2=self.judgements_collection.find_one(query4)
                if not dup2 is None:
                    # Check if the document already exists and has been processed
                    processed = dup2.get("processed")
                    if processed == 10:
                        raise Exception("Judgment already Exists!")  # Replace with your custom DuplicateRecordException
                    else:
                        object_id = dup2.get("_id")
            else:
                query4 = {
                    "court_name": court_name, "date": date}
                dup2 = self.judgements_collection.find_one(query4)
                if not dup2 is None:
                    # Check if the document already exists and has been processed
                    processed = dup2.get("processed")
                    if processed == 10:
                        raise Exception("Judgment already Exists!")
                         # Replace with your custom DuplicateRecordException
                    else:
                        object_id = dup2.get("_id")
        return object_id

    def get_class_name(self):
        return 'conn_super'

    def get_court_name(self):
        return 'Superior Court of Connecticut'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Connecticut'

