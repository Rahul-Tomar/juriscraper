import cloudscraper
from lxml import html
import requests

url="https://nycourts.gov/reporter/motindex/mots_ad2_08-2025.htm"
proxies = {
    'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050',
}
scraper = cloudscraper.create_scraper()
for i in range(1,10):
    response = scraper.get(url, proxies=proxies)
    # response = requests.get(url=url,proxies=proxies)
    if response.text.__contains__("Just a moment..."):
        print(f"cloud_flare not bypassed {i}")
    else:
        print(f"cloud_flare bypassed {i}")