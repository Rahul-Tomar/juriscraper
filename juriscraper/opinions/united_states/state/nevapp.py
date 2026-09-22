"""Scraper for COURT OF APPEALS OF THE STATE OF NEVADA
CourtID: nevapp

History:
    - 2023-12-13: Created by William E. Palin
"""
from typing_extensions import override

from juriscraper.opinions.united_states.state import nev


class Site(nev.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.court_code = "10002"
        self.acis_court_id = "74764f58-a87f-4ec5-8233-7a1255e410b3"
        self.url = self._build_url(0)

    def get_class_name(self):
        return "nevapp"

    @override
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

            if court_abbreviation != "Court of Appeals":
                continue

            seen_documents.add(document_uuid)
            cases.append(case)

        return cases

    def get_court_name(self):
        return "Nevada Court of Appeals"
