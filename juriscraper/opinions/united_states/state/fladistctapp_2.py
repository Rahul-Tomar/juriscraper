# Scraper for Florida 2nd District Court of Appeal Per Curiam
# CourtID: flaapp2
# Court Short Name: flaapp2

from juriscraper.opinions.united_states.state import fla


# class Site(fladistctapp_1.Site):
#     number = "second"
#     court_index = "2"
#
#     def get_class_name(self):
#         return 'fladistctapp_2'

class Site(fla.Site):
    # court_index = "1"
    # number = "first"
    fl_court = "second_district_court_of_appeal"

    def get_class_name(self):
        return "fladistctapp_2"

    def get_court_name(self):
        return "District Courts of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Florida"
