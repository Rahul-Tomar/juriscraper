# Scraper for Florida 6th District Court of Appeal
# CourtID: flaapp6
# Court Short Name: flaapp6

from juriscraper.opinions.united_states.state import fla


# class Site(fladistctapp_1.Site):
#     number = "sixth"
#     court_index = "6"
#
#     def get_class_name(self):
#         return "fladistctapp_6"

class Site(fla.Site):
    # court_index = "1"
    # number = "first"
    fl_court = "sixth_district_court_of_appeal"

    def get_class_name(self):
        return "fladistctapp_6"

    def get_court_name(self):
        return "District Courts of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Florida"
