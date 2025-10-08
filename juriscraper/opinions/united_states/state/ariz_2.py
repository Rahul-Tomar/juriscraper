from datetime import datetime

from juriscraper.OpinionSiteLinear import OpinionSiteLinear


class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_html(self) -> None:
        pass

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        for year in range(start_date.year, end_date.year + 1):
            self.url = f"https://opinions.azcourts.gov/SearchOpinionsMemoDecs.aspx?year={year}&court=999"
            self.parse()
            self.downloader_executed = False
        return 0

    def get_court_type(self):
        return "state"

    def get_court_name(self):
        return "Supreme Court Of The State Of Arizona"

    def get_state_name(self):
        return "Arizona"

    def get_class_name(self):
        return "ariz"
