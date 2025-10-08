from juriscraper.opinions.united_states.state import nyappdiv1_motions


class Site(nyappdiv1_motions.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.link_regex = 'mots_ad4_'
        self.base_url="https://nycourts.gov/reporter/motindex/mots_ad4_list.shtml"

    def get_class_name(self):
        return "nyappdiv4_motions"