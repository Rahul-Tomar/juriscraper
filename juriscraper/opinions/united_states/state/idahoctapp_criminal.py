from datetime import datetime

from juriscraper.opinions.united_states.state import idaho_civil


class Site(idaho_civil.Site):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_code = "ICA+Criminal+&+Post+Conviction"
        self.court_key = "ICA"
        self.court_year = datetime.now().year
        self.url = f"https://isc.idaho.gov/api/cms-content-search?scope=documents&document_type=ICA+Opinion&category=ICA+Criminal+%26+Post-Conviction&tag={self.court_year}&sort_by=entry_date&sort_direction=DESC&limit=100"
        self.court_id = self.__module__

    def get_class_name(self):
        return "idahoctapp_criminal"

    def get_court_name(self):
        return "Idaho Court of Appeals"
