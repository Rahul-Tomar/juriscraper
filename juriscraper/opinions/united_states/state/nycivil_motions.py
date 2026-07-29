from juriscraper.opinions.united_states.state import nyappdiv1_motions
from datetime import datetime

class Site(nyappdiv1_motions.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.link_regex = 'mots_coa'
        self.base_url="https://www.nycourts.gov/reporter/current/index/mots_coa_06_2026.shtml"
        # current_date = datetime.now()
        #
        # current_month = current_date.strftime("%m")  # 01,02,...12
        # current_year = current_date.strftime("%Y")  # 2026
        #
        # self.base_url = (
        #     f"https://www.nycourts.gov/reporter/current/index/"
        #     f"mots_coa_{current_month}_{current_year}.shtml"
        # )

    def get_class_name(self):
        return "nycivil_motions"

    def get_court_name(self):
        return "New York Court of Appeals"
