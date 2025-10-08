from datetime import datetime

from juriscraper.opinions.united_states.state import nycityct, nytrial


class Site(nycityct.Site):
    court_regex = r"(Just|Village|Town) Ct|Just(ice)? Cour+t"

    def get_class_name(self):
        return "nyjustct"

    def get_court_name(self):
        return "New York Justice Court"
