# Scraper for Texas 3rd Court of Appeals
# CourtID: texapp3
# Court Short Name: TX
# Author: Andrei Chelaru
# Reviewer: mlr
# Date: 2014-07-10


from juriscraper.opinions.united_states.state import tex, tex_new


class Site(tex_new.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.court_name = "capp_3"
        self.checkbox = "ctl00$ContentPlaceHolder1$chkListCourts$4"
        self.category = "ctl00$ContentPlaceHolder1$chkListDocTypes$0"

    def get_court_name(self):
        return "Texas Court of Appeals"

    def get_class_name(self):
        return "texapp_3"
