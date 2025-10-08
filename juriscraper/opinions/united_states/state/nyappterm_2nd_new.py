from datetime import datetime
from urllib.parse import urljoin

from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.state import ny_new, nyappterm_1st_new


class Site(nyappterm_1st_new.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.court_type = "at_2_idxtable"
        self.CURRENT_URL = self.BASE_URL + f"{self.court_type}.shtml"

    def get_court_name(self):
        return "Supreme Court, Appellate Term, Second Department, New York"

    def get_class_name(self):
        return "nyappterm_2nd_new"