from datetime import datetime

from juriscraper.opinions.united_states.state import nycityct, nytrial


class Site(nycityct.Site):
    court_regex = r"Sur{1,}oa?gate|Sur[.r]* Ct"

    def get_class_name(self):
        return "nysurct"

    def get_court_name(self):
        return "New York Surrogate Court"
