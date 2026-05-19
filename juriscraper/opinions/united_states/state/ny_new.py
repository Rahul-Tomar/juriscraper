from datetime import datetime
import os
import re
from urllib.parse import urljoin
import shutil
import fitz  # PyMuPDF
import requests
from PyPDF2 import PdfReader
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
            # 'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050',
             "http": "http://23.236.154.202:8800",
            "https": "http://23.236.154.202:8800"
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

    def is_pdf_valid(self,file_path):
        """Return True if PDF exists, readable, and not an HTML/error page."""

        if not os.path.isfile(file_path):
            return False, "PDF does not exist"

        if os.path.getsize(file_path) < 1000:
            return False, "PDF is too small or empty"

        try:
            # Detect fake PDF / HTML response
            with open(file_path, "rb") as f:
                first_bytes = f.read(5000)

            # PDF must start with %PDF
            if not first_bytes.startswith(b"%PDF"):
                text = first_bytes.decode(errors="ignore").lower()

                if "404 error" in text or "file not found" in text:
                    return False, "Downloaded file is a 404 HTML page"

                if "<html" in text or "<!doctype html" in text:
                    return False, "Downloaded file is HTML instead of PDF"

                return False, "Invalid PDF format"

            # Validate PDF structure
            reader = PdfReader(file_path)

            if len(reader.pages) == 0:
                return False, "PDF has no pages"

            return True, "PDF is valid and readable"

        except Exception as e:
            return False, f"PDF is corrupted or unreadable: {e}"

    def download_again(self,url,download_pdf_path,obj_id):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(download_pdf_path), exist_ok=True)

            headers = {
                # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }

            #  Fetch HTML
            response = requests.get(url, headers=headers, proxies=self.proxies,
                                    timeout=30)
            response.raise_for_status()

            html = response.text

            #  Detect invalid / 404 HTML before processing
            invalid_patterns = [
                "404 ERROR - File Not Found",
                "Sorry, but the page you requested cannot be found",
                "<title>404 ERROR",
            ]

            if any(
                pattern.lower() in html.lower() for pattern in
                invalid_patterns):
                print("❌ Invalid response / 404 page detected")
                return False

            content_type = response.headers.get("Content-Type", "").lower()

            # ✅ Real PDF
            if "application/pdf" in content_type or response.content.startswith(
                b"%PDF"):
                with open(download_pdf_path, "wb") as f:
                    f.write(response.content)

                # print("✅ Direct PDF downloaded")
                return True

            html = response.text.encode('utf-8', 'ignore').decode('utf-8')

            #  Parse HTML
            soup = BeautifulSoup(html, "lxml")

            #  Fix relative URLs
            for tag in soup.find_all('link', href=True):
                tag['href'] = urljoin(url, tag['href'])

            for tag in soup.find_all('img', src=True):
                tag['src'] = urljoin(url, tag['src'])

            # Add base tag
            if soup.head:
                base_tag = soup.new_tag("base", href=url)
                soup.head.insert(0, base_tag)

            #  Remove unwanted UI
            unwanted_classes = ["header", "footer-container", "skipcontent",
                                "ab-banner"]
            for cls in unwanted_classes:
                for tag in soup.find_all(class_=cls):
                    tag.decompose()

            #  Remove problematic scripts
            for script in soup.find_all("script"):
                src = script.get("src", "")
                if "cloudflare" in src or "cdn-cgi" in src:
                    script.decompose()

            #  Remove iframe
            for iframe in soup.find_all("iframe"):
                iframe.decompose()

            for a in soup.find_all("a"):
                a.unwrap()  # keeps inner text, removes <a> tag

            #  Remove FORM elements completely
            for form in soup.find_all("form"):
                form.decompose()

            #  Remove INPUT buttons (like "Return to Decision List")
            for inp in soup.find_all("input"):
                inp.decompose()

            for div in soup.find_all("div"):
                disclaimer = div.find("p", class_="disclaimer")
                if disclaimer:
                    div.decompose()

            options = {
                'enable-local-file-access': None,
                'load-error-handling': 'ignore',
                'load-media-error-handling': 'ignore',
                'javascript-delay': 2000,
                'no-stop-slow-scripts': None,

                # Important for colors/backgrounds
                'print-media-type': None,
                'background': None,
                'images': None,

                # Better quality
                'dpi': 300,
                'image-quality': 100,
                'encoding': 'UTF-8',
            }

            # wkhtmltopdf config (ensure installed)
            config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')

            pdfkit.from_string(str(soup), download_pdf_path, options=options,
                               configuration=config)

            # print(f"✅ PDF saved at: {download_pdf_path}")
            return True

        except Exception as e:
            print(f"❌ Error downloading {url}: {e}")
            return False

    def cleaned_pdf(self, input_file: str) -> str:
        """
        Remove only hyperlink annotations whose URI starts with:
        https://www.nycourts.gov/reporter/

        If no matching link is found, the PDF is not modified.
        """

        if input_file is None or not os.path.isfile(input_file):
            raise FileNotFoundError(f"PDF file does not exist: {input_file}")

        target_url_prefix = "https://www.nycourts.gov/reporter/"

        temp_folder = "/home/gaugedata/Documents/Juriscraper Test/"
        os.makedirs(temp_folder, exist_ok=True)

        temp_output_file = os.path.join(
            temp_folder,
            os.path.basename(input_file)
        )

        removed_links = 0

        doc = fitz.open(input_file)

        try:
            for page in doc:
                links = page.get_links()

                for link in links:
                    url = link.get("uri")

                    if url and url.startswith(target_url_prefix):
                        page.delete_link(link)
                        removed_links += 1

            # Checkpoint: if no matching link found, do not save/overwrite
            if removed_links == 0:
                # print("No nycourts reporter link found. PDF not modified.")
                return input_file

            doc.save(
                temp_output_file,
                garbage=4,
                deflate=True,
                clean=True
            )

        finally:
            doc.close()

        shutil.move(temp_output_file, input_file)

        print(f"Removed nycourts reporter links: {removed_links}")

        return input_file

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

            scraper = cloudscraper.create_scraper()  # This handles Cloudflare challenges
            response = scraper.get(pdf_url, proxies=self.proxies)
            if pdf_url.endswith('.html') or pdf_url.endswith('.htm') :
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
                    # print(response.content)
                    file.write(response.content)

            is_valid, message = self.is_pdf_valid(download_pdf_path)
            if not is_valid:
                flag = self.download_again(pdf_url, download_pdf_path, obj_id)
                if flag:
                    self.cleaned_pdf(download_pdf_path)
                    update_query.__setitem__("processed", 0)
                    self.judgements_collection.update_one({"_id": objectId}, {
                        "$set": update_query})
                    return download_pdf_path
                else:
                    update_query.__setitem__("processed", 2)
                    self.judgements_collection.update_one(
                        {"_id": objectId}, {"$set": update_query})
                    return download_pdf_path

            # if pdf has been downloaded successfully mark processed as 0 and update the record
            update_query.__setitem__("processed", 0)
            self.judgements_collection.update_one({"_id": objectId}, {"$set": update_query})
        except Exception as e:
            # if any error occur during downloading the pdf print the error and mark the record as processed 2
            print(f"Error while downloading the PDF: {e}")
            update_query.__setitem__("processed", 2)
            self.judgements_collection.update_one({"_id": objectId}, {"$set": update_query})
        return download_pdf_path
