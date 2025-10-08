from datetime import datetime

from juriscraper.opinions.united_states.state import nycityct, nytrial


class Site(nycityct.Site):
    court_regex = r"Fam Ct|Family Court|Youth Part"

    def get_class_name(self):
        return "nyfamct"

    def get_court_name(self):
        return "New York Family Court"
