import json

from lxml import html
import requests

class Acts:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url="https://www.govinfo.gov/wssearch/rb/plaw"
        self.page_size=100
        self.url_suffix = f"fetchChildrenOnly=0&sortDirection=1&pageSize={self.page_size}&offset=0"
        self.proxies = {
            'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'
        }

    def get_act_years(self):
        main_url=f"{self.base_url}?{self.url_suffix}"
        year_resp = requests.get(url=main_url,proxies=self.proxies)
        json_year = json.loads(year_resp.text)
        child_nodes = json_year["childNodes"]
        for child in child_nodes:
            node = child["nodeValue"]
            display_value = node["displayValue"]
            value = node["value"]
            print(f"{display_value}")
            year_wise_url=f"{self.base_url}/{value}?fetchChildrenOnly=1&sortDirection=1&pageSize={self.page_size}&offset=0"
            # print(year_wise_url)
            year_wise_resp = requests.get(url=year_wise_url, proxies=self.proxies)
            year_wise_json = json.loads(year_wise_resp.text)
            year_wise_child = year_wise_json["childNodes"]
            for inner_child in year_wise_child:
                inner_node = inner_child["nodeValue"]
                browse_path = str(inner_node["browsePath"]).lower()
                pub_pvt_url = f"{self.base_url}/{browse_path}?fetchChildrenOnly=1&sortDirection=1&pageSize={self.page_size}&offset=0"
                pub_pvt_resp = requests.get(url=pub_pvt_url, proxies=self.proxies)
                pub_pvt_json = json.loads(pub_pvt_resp.text)
                pub_pvt_child = pub_pvt_json["childNodes"]
                for pub_pvt_child in pub_pvt_child:
                    pub_pvt_node = pub_pvt_child["nodeValue"]
                    pub_pvt_path = str(pub_pvt_node["browsePathAlias"])
                    data_url = f"{self.base_url}/{pub_pvt_path}?fetchChildrenOnly=1&sortDirection=1&pageSize=100&offset=0"
                    data_url_resp = requests.get(url=data_url, proxies=self.proxies)
                    data_url_json = json.loads(data_url_resp.text)
                    data_url_child = data_url_json["childNodes"]
                    for data in data_url_child:
                        data_node = data["nodeValue"]
                        pkg_id = str(data_node["packageid"])
                        published_date = str(data_node["publishdate"])
                        meta_url="https://www.govinfo.gov/wssearch/getContentDetail?packageId="+pkg_id
                        meta_resp = requests.get(url=meta_url, proxies=self.proxies)
                        meta_json = json.loads(meta_resp.text)
                        title = meta_json['title']
                        print(f"{pkg_id} | {published_date} | {title}")

            print("******************************************************")

act = Acts()
act.get_act_years()
