import requests

resp = requests.get("https://ibbi.gov.in/en/legal-framework/notifications?title=&date=12%2F06%2F2025&page=3")
print(resp.status_code)
print(resp.text)