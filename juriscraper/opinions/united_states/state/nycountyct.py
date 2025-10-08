from datetime import datetime

from juriscraper.opinions.united_states.state import nycityct, nytrial


class Site(nycityct.Site):
    court_regex = r"^County|(Co(unty?)? Ct)"

    def get_class_name(self):
        return "nycountyct"

    def get_court_name(self):
        return "New York County Court"
