# Scraper for Louisiana Supreme Court
# CourtID: la
# Court Short Name: LA
# Contact: Community relations department
#          Robert Gunn
#          504-310-2592
#          rgunn@lasc.org

import datetime
import os
import re
from datetime import date
from urllib.parse import urljoin

from lxml import html as lxml_html
from playwright.sync_api import sync_playwright

from juriscraper.lib.html_utils import get_html_parsed_text
from juriscraper.lib.string_utils import titlecase
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.court_id = self.__module__
        self.year = date.today().year

        # New LASC page is Blazor-rendered.
        self.url = "https://www.lasc.org/Opinions"

        self.status = "Published"
        self.base_url = "https://www.lasc.org"

        # Playwright profile
        self.profile_dir = "/home/gaugedata/Downloads/playwright_lasc_profile"
        self.headless = True
        self.start_date = None
        self.end_date = None

    def _download(self, request_dict={}):
        """
        New LASC site is Blazor Server.

        Flow:
        1. Render main opinions page with Playwright.
        2. Extract date links:
           /opinions?p=2026-030
        3. Open only those date pages where:
           start_date <= opinion_date <= end_date
        4. Return parsed rendered HTML pages.
        """
        rendered_pages = []

        proxy_config, firefox_proxy_prefs = self._get_playwright_proxy_config()

        with sync_playwright() as p:
            launch_args = {
                "user_data_dir": self.profile_dir,
                "headless": self.headless,
                "viewport": {"width": 1400, "height": 900},
                "locale": "en-US",
                "timezone_id": "America/Los_Angeles",
                "ignore_https_errors": True,
            }

            if proxy_config:
                launch_args["proxy"] = proxy_config

            if firefox_proxy_prefs:
                launch_args["firefox_user_prefs"] = firefox_proxy_prefs

            context = p.firefox.launch_persistent_context(**launch_args)
            page = context.new_page()

            print("Opening main page:", self.url)
            page.goto(self.url, wait_until="domcontentloaded", timeout=90000)

            self._wait_for_blazor_date_links(page)

            main_html = page.content()
            date_links = self._extract_opinion_date_links(main_html, page.url)

            # print("Total opinion date links:", len(date_links))
            for index, item in enumerate(date_links, start=1):
                date_text = item["date"]
                opinion_date = item["date_obj"]
                url = item["url"]

                if not self._date_allowed(opinion_date):
                    print("Skipping date page:", date_text, url)
                    continue

                # print("Opening opinion date page:", date_text, url)

                page.goto(url, wait_until="domcontentloaded", timeout=90000)

                # Wait for Blazor detail page render.
                page.wait_for_timeout(10000)

                detail_html = page.content()

                parsed_page = self._get_subpage_html_by_rendered_html(detail_html)

                parsed_page.attrib["data-lasc-date"] = date_text
                parsed_page.attrib["data-lasc-date-iso"] = opinion_date.isoformat()
                parsed_page.attrib["data-lasc-url"] = url

                rendered_pages.append(parsed_page)

            context.close()

        return rendered_pages

    def _process_html(self):
        for h in self.html:
            date_text = h.attrib.get("data-lasc-date", "")

            rows = h.xpath(".//div[contains(@class, 'nrbody')]//p")

            if not rows:
                rows = h.xpath(".//p | .//div[contains(@class, 'col-12')]")

            for row in rows:
                row_text = self._clean_text(row.text_content())

                if not row_text:
                    continue

                date_span = row.xpath(".//span[contains(@class, 'nrdate')]")

                if date_span:
                    parsed_date = self._parse_old_nrdate(
                        date_span[0].text_content()
                    )

                    if parsed_date:
                        date_text = parsed_date

                    continue

                anchors = row.xpath(
                    ".//a["
                    "contains(translate(., 'abcdefghijklmnopqrstuvwxyz', "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), ' V. ') or "
                    "contains(translate(., 'abcdefghijklmnopqrstuvwxyz', "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), ' IN RE ') or "
                    "starts-with(translate(normalize-space(.), "
                    "'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), "
                    "'IN RE') or "
                    "starts-with(translate(normalize-space(.), "
                    "'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), "
                    "'IN THE') or "
                    "contains(translate(., 'abcdefghijklmnopqrstuvwxyz', "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), ' VS. ')"
                    "]"
                )

                for anchor in anchors:
                    anchor_text = self._clean_text(anchor.text_content())

                    if not anchor_text:
                        continue

                    parts = anchor_text.split(None, 1)

                    if len(parts) < 2:
                        continue

                    docket = parts[0].strip()
                    case_name = parts[1].strip()

                    if not docket or not case_name:
                        continue

                    href = anchor.get("href")

                    if not href:
                        continue

                    url = urljoin(self.base_url, href)

                    judges = []
                    judge = self._get_judge_above_anchor(anchor)

                    if judge:
                        judges.append(judge)

                    raw_summary_text = self._get_summary_for_anchor(
                        anchor,
                        anchor_text,
                    )
                    disposition, summary = self._split_disposition_and_summary(
                        raw_summary_text
                    )

                    self.cases.append(
                        {
                            "docket": [docket],
                            "judge": judges,
                            "name": titlecase(case_name),
                            "date": date_text,
                            "disposition": disposition,
                            "url": url,
                            "status":self.status
                        }
                    )

    def _split_disposition_and_summary(self, text):
        """
        Example:
            AFFIRMED. SEE OPINION.

        disposition:
            AFFIRMED.

        summary:
            SEE OPINION.

        Example:
            JUDGMENT OF THE COURT OF APPEAL REVERSED.
            DEFENDANT'S CONVICTION AND SENTENCE REINSTATED.
            SEE OPINION.
            Griffin, J., dissents and assigns reasons.

        disposition:
            JUDGMENT OF THE COURT OF APPEAL REVERSED.
            DEFENDANT'S CONVICTION AND SENTENCE REINSTATED.

        summary:
            SEE OPINION. Griffin, J., dissents and assigns reasons.
        """

        text = self._clean_text(text)

        if not text:
            return "", ""

        text = self._normalize_opinion_text(text)

        disposition = ""
        summary = ""

        match = re.search(r"\bSEE\s+OPINION\.?", text, flags=re.I)

        if match:
            disposition = text[: match.start()]
            summary = text[match.start() :]
        else:
            # If no SEE OPINION exists, keep first result-like sentence
            # as disposition.
            disposition = text
            summary = ""

        disposition = self._clean_disposition(disposition)
        summary = self._clean_summary(summary)

        return disposition, summary

    def _normalize_opinion_text(self, text):
        text = self._clean_text(text)

        if not text:
            return ""

        # Ensure "SEE OPINION." is separated cleanly.
        text = re.sub(r"\bSEE\s+OPINION\.?", "SEE OPINION.", text, flags=re.I)

        # Remove duplicate periods/spaces.
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\.\s*\.", ".", text)

        return text.strip()

    def _clean_disposition(self, text):
        text = self._clean_text(text)

        if not text:
            return ""

        text = re.sub(r"\bSEE\s+OPINION\.?", "", text, flags=re.I)
        text = self._clean_text(text)

        if text and not text.endswith("."):
            text += "."

        return text

    def _clean_summary(self, text):
        text = self._clean_text(text)

        if not text:
            return ""

        text = re.sub(r"\bSEE\s+OPINION\.?", "SEE OPINION.", text, flags=re.I)
        text = self._clean_text(text)

        return text

    def _get_playwright_proxy_config(self):
        """
        Use proxy directly from parent AbstractSite:
            self.proxies = {
                "http": "http://23.236.154.202:8800",
                "https": "http://23.236.154.202:8800"
            }

        No hardcoded proxy here.
        """

        proxy_url = None

        if hasattr(self, "proxies") and self.proxies:
            proxy_url = self.proxies.get("https") or self.proxies.get("http")

        if not proxy_url:
            return None, None

        parsed = re.match(
            r"^(?P<scheme>https?|socks5)://(?P<host>[^:/]+):(?P<port>\d+)$",
            proxy_url,
        )

        if not parsed:
            return {"server": proxy_url}, None

        scheme = parsed.group("scheme")
        host = parsed.group("host")
        port = int(parsed.group("port"))

        proxy_config = {
            "server": f"{scheme}://{host}:{port}",
        }

        firefox_proxy_prefs = {
            "network.proxy.type": 1,
            "network.proxy.http": host,
            "network.proxy.http_port": port,
            "network.proxy.ssl": host,
            "network.proxy.ssl_port": port,
            "network.proxy.no_proxies_on": "",
        }

        return proxy_config, firefox_proxy_prefs

    def _date_allowed(self, opinion_date):
        """
        Open date page only when date is inside crawling range.

        Example:
            last crawled/start date = June 1, 2026
            page date = June 29, 2026

        Since June 1 <= June 29, open it.
        """

        if not opinion_date:
            return True

        if self.start_date and opinion_date < self.start_date:
            return False

        if self.end_date and opinion_date > self.end_date:
            return False

        return True

    def _wait_for_blazor_date_links(self, page):
        try:
            page.wait_for_selector(
                'a[href*="opinions?p="], a[href*="Opinions?p="]',
                timeout=30000,
            )
        except Exception:
            page.wait_for_timeout(10000)

    def _extract_opinion_date_links(self, html, current_url):
        page = lxml_html.fromstring(html)

        links = []
        seen = set()

        anchors = page.xpath(
            ".//a[contains(@href, 'opinions?p=') or "
            "contains(@href, 'Opinions?p=')]"
        )

        for anchor in anchors:
            date_text = self._clean_text(anchor.text_content())
            href = anchor.get("href")

            if not date_text or not href:
                continue

            date_obj = self._parse_listing_date(date_text)

            if not date_obj:
                continue

            full_url = urljoin(current_url, href)
            key = (date_text, full_url)

            if key in seen:
                continue

            seen.add(key)

            links.append(
                {
                    "date": date_text,
                    "date_obj": date_obj,
                    "url": full_url,
                }
            )

        return links

    def _parse_listing_date(self, text):
        """
        Parses listing dates like:
            June 29, 2026
            March 6, 2026
        """

        text = self._clean_text(text)

        if not text:
            return None

        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                pass

        return None

    def _get_subpage_html_by_rendered_html(self, rendered_html):
        page = lxml_html.fromstring(rendered_html)

        textarea = page.xpath(".//textarea[@id='PostContent']")

        if textarea:
            html = textarea[0].text_content()
            return get_html_parsed_text(html)

        return page

    def _get_subpage_html_by_url(self, url):
        page = self._get_html_tree_by_url(url)
        return self._get_subpage_html_by_page(page)

    def _get_subpage_html_by_page(self, page):
        path = ".//textarea[@id='PostContent']"
        textarea = page.xpath(path)

        if textarea:
            html = textarea[0].text_content()
            return get_html_parsed_text(html)

        return page

    def _get_date_for_opinions(self, h):
        element_date = h.xpath("//span")[0]
        element_date_text = element_date.text_content().strip()

        return self._parse_old_nrdate(element_date_text)

    def _parse_old_nrdate(self, text):
        text = self._clean_text(text)

        if not text:
            return ""

        if "day of" not in text:
            return ""

        try:
            parts = text.split("day of")
            day = parts[0].split()[-1]
            day = re.sub(r"(st|nd|rd|th)$", "", day, flags=re.I)

            month = parts[1].split()[0]
            year = parts[1].split()[1].strip(",")

            return " ".join([month, day, year])
        except Exception:
            return ""

    def _get_judge_above_anchor(self, anchor):
        path = (
            "./preceding::*["
            "starts-with(normalize-space(.), 'BY ') or "
            "contains(normalize-space(.), 'CURIAM:')"
            "]"
        )

        try:
            text = anchor.xpath(path)[-1].text_content()
        except IndexError:
            return None

        text = self._clean_text(text)

        if "PER CURIAM" in text:
            return None

        return text.rstrip(":").replace("BY ", "", 1).strip()

    def _get_summary_for_anchor(self, anchor, anchor_text):
        parent = anchor.getparent()

        if parent is None:
            return ""

        summary_text = self._clean_text(parent.text_content())

        # Remove docket + case name anchor text
        summary_text = summary_text.replace(anchor_text, "")

        # Remove parish metadata like:
        # (Parish of Ouachita)
        # (Parish of East Baton Rouge)
        # (Parish of St. Tammany)
        summary_text = re.sub(
            r"\(\s*Parish\s+of\s+[^)]+\)",
            "",
            summary_text,
            flags=re.I,
        )

        return self._clean_text(summary_text)

    def _clean_text(self, text):
        if text is None:
            return ""

        text = str(text)
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _safe_filename(self, text):
        text = str(text or "").strip()
        text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
        text = text.strip("_")

        return text or "page"

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        """
        Only crawl pages where:
            start_date <= opinion listing date <= end_date

        start_date is your last crawled date / lower boundary.
        """

        if isinstance(start_date, datetime.datetime):
            self.start_date = start_date.date()
        else:
            self.start_date = start_date

        if isinstance(end_date, datetime.datetime):
            self.end_date = end_date.date()
        else:
            self.end_date = end_date

        if not self.downloader_executed:
            self.html = self._download()
            self.downloader_executed = True
            self._process_html()

        for attr in self._all_attrs:
            self.__setattr__(attr, getattr(self, f"_get_{attr}")())

        self._clean_attributes()

        if "case_name_shorts" in self._all_attrs:
            self.case_name_shorts = self._get_case_name_shorts()

        self._post_parse()
        self._check_sanity()
        self._date_sort()
        self._make_hash()

        return 0

    def get_class_name(self):
        return "la"

    def get_court_name(self):
        return "Supreme Court of Louisiana"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Louisiana"
