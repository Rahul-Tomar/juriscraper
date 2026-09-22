"""Scraper for Nevada Supreme Court
CourtID: nev

History:
    - 2023-12-13: Updated by William E. Palin
"""
from juriscraper.AbstractSite import logger
from juriscraper.opinions.united_states.state import nev, nevapp


class Site(nevapp.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.court_code = "10002"
        self.status = "Unpublished"
        self.acis_court_id = "74764f58-a87f-4ec5-8233-7a1255e410b3"
        self.docket_entry_type_id = "1000018"
        self.url = self._build_url(0)



    def get_class_name(self):
        return "nevapp_u"
