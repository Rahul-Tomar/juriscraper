"""Scraper for Supreme Court of Northern Mariana Islands
CourtID: nmi
Court Short Name: NMI
Author: William Edward Palin
History:
  2023-01-21: Created by William Palin
  2026-09-18: Updated for new cnmilaw.gov website structure
"""

import re
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urljoin

from juriscraper.lib.string_utils import normalize_dashes
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    court = "Supreme"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        year = datetime.now().year
        self.url = self._build_url(year)

    def _build_url(self, year: int) -> str:
        return (
            "https://cnmilaw.gov/documents"
            f"?type=case&court={self.court}&year={year}"
        )

    def _cleanup_judge_names(self, judges: str) -> List[str]:
        if not judges:
            return []

        judges = re.sub(r",\s*Jr\.", " Jr.", judges)

        cleaned_judges = []

        for judge in judges.split(","):
            judge = judge.strip()
            judge = judge.strip("*").strip()

            if judge:
                cleaned_judges.append(judge)

        return cleaned_judges

    def _fetch_author(self, judges: str) -> str:
        if not judges:
            return "Per Curiam"

        if "*" not in judges:
            return "Per Curiam"

        normalized_judges = re.sub(r",\s*Jr\.", " Jr.", judges)

        for judge in normalized_judges.split(","):
            if "*" in judge:
                return judge.strip().strip("*").strip()

        return "Per Curiam"

    def _process_html(self):
        rows = self.html.xpath(
            "//table[contains(@class, 'doctable')]//tbody/tr"
        )

        for row in rows:
            cells = row.xpath("./td")

            if len(cells) < 5:
                continue

            name = cells[0].text_content().strip()
            citation_text = cells[1].text_content().strip()

            case_date = cells[2].get("data-sort")

            if not case_date:
                case_date = cells[2].text_content().strip()

            judge_text = cells[3].text_content().strip()

            pdf_links = cells[4].xpath(
                ".//a[contains(@class, 'pdf-link')]/@href"
            )

            if not pdf_links:
                pdf_links = cells[4].xpath(
                    ".//a[contains("
                    "translate(@href, "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                    "'abcdefghijklmnopqrstuvwxyz'), "
                    "'.pdf')]/@href"
                )

            if not pdf_links:
                continue

            pdf_url = pdf_links[0].strip()

            if not pdf_url:
                continue

            pdf_url = urljoin(
                "https://cnmilaw.gov",
                pdf_url
            )

            citation = []

            if citation_text:
                citation = [citation_text]

            self.cases.append(
                {
                    "name": name,
                    "citation": citation,
                    "date": case_date,
                    "judge": self._cleanup_judge_names(judge_text),
                    "author": self._fetch_author(judge_text),
                    "url": pdf_url,
                    "docket": [],
                }
            )

    def extract_from_text(self, scraped_text: str) -> Dict[str, Any]:
        normalized_content = normalize_dashes(scraped_text)

        match = re.search(
            r"Case\s+No\.?\s*:?\s*([A-Z0-9][A-Z0-9\-–—. ]+)",
            normalized_content,
            re.IGNORECASE,
        )

        docket_number = ""

        if match:
            docket_number = match.group(1).strip()

        metadata = {
            "Docket": {
                "docket_number": docket_number,
            },
        }

        return metadata

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        for year in range(start_date.year, end_date.year + 1):
            self.parse()
            self.downloader_executed = False

        return 0

    def get_court_name(self):
        return "Supreme Court of Northern Mariana Islands"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Northern Mariana Islands"

    def get_class_name(self):
        return "nmariana"
