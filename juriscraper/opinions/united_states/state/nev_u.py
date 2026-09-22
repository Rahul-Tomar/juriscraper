"""Scraper for Nevada Supreme Court
CourtID: nev

History:
    - 2023-12-13: Updated by William E. Palin
"""
from juriscraper.AbstractSite import logger
from juriscraper.opinions.united_states.state import nev

class Site(nev.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Unpublished"
        self.base_url = "https://acis-api.nvcourts.gov/courts/cms/docketentrydocuments"
        self.acis_court_id = "dc01122c-a19d-4eb7-bfe9-5b96e93c26fd"
        self.page_size = 25
        self.url = self._build_url(0)
        self.filtered_json = []

    def _build_url(self, page: int) -> str:
        docket_entry_sub_type_id = "1000018"
        return (
            f"{self.base_url}"
            f"?docketEntryHeader.docketEntryTypeID={docket_entry_sub_type_id}"
            f"&caseHeader.courtID={self.acis_court_id}"
            f"&page={page}"
            f"&size={self.page_size}"
            f"&sort=docketEntryHeader.filedDate%2Cdesc"
        )

    def get_class_name(self):
        return "nev_u"
