from juriscraper.OpinionSiteLinear import OpinionSiteLinear
from juriscraper.opinions.united_states.state import md


class Site(md.Site):
    base_url = "https://www.mdcourts.gov/cgi-bin/indexlist.pl?court={}&year={}&order=bydate&submit=Submit"
    court = "coa"
    start_year = 2026
    current_year = None
    empty_cite_strings = {"slip.op.", "."}
    no_judge_strings = {"Order", "PC Order", "Per Curiam"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_class_name(self):
        return "md_supreme"

    def get_court_name(self):
        return "Supreme Court of Maryland"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Maryland"


