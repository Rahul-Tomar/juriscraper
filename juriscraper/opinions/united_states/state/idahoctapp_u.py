from datetime import datetime
from time import strftime

from juriscraper.opinions.united_states.state import idaho_civil

from casemine.casemine_util import CasemineUtil
from juriscraper.lib.exceptions import InsanityException
from juriscraper.lib.string_utils import clean_string, convert_date_string
from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(idaho_civil.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.status = "Unpublished"
        self.court_year = datetime.now().year
        self.url = f"https://isc.idaho.gov/api/cms-content-search?scope=documents&document_type=ICA+Opinion&category=ICA+Unpublished&tag={self.court_year}&sort_by=entry_date&sort_direction=DESC&limit=100"
        self.case_status = "Unpublished"

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.target = start_date.strftime("%d/%m/%Y")
        self.parse()
        return 0

    def get_class_name(self):
        return "idahoctapp_u"

    def get_court_name(self):
        return "Idaho Court of Appeals"

    def get_state_name(self):
        return "Idaho"

    def get_court_type(self):
        return "state"
