# Scraper for Florida 4th District Court of Appeal Per Curiam
# CourtID: flaapp4
# Court Short Name: flaapp4

from juriscraper.opinions.united_states.state import fla


# class Site(fladistctapp_1.Site):
#     number = "fourth"
#     court_index = "4"
#
#     def get_class_name(self):
#         return "fladistctapp_4"

class Site(fla.Site):
    # court_index = "1"
    # number = "first"
    fl_court = "fourth_district_court_of_appeal"

    def get_class_name(self):
        return "fladistctapp_4"

    def get_court_name(self):
        return "District Courts of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Florida"
