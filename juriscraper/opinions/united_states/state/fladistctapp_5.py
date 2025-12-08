"""
Scraper for Florida 5th District Court of Appeal
CourtID: flaapp5
Court Short Name: flaapp5
Court Contact: 5dca@flcourts.org, 386-947-1530
Author: Andrei Chelaru
Reviewer: mlr
History:
 - 2014-07-23, Andrei Chelaru: Created.
 - 2014-08-05, mlr: Updated.
 - 2014-08-06, mlr: Updated.
 - 2014-09-18, mlr: Updated date parsing code to handle Sept.
 - 2016-03-16, arderyp: Updated to return proper absolute pdf url paths, simplify date logic
"""

from juriscraper.opinions.united_states.state import fla


# class Site(fladistctapp_1.Site):
#     number = "fifth"
#     court_index = "5"
#
#     def get_class_name(self):
#         return "fladistctapp_5"

class Site(fla.Site):
    # court_index = "1"
    # number = "first"
    fl_court = "fifth_district_court_of_appeal"

    def get_class_name(self):
        return "fladistctapp_5"

    def get_court_name(self):
        return "District Courts of Appeal"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Florida"
