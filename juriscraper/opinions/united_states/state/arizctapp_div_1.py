"""
Author: Deb Linton
Date created: 2014-02-14

Scraper for the Court of Appeals of Arizona, Division 1

CourtID: arizctapp
Court Short Name: Ariz. Ct. App.
"""

from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.court_id = self.__module__

        self.url = (
            "https://www.azcourts.gov/opinions/"
            "SearchOpinionsMemoDecs.aspx?court=998"
        )

        self.base_url = "https://www.azcourts.gov/"

        self.status = "Published"

        proxy_url = (
            self.proxies.get("https")
            or self.proxies.get("http")
        )

        self.playwright_proxy = {
            "server": proxy_url
        } if proxy_url else None

        self.cases = []

        self.stop_crawling = False

        self.browser = None
        self.context = None
        self.page = None

    def _download(self, request_dict=None):
        """
        Load and extract the JavaScript-rendered opinion pages using Playwright.

        This method is automatically called by self.parse().
        """
        self.cases = []
        self.stop_crawling = False

        try:
            self._start_browser()
            self._load_first_page()
            self._process_all_pages()

            # parse() expects _download() to return HTML.
            # Cases are already collected in self.cases.
            return self.page.content()

        finally:
            self._close_browser()

    def crawling_range( self, start_date: datetime, end_date: datetime ) -> int:
        self.parse()
        return 0

    def _start_browser(self):
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.firefox.launch(
            headless=True,
            proxy=self.playwright_proxy
        )

        self.context = self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 "
                "(X11; Ubuntu; Linux x86_64; rv:136.0) "
                "Gecko/20100101 Firefox/136.0"
            ),
            locale="en-US",
            viewport={
                "width": 1366,
                "height": 768
            },
            ignore_https_errors=True
        )

        self.page = self.context.new_page()

    def _load_first_page(self):
        response = self.page.goto(
            self.url,
            wait_until="domcontentloaded",
            timeout=120_000
        )

        if response is None:
            raise RuntimeError(
                "Arizona opinions page returned no browser response."
            )

        # print("Status code:", response.status)
        # print("Final URL:", self.page.url)

        if response.status >= 400:
            raise RuntimeError(
                f"Arizona opinions page returned HTTP {response.status}"
            )

        self._wait_for_opinion_listing()

    def _wait_for_opinion_listing(self):
        """
        Wait for JavaScript to render the opinion list.
        """
        try:
            self.page.wait_for_selector(
                "ul.opinion-listing--list",
                state="attached",
                timeout=60_000
            )

        except PlaywrightTimeoutError:
            html = self.page.content()

            if "opinion-listing" not in html:
                raise RuntimeError(
                    "Opinion listing did not load in the rendered HTML."
                )

    def _process_all_pages(self):
        page_number = 1

        while True:
            # print("=" * 70)
            # print("Processing Arizona opinion page:", page_number)
            # print("URL:", self.page.url)
            # print("=" * 70)

            rendered_html = self.page.content()

            html_url = (f"{self.url}&page={page_number}")

            cases_before_page = len(self.cases)

            self._extract_cases_from_html(
                rendered_html,html_url
            )

            cases_added = (
                len(self.cases) - cases_before_page
            )

            # print(
            #     "Cases added from page "
            #     f"{page_number}: {cases_added}"
            # )

            # print(
            #     "Total cases collected:",
            #     len(self.cases)
            # )

            if self.stop_crawling:
                # print(
                #     "Stored crawled date reached. "
                #     "Stopping pagination."
                # )
                break

            if not self._go_to_next_page():
                # print("No further pagination page found.")
                break

            page_number += 1

    def _extract_cases_from_html(self, html,html_url):
        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        opinion_items = soup.select(
            "ul.opinion-listing--list > li.opinion"
        )

        print(
            "Opinion records found on rendered page:",
            len(opinion_items)
        )

        for opinion in opinion_items:
            time_tag = opinion.select_one(
                "time"
            )

            if time_tag is None:
                print(
                    "Skipping opinion because date is missing."
                )
                continue

            raw_date = (
                time_tag.get("datetime", "").strip()
                or time_tag.get_text(
                    " ",
                    strip=True
                )
            )

            parsed_date = self._parse_date(
                raw_date
            )

            if parsed_date is None:
                print(
                    "Unsupported opinion date:",
                    raw_date
                )
                continue

            compare_date = parsed_date.strftime(
                "%d/%m/%Y"
            )

            case_date = parsed_date.strftime(
                "%B %d, %Y"
            )

            if CasemineUtil.compare_date(
                self.crawled_till,
                compare_date
            ) == 1:
                self.stop_crawling = True
                return

            case_number_tag = opinion.select_one(
                "h4.opinion--case-number a"
            )

            title_tag = opinion.select_one(
                "h3.opinion--title a"
            )

            decision_type_tag = opinion.select_one(
                "span.opinion--decision-type"
            )

            case_number = (
                case_number_tag.get_text(
                    " ",
                    strip=True
                )
                if case_number_tag
                else ""
            )

            case_name = (
                title_tag.get_text(
                    " ",
                    strip=True
                )
                if title_tag
                else ""
            )

            decision_type = (
                decision_type_tag.get_text(
                    " ",
                    strip=True
                )
                if decision_type_tag
                else ""
            )
            if "Memorandum" in decision_type:
                continue

            relative_url = ""

            if title_tag is not None:
                relative_url = title_tag.get(
                    "href",
                    ""
                ).strip()

            if (
                not relative_url
                and case_number_tag is not None
            ):
                relative_url = case_number_tag.get(
                    "href",
                    ""
                ).strip()

            download_url = (
                urljoin(
                    self.base_url,
                    relative_url
                )
                if relative_url
                else ""
            )

            judges = self._extract_judges(
                opinion
            )

            child_cases = self._extract_child_cases(
                opinion
            )

            if not case_name:
                # print(
                #     "Skipping opinion because title is missing:",
                #     case_number
                # )
                continue

            if not download_url:
                # print(
                #     "Skipping opinion because PDF URL is missing:",
                #     case_number,
                #     case_name
                # )
                continue

            self.cases.append({
                "name": case_name,
                "date": case_date,
                "status": self.status,
                "url": download_url,
                "html_url": html_url,
                "judge": judges if judges else [],
                "docket": [case_number] if case_number else []
            })

            print("Added:",case_date,"|",case_number,"|",case_name)

    def _go_to_next_page(self):
        current_item = self.page.locator("ol.paging > li.item__current")

        if current_item.count() == 0:
            # print("Current pagination item not found.")
            return False

        current_text = current_item.first.inner_text().strip()

        try:
            current_page = int(
                current_text.replace(",", "")
            )
        except ValueError:
            # print("Unable to parse current page number:", current_text)
            return False

        next_page = current_page + 1

        # print("Current page:", current_page)
        # print("Looking for next page:", next_page)

        page_buttons = self.page.locator("ol.paging button.paging--link")

        for index in range(page_buttons.count()):
            button = page_buttons.nth(index)

            try:
                button_text = (
                    button.inner_text()
                    .strip()
                    .replace(",", "")
                )

                if not button_text.isdigit():
                    continue

                if int(button_text) != next_page:
                    continue

                if not button.is_visible():
                    continue

                # print("Clicking pagination page:", next_page)

                button.scroll_into_view_if_needed()

                button.click(
                    timeout=30_000
                )

                try:
                    self.page.wait_for_function(
                        """
                        expectedPage => {
                            const current = document.querySelector(
                                "ol.paging > li.item__current"
                            );

                            if (!current) {
                                return false;
                            }

                            const value = current.innerText
                                .trim()
                                .replace(/,/g, "");

                            return Number(value) === expectedPage;
                        }
                        """,
                        arg=next_page,
                        timeout=60_000
                    )

                except PlaywrightTimeoutError:
                    # print(
                    #     "Pagination did not move from page",
                    #     current_page,
                    #     "to page",
                    #     next_page
                    # )
                    return False

                try:
                    self.page.wait_for_selector(
                        "ul.opinion-listing--list > li.opinion",
                        state="attached",
                        timeout=30_000
                    )
                except PlaywrightTimeoutError:
                    # print(
                    #     "Opinion records were not found on page:",
                    #     next_page
                    # )
                    return False

                self.page.wait_for_timeout(1000)

                record_count = self.page.locator(
                    "ul.opinion-listing--list > li.opinion"
                ).count()

                # print("Pagination moved to page:", next_page)
                # print(
                #     "Opinion records available on page",
                #     next_page,
                #     ":",
                #     record_count
                # )

                return True

            except Exception as exc:
                print("Failed to process pagination button:",button_text if "button_text" in locals() else "","|",exc)

        # print("Next page button not found for page:",next_page)

        return False

    def _get_first_case_signature(self):
        locator = self.page.locator( "ul.opinion-listing--list > li.opinion").first

        if locator.count() == 0:
            return ""

        try:
            return locator.evaluate(
                """
                item => {
                    const time = item.querySelector("time");
                    const number = item.querySelector(
                        "h4.opinion--case-number"
                    );

                    return [
                        time ? (
                            time.getAttribute("datetime")
                            || time.innerText
                        ) : "",
                        number ? number.innerText : ""
                    ].join("|").trim();
                }
                """
            )

        except Exception:
            return ""

    def _extract_judges(self, opinion):
        judges = []

        for judge_item in opinion.select(
            "ol.opinion--judges > li.judges--judge"
        ):
            judge_name_tag = judge_item.select_one( "span.judge--display-name")

            if judge_name_tag is None:
                continue

            judge_name = judge_name_tag.get_text(
                " ",
                strip=True
            )

            if judge_name:
                judges.append(judge_name)

        return judges

    def _extract_child_cases(self, opinion):
        child_cases = []

        for child_item in opinion.select(
            "ul.opinion--children > li.children--item"
        ):
            case_number_tag = child_item.select_one(
                "span.child--case-number"
            )

            title_tag = child_item.select_one(
                "span.child--title"
            )

            child_cases.append({
                "case_number": (
                    case_number_tag.get_text(
                        " ",
                        strip=True
                    )
                    if case_number_tag
                    else ""
                ),
                "title": (
                    title_tag.get_text(
                        " ",
                        strip=True
                    )
                    if title_tag
                    else ""
                ),
            })

        return child_cases

    def _parse_date(self, value):
        if not value:
            return None

        value = str(value).strip()

        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%d/%m/%Y",
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(
                    value,
                    date_format
                )
            except ValueError:
                continue

        return None

    def _process_html(self):
        """
        Opinion records are already extracted in _download()
        because the website requires Playwright pagination.
        """
        return

    def _close_browser(self):
        try:
            if self.page is not None:
                self.page.close()
        except Exception:
            pass

        try:
            if self.context is not None:
                self.context.close()
        except Exception:
            pass

        try:
            if self.browser is not None:
                self.browser.close()
        except Exception:
            pass

        try:
            if getattr(
                self,
                "playwright",
                None
            ) is not None:
                self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.context = None
        self.browser = None

    def get_court_name(self):
        return "Arizona Court Of Appeals"

    def get_class_name(self):
        return "arizctapp_div_1"

    def get_state_name(self):
        return "Arizona"

    def get_court_type(self):
        return "state"
