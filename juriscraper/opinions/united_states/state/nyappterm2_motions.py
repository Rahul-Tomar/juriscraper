from juriscraper.opinions.united_states.state import nyappdiv1_motions


class Site(nyappdiv1_motions.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.link_regex = 'mots_at2'
        self.base_url="https://nycourts.gov/reporter/motindex/mots_at2_list.shtml"

    def get_class_name(self):
        return "nyappterm2_motions"

    def get_court_name(self):
        return "Supreme Court, Appellate Term, Second Department, New York"