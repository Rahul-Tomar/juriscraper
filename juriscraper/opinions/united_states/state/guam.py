"""Scraper for Supreme Court of Guam
CourtID: guam
Court Short Name: Guam
Author: mmantel
History:
  2019-12-09: Created by mmantel
  2024-01-25: updated by grossir
"""

import re
from datetime import date, datetime
from typing import Optional
from lxml import html as LH
from dateutil import parser
from dateutil.parser import ParserError

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"  # The year dropdown goes back to 1990, but the Court wasn't  # created until 1996 and there are no opinions posted for  # prior years.  # self.back_scrape_iterable = range(1996, self._year)

    def _process_html(self) -> None:
        """Process HTML into case objects

        Some docket numbers are a consolidation of other dockets
        For example: "CVA12-018 (consolidated with CVA12-030)"
        Deleting the date and citation from the free text allows us
        to catch these names

        :return: None
        """
        opinion_xpath = '//h3[contains(text(),"Latest Opinions")]/parent::div/following-sibling::p'

        for section in self.html.xpath(opinion_xpath):

            links = section.xpath(".//a")

            for link in links:

                try:
                    name = "".join(link.xpath(".//text()")).strip()

                    pdf_url = link.xpath("./@href")[0].strip()

                    if not pdf_url.startswith("https://guamcourts.gov/"):
                        pdf_url = "https://guamcourts.gov/" + pdf_url.lstrip(
                            "/")

                    # Tail contains:
                    # ", 2026 Guam 3, CVA24-012, May 7, 2026."

                    tail_text = (link.tail or "").strip()
                    combined_text = f"{name} {tail_text}"

                    citation = ""
                    citation_match = re.search(
                        r"\d{4}\s*Guam\s*\d+",
                        combined_text
                    )

                    if citation_match:
                        citation = citation_match.group(0).strip()

                    docket = ""

                    docket_match = re.search(
                        r"\b[A-Z]{2,5}\d{2}-\d{3}\b",
                        combined_text
                    )

                    if docket_match:
                        docket = docket_match.group(0)

                    row_date = self.find_date(combined_text)
                    curr_date = datetime.strptime(row_date, "%B %d, %Y").strftime("%d/%m/%Y")
                    res = CasemineUtil.compare_date(self.crawled_till,
                                                    curr_date)
                    if res == 1:
                        return

                    self.cases.append({
                        "url": pdf_url,
                        "name": name,
                        "docket": [docket] if docket else [],
                        "date": row_date ,
                        "date_filed_is_approximate": row_date is None,
                        "citation": [citation] if citation else [],
                    })

                    # print("Added:", name)

                except Exception as e:
                    print("Error parsing opinion:", str(e))

    def find_date(self, text: str) -> Optional[str]:
        """Find dates on text, and validate that they are indeed dates
        Sometimes the regex will pick a part of the string that is not a date

        :param text: free text with docket, date and citation info in varying order
        :return: validated date or None
        """
        # Seen formats: "12-28-2023", "October 11, 2023", "Nov. 29, 2023"
        date_pattern = r"([JFMASONDa-z.]+|\d{1,4})[\s-]+\d{1,2}[,\s-]+\d{2,4}"
        for date_match in re.finditer(date_pattern, text):
            try:
                parser.parse(date_match.group())
                return date_match.group()
            except ParserError:
                pass

    def _download_backwards(self, year: int) -> None:
        """Sets up the download of past records

        :param year: search filter for the page
        :return: None
        """
        self._year = year - 1
        if self._year < datetime.now().year:
            # legacy URL for old opinions
            self.url = f"https://guamcourts.gov/legacydata/supreme-court-opinions?action=get_items&type=SPRMOP&year={self._year}"
            self.html = self._download()
            if isinstance(self.html, str):
                tree = LH.fromstring(self.html)
            elif isinstance(self.html, LH.HtmlElement):
                tree = self.html  # already parsed
            else:
                raise TypeError(f"Unexpected type for self.html: {type(self.html)}")
            opinion_items = tree.xpath('//div[@class="item_for_list"]')
            cutoff_date = datetime(2026, 1, 5)
            for item in opinion_items:

                # Posted date
                posted_text = item.xpath('.//div/text()')[0].strip()  # "Posted: 1/5/2026"
                posted_date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})',
                                              posted_text)
                posted_date = None
                if posted_date_match:
                    posted_date = datetime.strptime(posted_date_match.group(1),"%m/%d/%Y")
                if posted_date and posted_date < cutoff_date:
                    continue
                # Case name
                name = item.xpath('.//h4/a/text()')[0].strip()

                # PDF URL
                pdf_url = item.xpath('.//h4/a/@href')[0].strip()
                if not pdf_url.startswith("https://guamcourts.gov/"):
                    pdf_url = "https://guamcourts.gov/" + pdf_url.lstrip("/")

                # Citation, docket, and case date from the <p>
                p_text = item.xpath('.//p/text()')[0].strip()
                citation_match = re.search(r'\d{4}\s*Guam\s*\d+', p_text)
                citation = citation_match.group(0) if citation_match else ""

                docket_match = re.search(r'[A-Z]{2,5}\d{2}-\d{3}', p_text)
                docket = docket_match.group(0) if docket_match else ""

                date_match = re.search(r'(\w+\s+\d{1,2},\s+\d{4})', p_text)
                case_date = datetime.strptime(date_match.group(1),"%B %d, %Y")

                self.cases.append({
                    "url": pdf_url,
                    "name": name,
                    "docket": [docket] if docket else [],
                    "date": case_date,
                    "date_filed_is_approximate": case_date is None,
                    "citation": [citation] if citation else [],
                })
        else:
            # current year URL uses the new structure
            self.url = "https://guamcourts.gov/courts-council/supreme-court/opinions"

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        # OLd url by deepak
        # self.url = "https://guamcourts.org/Supreme-Court-Opinions/Supreme-Court-Opinions.asp"

        self.url = "https://guamcourts.gov/courts-council/supreme-court/opinions"
        self.parse()
        self._year = datetime.now().year
        self._download_backwards(self._year)
        self.downloader_executed = False
        return len(self.cases)

    def get_class_name(self):
        return "guam"

    def get_state_name(self):
        return "Guam"

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court of Guam"
