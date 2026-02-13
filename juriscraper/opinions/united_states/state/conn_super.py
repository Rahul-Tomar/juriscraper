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
        self.url = "https://jud.ct.gov/Superiorcourt/MOD/MODListing.aspx"

    def _download(self, request_dict={}):
        pass

    def _process_html(self):
        # print("hello")
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
            page.goto("https://jud.ct.gov/", wait_until="networkidle",
                      timeout=60000)

            # STEP 2: MOD page
            page.goto(
                "https://jud.ct.gov/Superiorcourt/MOD/MODListing.aspx",
                wait_until="networkidle",
                timeout=60000
            )

            # STEP 3: expand ALL collapsable sections (JS-level click = most reliable)
            page.evaluate("""
                document.querySelectorAll('span.minButton').forEach(btn => btn.click());
            """)

            page.wait_for_timeout(1000)

            # STEP 4: iterate through each week section
            sections = page.query_selector_all("article.collapsable")
            for section in sections:
                # Extract week starting date
                header_text = section.query_selector("header").inner_text()
                week = header_text.split("Entries for the week starting on:")[
                    -1].strip().rstrip(":")

                # print(f"\nWEEK: {week}")
                date_part = week.split(':')[0]
                m, d, y = date_part.split('-')
                formatted_date = f"{d}/{m}/{y}"
                dt = datetime.strptime(date_part, "%m-%d-%Y")

                date = dt.strftime("%d %b , %Y")
                res = CasemineUtil.compare_date(self.crawled_till, formatted_date)
                if res == 1:
                    continue
                # Each case entry
                cases = section.query_selector_all(
                    "div.collapsable_cont article.MODList > div.fullWidth"
                )

                for case in cases:
                    docket = case.query_selector(
                        ".DocketNo").inner_text().strip()
                    case_name = case.query_selector(
                        ".CaseName").inner_text().strip()

                    link_el = case.query_selector(".DocURL a")
                    url = link_el.get_attribute("href") if link_el else ""

                    # Normalize URL
                    if url and not url.startswith("http"):
                        url = "https://jud.ct.gov/Superiorcourt/MOD/" + url.lstrip("/")

                    self.cases.append({
                        "date": date,
                        "docket": docket,
                        "name": case_name,
                        "url": url,
                        "status":self.status
                    })


                    print({
                        "date": date,
                        "docket": docket,
                        "name": case_name,
                        "doc_url": url,
                        "status":self.status
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



    def get_class_name(self):
        return 'conn_super'

    def get_court_name(self):
        return 'Superior Court of Connecticut'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Connecticut'

