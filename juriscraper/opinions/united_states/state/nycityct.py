from datetime import datetime

import cloudscraper
import requests
from typing_extensions import override

from juriscraper.opinions.united_states.state import nytrial

class Site(nytrial.Site):
    court_regex = r"City? (Ct|Court)"
    # Most start with the regex, but there are special cases
    # such as 'Utica City Ct' in Dec 2023

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        flag = False
        for year in range(start_date.year, end_date.year+1):
            for i in range(1, 13):
                if year==end_date.year and i==end_date.month:
                    self.url=self.build_url()
                    flag=True
                else:
                    self.url=self.build_url(datetime(year=year,month=i,day=1))
                self.parse()
                self.downloader_executed=False
                # print(self.url)
                if flag:
                    break
        return 0

    @override
    def _download(self, request_dict={}):
        proxies = {
            # 'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050',
            "http": "http://23.236.154.202:8800",
            "https": "http://23.236.154.202:8800"
             }
        scraper = cloudscraper.create_scraper()  # This handles Cloudflare challenges
        print(self.url)
        response = scraper.get(self.url, proxies=proxies)
        html_tree = self._make_html_tree(response.content)
        return html_tree


    def get_class_name(self):
        return "nycityct"

    def get_court_name(self):
        return "New York City Court"
