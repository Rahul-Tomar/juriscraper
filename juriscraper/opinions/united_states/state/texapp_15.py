# Scraper for Texas 15th Court of Appeals
# CourtID: texapp15
# Court Short Name: TX
# Author:Ashish
# Date: 28 Jan 2026


from juriscraper.opinions.united_states.state import tex_new


class Site(tex_new.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.court_name = "capp_14"
        self.checkbox = "ctl00$ContentPlaceHolder1$chkListCourts$16"
        self.category = "ctl00$ContentPlaceHolder1$chkListDocTypes$0"

    def get_court_name(self):
        return "Texas Court of Appeals"

    def get_class_name(self):
        return "texapp_15"
