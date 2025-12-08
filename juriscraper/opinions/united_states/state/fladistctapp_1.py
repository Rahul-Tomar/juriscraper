"""
Scraper for Florida 1st District Court of Appeals
CourtID: fladistctapp1
"""

from datetime import datetime, timedelta
from urllib.parse import urlencode, urljoin

from PIL.ImImagePlugin import number

from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import titlecase
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from juriscraper.opinions.united_states.state import fla


class Site(fla.Site):
    # court_index = "1"
    # number = "first"
    fl_court = "first_district_court_of_appeal"

    def get_class_name(self):
        return "fladistctapp_1"

    def get_court_name(self):
        return "District Courts of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Florida"





