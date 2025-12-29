"""Scraper for Colorado Appeals Court
CourtID: coloctapp
Court Short Name: Colo. Ct. App.

History:
    - Ashish 2025 Nov 13
"""

from juriscraper.opinions.united_states.state import colo


class Site(colo.Site):
    api_court_code = "14024_02"
    days_interval = 30
    status = "Unpublished"

    def get_court_name(self):
        return "Court of Appeals of Colorado"

    def get_class_name(self):
            return "coloctapp_u"
