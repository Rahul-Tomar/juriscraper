"""Scraper for Nevada Supreme Court
CourtID: nev

History:
    - 2023-12-13: Updated by William E. Palin
    - 2026-09-21: Updated for Nevada ACIS API
"""

import json
import re
from datetime import date, datetime
from urllib.parse import urlencode
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Published"
        self.base_url = "https://acis-api.nvcourts.gov/courts/cms/docketentrydocuments"
        self.acis_court_id = "dc01122c-a19d-4eb7-bfe9-5b96e93c26fd"
        self.docket_entry_type_id = "1000014"
        self.page_size = 25
        self.url = self._build_url(0)
        self.filtered_json = []

    def _build_url(self, page: int) -> str:
        return (
            f"{self.base_url}"
            f"?docketEntryHeader.docketEntryTypeID={self.docket_entry_type_id}"
            f"&caseHeader.courtID={self.acis_court_id}"
            f"&page={page}"
            f"&size={self.page_size}"
            f"&sort=docketEntryHeader.filedDate%2Cdesc"
        )

    def _download(self, page: int = 0, **kwargs):
        self.url = self._build_url(page)
        print("URL :", self.url)

        if self.test_mode_enabled():
            return json.load(open(self.url))

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US",
            "Connection": "keep-alive",
            "Host": "acis-api.nvcourts.gov",
            "Origin": "https://acis.nvcourts.gov",
            "Referer": "https://acis.nvcourts.gov/",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }

        response = self.request["session"].get(self.url, headers=headers,proxies=self.proxies)
        response.raise_for_status()
        return response.json()

    def _get_results(self, data):
        if not data:
            return []
        return data.get("_embedded", {}).get("results", [])

    def _parse_filed_date(self, filed_date: str):
        if not filed_date:
            return None

        try:
            parsed_date = datetime.fromisoformat(filed_date.replace("Z", "+00:00"))
            return parsed_date.replace(tzinfo=None)
        except Exception as e:
            print("UNABLE TO PARSE FILED DATE :", filed_date, "| ERROR :", e)
            return None

    def _normalize_date(self, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.replace(tzinfo=None)

        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)

        if isinstance(value, str):
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
                "%m/%d/%Y",
            ]

            for date_format in formats:
                try:
                    return datetime.strptime(value, date_format)
                except ValueError:
                    continue

        return None

    def _get_crawled_till(self):
        crawled_till = getattr(self, "crawled_till", None)
        return self._normalize_date(crawled_till)

    def _extract_citation(self, description: str):
        if not description:
            return []

        match = re.search(r"(\d+)\s+Nev\.\s+Adv\.\s+Opn\.\s+No\.\s+(\d+)", description, re.IGNORECASE)

        if not match:
            return []

        volume = match.group(1)
        advance_number = match.group(2)
        return [f"{volume} Nev., Advance Opinion {advance_number}"]

    def _get_pdf_url(self, case):
        document_uuid = case.get("documentLinkUUID")
        case_header = case.get("caseHeader") or {}
        case_uuid = case_header.get("caseInstanceUUID")

        if not document_uuid or not case_uuid:
            return ""

        return (
            f"https://acis-api.nvcourts.gov"
            f"/courts/{self.acis_court_id}"
            f"/cms/case/{case_uuid}"
            f"/docketentrydocuments/{document_uuid}"
        )

    def filter_cases(self):
        cases = []
        seen_documents = set()

        for case in self.filtered_json:
            document_uuid = case.get("documentLinkUUID")

            if not document_uuid:
                continue

            if document_uuid in seen_documents:
                continue

            case_header = case.get("caseHeader") or {}
            court_abbreviation = case_header.get("courtAbbreviation") or ""

            if court_abbreviation != "Supreme Court":
                continue

            seen_documents.add(document_uuid)
            cases.append(case)

        return cases

    def _process_html(self):
        filtered_cases = self.filter_cases()

        for case in filtered_cases:
            docket_header = case.get("docketEntryHeader") or {}
            case_header = case.get("caseHeader") or {}

            case_number = (case_header.get("caseNumber") or "").strip()
            case_title = (case_header.get("caseTitle") or "").strip()
            filed_date = docket_header.get("filedDate") or ""
            description = docket_header.get("docketEntryDescription") or ""
            parsed_date = self._parse_filed_date(filed_date)

            if parsed_date is None:
                continue

            citation = self._extract_citation(description)
            pdf_url = self._get_pdf_url(case)

            docket = []

            if case_number:
                docket.append(case_number)

            # print("CASE TITLE :", case_title)
            # print("DATE       :", parsed_date.strftime("%Y-%m-%d"))
            # print("CITATION   :", citation)
            # print("PDF URL    :", pdf_url)

            self.cases.append(
                {
                    "citation": citation,
                    "name": case_title,
                    "docket": docket,
                    "date": parsed_date.strftime("%Y-%m-%d"),
                    "url": pdf_url,
                    "status":self.status
                }
            )

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        if not self.downloader_executed:
            self.filtered_json = []

            start_date = self._normalize_date(start_date)
            end_date = self._normalize_date(end_date)
            crawled_till = self._get_crawled_till()
            page = 0
            stop_pagination = False

            while True:
                print("=" * 100)
                print("FETCHING PAGE :", page)

                data = self._download(page=page)
                results = self._get_results(data)

                if not results:
                    print("NO RECORDS FOUND ON PAGE :", page)
                    break

                print("RECORDS FOUND :", len(results))

                for record in results:
                    docket_header = record.get("docketEntryHeader") or {}
                    case_header = record.get("caseHeader") or {}

                    case_number = case_header.get("caseNumber") or ""
                    filed_date_text = docket_header.get("filedDate")
                    filed_date = self._parse_filed_date(filed_date_text)

                    if filed_date is None:
                        continue


                    if crawled_till is not None and filed_date < crawled_till:
                        print("RECORD IS OLDER THAN CRAWLED TILL")
                        print("RECORD DATE :", filed_date)
                        print("CRAWLED TILL:", crawled_till)
                        print("STOPPING PAGINATION")
                        stop_pagination = True
                        break

                    if start_date is not None and filed_date < start_date:
                        print("RECORD IS OLDER THAN START DATE")
                        print("RECORD DATE :", filed_date)
                        print("START DATE  :", start_date)
                        print("STOPPING PAGINATION")
                        stop_pagination = True
                        break

                    if end_date is not None and filed_date > end_date:
                        print("RECORD IS NEWER THAN END DATE - SKIPPING :", filed_date)
                        continue

                    self.filtered_json.append(record)

                if stop_pagination:
                    break

                if len(results) < self.page_size:
                    print("LAST PAGE REACHED :", page)
                    print("RECORDS ON PAGE   :", len(results))
                    break

                page += 1

            print("=" * 100)
            print("TOTAL FILTERED RECORDS :", len(self.filtered_json))

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

        return len(self.cases)

    def get_class_name(self):
        return "nev"

    def get_court_name(self):
        return "Supreme Court of Nevada"

    def get_state_name(self):
        return "Nevada"

    def get_court_type(self):
        return "state"
