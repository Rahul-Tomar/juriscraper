from datetime import datetime

from lxml import html
import requests
from typing_extensions import override
import os
from playwright.sync_api import sync_playwright

from juriscraper.OpinionSiteLinear import OpinionSiteLinear

class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.current_year = None

    @override
    def _request_url_get(self, url):
        self.request["response"] = requests.get(
            url=url,
            proxies=self.proxies,
            timeout=60,
        )

    def _process_html(self):

        sections = self.html.xpath(
            '//section[contains(@class,"ma__stacked-row__section")]')

        for section in sections:

            # Extract month header: <h2 class="ma__comp-heading">
            head_month = section.xpath(
                './/h2[contains(@class,"ma__comp-heading")]/text()')
            if not head_month:
                continue

            head_month = head_month[0].strip()

            # Skip months with "No Decisions"
            if "No Decisions" in head_month or "No decisions" in head_month:
                continue

            # Main content (contains listing)
            main_content = section.xpath(
                ".//div[contains(@class,'main-content')]")
            if not main_content:
                continue

            main_content = main_content[0]

            # All case entries
            links = main_content.xpath(
                ".//div[contains(@class,'ma__download-link')]")

            for link in links:

                # Extract the link to the case detail page
                href = link.xpath(
                    ".//a[contains(@class,'js-clickable-link')]/@href")
                if not href:
                    continue

                href = href[0]

                # Always convert to absolute URL
                if not href.startswith("https://www.mass.gov"):
                    href = "https://www.mass.gov" + href

                # Load inner page
                response = requests.get(url=href, proxies=self.proxies,
                                        timeout=60)
                inner_html = self._make_html_tree(response.text)

                # Extract title
                title_text = inner_html.xpath(
                    '//h1[@class="ma__page-header__title"]/text()')
                title = ' '.join(t.strip() for t in title_text if t.strip())

                # Extract date
                date_text = inner_html.xpath(
                    '//tr[th[text()="Date:"]]/td/span/text()')
                date = date_text[0].strip() if date_text else ''

                # Extract docket
                doc_text = inner_html.xpath(
                    '//tr[th[text()="Docket Number:"]]/td/span/text()')
                doc = doc_text[0].strip() if doc_text else ''
                docket_list = [
                    item.strip()
                    for item in str(doc)
                    .replace(":", "")
                    .replace("DIA No.", "")
                    .replace("DIA Board No.", "")
                    .replace("DIA Board Nos.", "")
                    .split(',')
                    if item.strip()
                ]

                # Extract judge
                judge_name = inner_html.xpath(
                    '//div[contains(@class, "ma__rich-text")]//p/strong//text()')
                judge_name = ''.join(judge_name).strip() if judge_name else ''

                # Extract PDF URL
                pdf_url = inner_html.xpath(
                    '//a[contains(@class, "ma__download-link__file-link")]/@href')
                pdf_url = pdf_url[0] if pdf_url else ''

                # Force the expected pattern: https://www.mass.gov/doc/<slug>/download
                if pdf_url and not pdf_url.startswith("https://www.mass.gov"):
                    pdf_url = "https://www.mass.gov" + pdf_url

                # Append the case
                self.cases.append({
                    "name": title,
                    "date": date,
                    "docket": docket_list,
                    "judge": [judge_name],
                    "url": pdf_url
                })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        for year in range(start_date.year, end_date.year+1):
            self.url=f'https://www.mass.gov/lists/{year}-dia-reviewing-board-decisions'
            self.parse()
            self.downloader_executed=False
        return 0

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
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    proxy_config = {
                        "server": "http://23.236.197.227:8800"  # fixed proxy
                    }
                    with sync_playwright() as p:
                        browser = p.firefox.launch(headless=True,proxy=proxy_config)
                        page = browser.new_page()
                        with page.expect_download() as download_info:
                            # Use evaluate to simulate a browser click for direct download
                            page.evaluate(f'''
                                () => {{
                                    const a = document.createElement("a");
                                    a.href = "{pdf_url}";
                                    a.download = "";
                                    document.body.appendChild(a);
                                    a.click();
                                    a.remove();
                                }}
                            ''')
                        download = download_info.value
                        download.save_as(download_pdf_path)
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

    def get_class_name(self):
        return "mass_dia"

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return "Massachusetts"

    def get_court_name(self):
        return "Massachusetts Department of Industrial Accidents"
