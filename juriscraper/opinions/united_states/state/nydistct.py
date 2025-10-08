from datetime import datetime

from juriscraper.opinions.united_states.state import nycityct, nytrial


class Site(nycityct.Site):
    court_regex = r"Dist\.?(ric[tk])? C(our)?t"

    def get_class_name(self):
        return "nydistct"

    def get_court_name(self):
        return "New York District Court"
