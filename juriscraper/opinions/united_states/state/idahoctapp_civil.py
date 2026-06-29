from datetime import datetime

from juriscraper.opinions.united_states.state import idaho_civil


class Site(idaho_civil.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_code = "ICa+Civil"
        self.court_key = "ICA"
        self.court_year = datetime.now().year
        self.url = f"https://isc.idaho.gov/api/cms-content-search?scope=documents&document_type={self.court_key}+Opinion&category={self.court_code}&tag={self.court_year}&sort_by=entry_date&sort_direction=DESC&limit=100"
        self.court_id = self.__module__

    def get_class_name(self):
        return "idahoctapp_civil"

    def get_court_name(self):
        return "Idaho Court of Appeals"
