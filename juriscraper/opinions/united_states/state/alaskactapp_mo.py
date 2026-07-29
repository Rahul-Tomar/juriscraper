from datetime import date, datetime
from typing import Dict, Tuple
from urllib.parse import urljoin

from lxml import etree
from dateutil import parser
import requests
from requests.exceptions import ChunkedEncodingError

from casemine.casemine_util import CasemineUtil
from juriscraper.AbstractSite import logger
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from juriscraper.lib.html_utils import (get_row_column_links,
                                        get_row_column_text, )
from juriscraper.opinions.united_states.state import alaska, alaskactapp


class Site(alaskactapp.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.url = "https://appellate-records.courts.alaska.gov/CMSPublic/Home/MOJOpinions?isCOA=True"
        self.opinion_type = "minute order"

    def _process_html(self) -> None:
        if not self.html:
            logger.info(
                "HTML was not downloaded from source page. Should retry"
            )
            return

        base_url = "https://appellate-records.courts.alaska.gov"

        publication_blocks = self.html.xpath(
            "//div[contains(concat(' ', normalize-space(@class), ' '), "
            "' fluid-div ')][.//table[contains(@class, 'cms-opinion-table')]]"
        )

        for block in publication_blocks:
            adate_elements = block.xpath(
                ".//h5[@title='Date of Publication' "
                "or @title='Publication Date']/strong"
            )

            if not adate_elements:
                logger.debug(
                    "Publication date not found for an opinion table"
                )
                continue

            adate = adate_elements[0].text_content().strip()

            try:
                parsed_date = datetime.strptime(
                    adate,
                    "%A, %B %d, %Y"
                )
            except ValueError:
                logger.warning(
                    "Unable to parse publication date: %s",
                    adate
                )
                continue

            # Required output:
            # Wednesday, July 22, 2026 -> July 22, 2026
            date = adate.split(",", 1)[1].strip()

            # Skip dates outside the backscrape range.
            if (
                self.is_backscrape
                and not self.date_is_in_backscrape_range(adate)
            ):
                logger.debug(
                    "Backscraper skipping %s",
                    adate
                )
                continue

            curr_date = parsed_date.strftime("%d/%m/%Y")

            if CasemineUtil.compare_date(
                self.crawled_till,
                curr_date
            ) == 1:
                return

            tables = block.xpath(
                ".//table[contains(@class, 'cms-opinion-table')]"
            )

            for table in tables:

                # --------------------------------------------------------------
                # Process tbody rows only.
                # --------------------------------------------------------------
                for row in table.xpath("./tbody/tr"):

                    pdf_links = row.xpath(
                        ".//td[@title='Document Download' "
                        "or @title='Document Dowload']/a/@href"
                    )

                    html_links = row.xpath(
                        ".//td[@title='Case Number and Link to the Case']"
                        "/a/@href"
                    )

                    url = None

                    if pdf_links:
                        pdf_path = pdf_links[0].strip()

                        # Remove malformed quote characters from the new HTML.
                        pdf_path = pdf_path.strip("'\"")

                        if pdf_path:
                            url = urljoin(
                                base_url,
                                pdf_path
                            )

                    elif html_links:
                        # ------------------------------------------------------
                        # No PDF link in the row.
                        # Open the case detail page and locate its PDF.
                        # ------------------------------------------------------
                        html_path = html_links[0].strip().strip("'\"")

                        if html_path:
                            html_url = urljoin(
                                base_url,
                                html_path
                            )

                            retry_flag = True
                            text = None

                            while retry_flag:
                                text = self.hit_retry(html_url)

                                print("\n\t!! HIT AGAIN !!")

                                if str(text) != "HIT AGAIN":
                                    retry_flag = False

                            if text is not None:
                                html_tree = self._make_html_tree(text)

                                pdfs = html_tree.xpath(
                                    "//table[contains(@class, "
                                    "'cms-case-other-table')]"
                                    "//td[@title='Document Download' "
                                    "or @title='Document Dowload']"
                                    "/a/@href"
                                )

                                if pdfs:
                                    pdf_path = (
                                        pdfs[0]
                                        .strip()
                                        .strip("'\"")
                                    )

                                    url = urljoin(
                                        base_url,
                                        pdf_path
                                    )

                                    print(
                                        f"{adate} New-Pdf - {url}\n"
                                    )

                    # ----------------------------------------------------------
                    # Extract docket/case number directly using the td title.
                    # This avoids depending on changing column positions.
                    # ----------------------------------------------------------
                    docket_values = row.xpath(
                        ".//td[@title='Case Number and Link to the Case']"
                        "/a/text()"
                    )

                    if not docket_values:
                        docket_values = row.xpath(
                            ".//td[@title='Case Number and Link to the Case']"
                            "//text()[normalize-space()]"
                        )

                    docs = []

                    for docket_value in docket_values:
                        for docket in docket_value.split(","):
                            docket = docket.strip()

                            if docket:
                                docs.append(docket)

                    title_values = row.xpath(
                        ".//td[@title='Case Title']//text()"
                    )

                    title = " ".join(
                        value.strip()
                        for value in title_values
                        if value.strip()
                    ).strip()

                    if not docs:
                        if self.opinion_type in [
                            "bail orders",
                            "orders"
                        ]:
                            docket_text = str(
                                get_row_column_text(row, 2)
                            )
                        else:
                            docket_text = str(
                                get_row_column_text(row, 3)
                            )

                        docs = [
                            item.strip()
                            for item in docket_text.split(",")
                            if item.strip()
                        ]

                    if not title:
                        if self.opinion_type in [
                            "bail orders",
                            "orders"
                        ]:
                            title = get_row_column_text(
                                row,
                                3
                            ).strip()
                        else:
                            title = get_row_column_text(
                                row,
                                4
                            ).strip()

                    # ----------------------------------------------------------
                    # Extract citation when a citation column exists.
                    # ----------------------------------------------------------
                    citation_values = row.xpath(
                        ".//td[@title='Citation']//text()"
                    )

                    cite = []

                    if citation_values:
                        citation_text = " ".join(
                            value.strip()
                            for value in citation_values
                            if value.strip()
                        )

                        cite = [
                            item.strip()
                            for item in citation_text.split(",")
                            if item.strip()
                        ]

                    elif (
                        self.url == "https://appellate-records.courts.alaska.gov/CMSPublic/Home/Opinions?isCOA=False"
                    ):
                        # Fallback for the older Supreme Court table.
                        citation_text = str(
                            get_row_column_text(row, 5)
                        )

                        cite = [
                            item.strip()
                            for item in citation_text.split(",")
                            if item.strip()
                        ]

                    if not docs:
                        logger.warning(
                            "Skipping row because docket number is missing: %s",
                            title
                        )
                        continue

                    if not title:
                        logger.warning(
                            "Skipping row because case title is missing. "
                            "Docket: %s",
                            docs
                        )
                        continue

                    print(title)

                    self.cases.append(
                        {
                            "date": date,
                            "docket": docs,
                            "name": title,
                            "citation": cite,
                            "url": url,
                            "opinion_type": self.opinion_type,
                        }
                    )

    def get_class_name(self):
        return "alaskactapp_mo"
