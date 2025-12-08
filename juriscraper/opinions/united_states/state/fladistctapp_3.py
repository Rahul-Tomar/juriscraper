# Scraper for Florida 3rd District Court of Appeal Per Curiam
# CourtID: flaapp3
# Court Short Name: flaapp3

from juriscraper.opinions.united_states.state import fla


# class Site(fladistctapp_1.Site):
#     number = "third"
#     court_index = "3"
#
#     def get_class_name(self):
#         return 'fladistctapp_3'

class Site(fla.Site):
    # court_index = "1"
    # number = "first"
    fl_court = "third_district_court_of_appeal"

    def get_class_name(self):
        return "fladistctapp_3"

    def get_court_name(self):
        return "District Courts of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Florida"
