from datetime import datetime
from xmlrpc.client import boolean
import pdfkit
import os
import requests
from lxml import html as lxml_html
from lxml import etree
import re
from bs4 import BeautifulSoup

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from playwright.sync_api import sync_playwright
class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url="https://www.oscn.net/rss/STOKCSSC.asp"
        self.proxies = {
            "http": "http://156.241.221.148:8800",
            "https": "http://156.241.221.148:8800"
            }
        self._opt_attrs = [
            "adversary_numbers",
            "causes",
            "dispositions",
            "divisions",
            "docket_attachment_numbers",
            "docket_document_numbers",
            "docket_numbers",
            "judges",
            "lower_courts",
            "lower_court_judges",
            "lower_court_numbers",
            "nature_of_suit",
            "citations",
            "parallel_citations",
            "summaries",
            "case_name_shorts",
            "child_courts",
            "authors",
            "joined_by",
            "per_curiam",
            "types",
            "other_dates",
            "html_urls",
            "response_htmls",
            "opinion_types",
            "teasers",
            "revision_status"
        ]
        self._opt_attrs = self._opt_attrs + ["cite_info_html"]
        self._all_attrs = self._req_attrs + self._opt_attrs

        for attr in self._all_attrs:
            self.__setattr__(attr, None)

    def _process_html(self):
        xml_string = etree.tostring(
            self.html,
            encoding="unicode",
            method="xml"
        )

        # 2. Fix malformed <link/>URL into <link>URL</link>
        fixed_xml = re.sub(
            r"<link\s*/>\s*(http[^<\s]+)",
            r"<link>\1</link>",
            xml_string
        )

        # 3. Parse safely (RSS is malformed)
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(
            fixed_xml.encode("utf-8"),
            parser=parser
        )

        # 4. Extract links (one by one)
        for idx, item in enumerate(root.xpath("//item"), start=1):
            link = item.findtext("link")
            # print(f"{idx}. {link}")
            flag = False
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Host": "www.oscn.net",
                "Referer": "https://oksc.oscn.net/",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
            }
            self.US_PROXIES = [
                # ("23.236.154.202", 8800),
                # ("23.236.154.249", 8800),
                # ("23.236.197.155", 8800),
                # ("23.236.197.227", 8800),
                # ("23.236.197.153", 8800),
                # ("156.241.221.148", 8800),
                ("156.241.216.136", 8800),
                ("156.241.216.8", 8800),
                ("156.241.216.194", 8800),
                ("156.241.221.92", 8800),
                ("156.241.216.136", 8800),
                ("156.241.216.8", 8800),
                ("156.241.216.194", 8800),
                ("156.241.221.92", 8800),
                ("23.236.154.202", 8800),
                ("23.236.154.249", 8800),
                ("23.236.197.155", 8800),
                ("23.236.197.227", 8800),
                ("23.236.197.153", 8800),
                ("156.241.221.148", 8800),
            ]
            resp=None
            for ip, port in self.US_PROXIES:
                proxy = self.make_proxy(ip, port)

                try:
                    resp = requests.get(
                        link,
                        headers=headers,
                        proxies=proxy,
                        timeout=30
                    )

                    print(f"Trying {ip}:{port} → {resp.status_code}")

                    if resp.status_code == 200:
                        break

                except requests.RequestException as e:
                    print(f"Proxy failed {ip}:{port} → {e}")
                    continue

            if not resp or resp.status_code != 200:
                raise RuntimeError("All proxies exhausted, no 200 response")

            soup = BeautifulSoup(resp.text, "lxml")
            content = str(soup)
            container = soup.select_one("#tmp-style")

            # --- TITLE ---
            title = container.find("font", size="4").get_text(strip=True)
            citation = container.find("font", size="2").get_text(strip=True)
            date_match = re.search(r"Decided:\s*([0-9/]+)",
                                   container.get_text())
            decision_date = datetime.strptime(date_match.group(1),
                                              "%m/%d/%Y").date()
            date = decision_date.strftime("%b %d , %Y")
            parsed_date = decision_date.strftime("%d/%m/%Y")

            # res = CasemineUtil.compare_date(self.crawled_till, parsed_date)
            # if res == 1:
            #     # continue
            #     return
            citation = container.find("font", size="1").get_text(strip=True)
            if "," in citation:
                parallel_citation = citation.split(",", 1)[1].strip()
            else:
                parallel_citation = ''
            pdf_url=''
            # --- CASE NUMBER + URL ---
            case_link = container.find("a")
            case_url=''
            if case_link:
                flag = True
                case_url = "https://www.oscn.net/applications/oscn/" + case_link["href"]
                case_response = None
                for ip, port in self.US_PROXIES:
                    proxy = self.make_proxy(ip, port)

                    try:
                        case_response = requests.get(
                            case_url,
                            headers=headers,
                            proxies=proxy,
                            timeout=30
                        )

                        print(f"Trying {ip}:{port} → {case_response.status_code}")

                        if case_response.status_code == 200:
                            break

                    except requests.RequestException as e:
                        print(f"Proxy failed {ip}:{port} → {e}")
                        continue

                if not resp or resp.status_code != 200:
                    raise RuntimeError(
                        "All proxies exhausted, no 200 response")

                if case_response.status_code==200:
                    case_soup = BeautifulSoup(case_response.text, "lxml")
                    # print(soup.prettify())

                    table = case_soup.find("table", class_="docketlist")
                    if not table:
                        return

                    tbody = table.find("tbody")
                    if not tbody:
                        return

                    for tr in tbody.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) < 3:
                            continue

                        # --- DATE ---
                        dt_el = tds[0].find("nobr")
                        if not dt_el:
                            continue
                        dt_str = dt_el.get_text(strip=True)

                        # --- TYPE ---
                        type_el = tds[1].find("nobr")
                        if not type_el:
                            continue
                        doc_type = type_el.get_text(strip=True)

                        if doc_type not in ("OPIN", "ORDR"):
                            continue

                        # --- DATE CHECK FOR ORDR ---
                        if doc_type == "ORDR":
                            dt_str = dt_str.replace("-", "/")
                            if dt_str != date:
                                continue

                        # --- PDF LINK ---
                        pdf_a = tds[2].select_one(
                            "div.description-wrapper a.doc-pdf")
                        if not pdf_a:
                            continue

                        pdf_url = "https://www.oscn.net/dockets/" + pdf_a["href"]
                        # print("Got PDF URL:", pdf_url)
            case_number = case_link.get_text(strip=True)
            if not case_number:
                case_number=citation
            status = self.detect_publication_status(content)
            div = self.extract_opinion_html(content)

            if not pdf_url:
                pdf_content = self.sanitize_opinion_html_for_pdf(div)
            revision_status =0 #by default for published
            if status=="Unpublished":
                revision_status=0
            elif status=="Unknown":
                revision_status=1

            print("TITLE:", title)
            print(pdf_url)
            # print("CASE NUMBER:", case_number)
            # print("DATE:", decision_date)
            # print("URL:", case_url)

            self.cases.append({
                'name':title,
                'date':date,
                'status':status,
                'url':pdf_url,
                'docket':[case_number],
                "response_html":div,
                "citation":citation,
                "revision_status":revision_status,
                "parallel_citation":[parallel_citation]
            })
            # return

            # print(resp.status_code)

    def download_pdf(self, data, objectId):

        pdf_url = data.get('pdf_url')
        html_url = data.get('html_url')
        response_html = data.get('response_html')

        year = int(data.get('year'))
        court_name = data.get('court_name')
        court_type = data.get('court_type')

        if str(court_type) == 'Federal':
            state_name = data.get('circuit')
        else:
            state_name = data.get('state')

        opinion_type = data.get('opinion_type')

        # Build directory path
        if str(opinion_type) == "Oral Argument":
            path = (
                "/synology/PDFs/US/juriscraper/" + court_type + "/" +
                state_name + "/" +
                court_name + "/" +
                "oral arguments/" +
                str(year)
            )
        else:
            path = (
                "/synology/PDFs/US/juriscraper/" + court_type + "/" +
                state_name + "/" +
                court_name + "/" +
                str(year)
            )

        obj_id = str(objectId)
        download_pdf_path = os.path.join(path, f"{obj_id}.pdf")

        # ----------------------------
        # CASE 1: NO PDF URL → TRY HTML
        # ----------------------------
        if not pdf_url or str(pdf_url).strip() in ["", "null"]:
            pdf_content = self.sanitize_opinion_html_for_pdf(response_html)
            # Convert HTML → PDF using response_html as-is (NO image logic)
            try:
                os.makedirs(path, exist_ok=True)

                html_data = response_html  # No modifications

                config = pdfkit.configuration(
                    wkhtmltopdf="/usr/bin/wkhtmltopdf")

                pdfkit.from_string(
                    pdf_content,
                    download_pdf_path,
                    configuration=config,
                    options={
                        "page-size": "Letter",
                        "encoding": "UTF-8",
                        "quiet": ""
                    }
                )

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )
                return download_pdf_path

            except Exception as e:
                print("HTML → PDF Error:", e)
                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 2}}
                )
                return None

        # -------------------------------------
        # CASE 2: VALID PDF URL → DOWNLOAD PDF
        # -------------------------------------
        i = 0
        while True:
            try:
                os.makedirs(path, exist_ok=True)

                # us_proxy = CasemineUtil.get_us_proxy()

                response = None
                last_exception = None

                for ip, port in self.US_PROXIES:
                    proxy = {
                        "http": f"http://{ip}:{port}",
                        "https": f"http://{ip}:{port}",
                    }

                    try:
                        response = requests.get(
                            url=pdf_url,
                            headers={
                                "User-Agent": (
                                    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) "
                                    "Gecko/20100101 Firefox/136.0"
                                )
                            },
                            proxies=proxy,
                            timeout=120
                        )

                        print(f"Trying {ip}:{port} → {response.status_code}")

                        if response.status_code == 200:
                            break  # ✅ SUCCESS

                    except requests.RequestException as e:
                        print(f"Proxy failed {ip}:{port} → {e}")
                        last_exception = e
                        continue

                # ---- FINAL VALIDATION ----
                if not response or response.status_code != 200:
                    raise RuntimeError(
                        "All proxies exhausted, no 200 response for PDF download"
                    )

                with open(download_pdf_path, 'wb') as file:
                    file.write(response.content)

                self.judgements_collection.update_one(
                    {"_id": objectId},
                    {"$set": {"processed": 0}}
                )
                break

            except requests.RequestException as e:
                # Retry only for proxy failures
                if "Unable to connect to proxy" in str(e):
                    i += 1
                    if i > 10:
                        break
                    continue
                else:
                    print(f"Error while downloading the PDF: {e}")
                    self.judgements_collection.update_one(
                        {"_id": objectId},
                        {"$set": {"processed": 2}}
                    )
                    break

        return download_pdf_path

    def generate_pdf_from_html(self, pdf_content: str, path: str, objectId):
        """
        Generates a PDF from sanitized HTML content and stores it at:
        <path>/<objectId>.pdf

        Args:
            pdf_content (str): Clean HTML content
            path (str): Directory where PDF should be stored
            objectId: MongoDB ObjectId

        Returns:
            str | None: Absolute PDF path if successful, else None
        """
        try:
            if not pdf_content:
                raise ValueError(
                    "Empty HTML content provided for PDF generation")

            os.makedirs(path, exist_ok=True)

            obj_id = str(objectId)
            download_pdf_path = os.path.join(path, f"{obj_id}.pdf")

            config = pdfkit.configuration(
                wkhtmltopdf="/usr/bin/wkhtmltopdf"
            )

            pdfkit.from_string(
                pdf_content,
                download_pdf_path,
                configuration=config,
                options={
                    "page-size": "Letter",
                    "encoding": "UTF-8",
                    "quiet": ""
                }
            )

            return download_pdf_path

        except Exception as e:
            print(f"HTML → PDF generation failed for {objectId}: {e}")
            return None

    def _process_opinion(self, data) -> bool:
        self.flag = False
        obj_id = None
        try:
            duplicate_id = self._fetch_duplicate(data)
            obj_id = self.update_insert_meta(data, duplicate_id)
        except Exception as ex:
            if not str(ex).__eq__("Judgment already Exists!"):
                raise Exception(ex)

        if obj_id is not None:
            content_pdf = self.download_pdf(data, obj_id)
        # flag = saveContent(judId, contentPdf)
        return self.flag

    def update_insert_meta(self, data, existing_id):
        if existing_id is None:
            inserted_doc = self.judgements_collection.insert_one(data)
            object_id = inserted_doc.inserted_id
            self.flag = True
            return object_id
        else:
            self.judgements_collection.update_one({'_id': existing_id}, {'$set': data})
            return existing_id

    def _get_cite_info_html(self):
        return self._get_optional_field_by_id("cite_info_html")

    def _get_revision_status(self):
        return [case.get("revision_status", "") for case in self.cases]

    def sanitize_opinion_html_for_pdf(self, div_html: str) -> str:
        """
        Returns clean, court-style HTML BODY content only.
        No <html>, <head>, or <body> nesting.
        Safe for direct PDF rendering.
        """
        if not div_html:
            return ""

        # Remove OSCN junk markers
        div_html = re.sub(r'BEGIN DOCUMENT', '', div_html, flags=re.I)

        soup = BeautifulSoup(div_html, "lxml")

        # Remove html/head/body if present
        for tag in soup.find_all(["html", "head", "body"]):
            tag.unwrap()

        # Remove scripts and non-printable elements
        for tag in soup(
            ["script", "style", "iframe", "object", "embed", "noscript"]):
            tag.decompose()

        # Remove hyperlinks but keep text
        for a in soup.find_all("a"):
            a.unwrap()

        # Remove raw URLs from visible text
        for node in soup.find_all(string=True):
            cleaned = re.sub(r'https?://\S+', '', node)
            cleaned = re.sub(r'www\.\S+', '', cleaned)
            node.replace_with(cleaned)

        # Strip unwanted attributes
        for tag in soup.find_all(True):
            for attr in ("href", "onclick", "id", "class", "style", "name"):
                tag.attrs.pop(attr, None)

        # Replace <br> with line breaks
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # --- Court-style CSS (INLINE, BODY-SAFE) ---
        css = """
    <style>
    body {
        font-family: "Times New Roman", Georgia, serif;
        font-size: 12pt;
        line-height: 1.6;
        margin: 1.25in 1in;
        color: #000;
    }

    p {
        margin: 0 0 12px 0;
        text-align: justify;
    }

    blockquote {
        margin: 12px 36px;
        font-style: italic;
    }

    hr {
        border: none;
        border-top: 1px solid #000;
        margin: 18px 0;
    }

    center {
        text-align: center;
        margin: 12px 0;
    }

    strong { font-weight: bold; }
    em { font-style: italic; }

    sup {
        font-size: 9pt;
        vertical-align: super;
    }

    .page-break {
        page-break-before: always;
    }
    </style>
    """

        # Return BODY CONTENT ONLY (NO <html><body>)
        return css + str(soup)

    def extract_opinion_html(self, html: str) -> str:
        """
        Extracts ALL OSCN document blocks and concatenates them.
        This handles multi-section opinions correctly.
        """

        blocks = re.findall(
            r"<!--\s*BEGIN DOCUMENT\s*-->(.*?)<!--\s*END DOCUMENT\s*-->",
            html,
            flags=re.I | re.S
        )

        if not blocks:
            raise ValueError("BEGIN/END DOCUMENT markers not found")

        combined_html = "\n".join(blocks)

        soup = BeautifulSoup(combined_html, "lxml")

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        return soup.prettify()

    def make_proxy(self,ip, port):
        proxy_url = f"http://{ip}:{port}"
        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return len(self.cases)

    def detect_publication_status(self,html_content: str) -> str:
        """
        Detects the publication status of an Oklahoma case based on HTML content.

        Args:
            html_content (str): The HTML content of the case page.

        Returns:
            str: One of 'Published', 'Semi-Published', 'Unpublished'.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all <p align="center"> tags
        p_tags = soup.find_all("p", align="center")

        for p in p_tags:
            font = p.find("font", color="#ff0000")
            if font:
                text = font.get_text(strip=True).upper()

                if "NOTICE: THIS OPINION HAS NOT BEEN RELEASED FOR PUBLICATION" in text:
                    return "Unknown"
                elif "FOR PUBLICATION IN OBJ ONLY. NOT FOR OFFICIAL PUBLICATION" in text:
                    return "Unpublished"

        # If neither of the above tags are present, assume Published
        return "Published"

    def get_court_name(self):
        return "Supreme Court of Oklahoma"

    def get_state_name(self):
        return "Oklahoma"

    def get_class_name(self):
        return "okla_new"

    def get_court_type(self):
        return "state"
