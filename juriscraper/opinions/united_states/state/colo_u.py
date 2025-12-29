"""Scraper for Colorado Supreme Court


History:
    - 2025 Nov 13 Ashish
"""

from juriscraper.opinions.united_states.state import colo


class Site(colo.Site):
    days_interval = 30
    status = "Unpublished"

    def get_class_name(self):
            return "colo_u"
