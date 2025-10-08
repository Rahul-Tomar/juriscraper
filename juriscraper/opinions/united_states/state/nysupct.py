from datetime import datetime

from juriscraper.opinions.united_states.state import nycityct, nytrial


class Site(nycityct.Site):
    court_regex = r"Sup[rt]?\.? ?[Cc]o?u?r?t?|[sS]ur?pu?rem?e? C(our)?t|Sur?pe?r?me?|Suoreme|Sup County|Integrated Domestic Violence|Soho Fashions LTD"

    def get_class_name(self):
        return "nysupct"

    def get_court_name(self):
        return "New York Supreme Court"
