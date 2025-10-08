

# import requests
#
# pdf_url="https://ojd.contentdm.oclc.org/digital/custom/OJDRedirect?collection=p17027coll5&identifier=A183038.pdf"
#        # https://ojd.contentdm.oclc.org/digital/api/collection/p17027coll5/id/39177/download
# response = requests.get(url=pdf_url, proxies={
#             # 'http': 'socks5h://127.0.0.1:9050','https': 'socks5h://127.0.0.1:9050',
#             "http": "http://192.126.217.76:8800", "https": "http://192.126.217.76:8800"})
#
# print(response.status_code)
# print(response.text)
# import cloudscraper
#
# proxies = {
#           # "http": "http://23.226.137.155:8800", "https": "https://23.226.137.155:8800",
#           # "http": f"{us_proxy.ip}:{us_proxy.port}", "https": f"{us_proxy.ip}:{us_proxy.port}",
#           'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'
# }
#
# scraper = cloudscraper.create_scraper()  # This handles Cloudflare challenges
#
# # Example POST data (you can modify this as per your API requirements)
# payload = {
#     "rbOpinionMotion": "opinion", "Pty": "",
#             "and_or": "and", "dtStartDate": "01/06/205",
#             "dtEndDate": "04/06/205", "court": "Court of Appeals",
#             "docket": "", "judge": "", "slipYear": "", "slipNo": "",
#             "OffVol": "", "Rptr": "", "OffPage": "", "fullText": "",
#             "and_or2": "and", "Order_By": "Party Name", "Submit": "Find",
#             "hidden1": "", "hidden2": "",
# }
#
# heads={
#     "Host":"iapps.courts.state.ny.us",
#     "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
#     "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     "Accept-Language":"en-US,en;q=0.5",
#     "Accept-Encoding":"gzip, deflate, br, zstd",
#     "Content-Type":"application/x-www-form-urlencoded",
#     "Content-Length":"241",
#     "Origin":"https://iapps.courts.state.ny.us",
#     "Connection":"keep-alive",
#     "Referer":"https://iapps.courts.state.ny.us/lawReporting/Search?searchType=all",
#     "Upgrade-Insecure-Requests":"1",
#     "Sec-Fetch-User":"?1",
#     "Priority":"u=0, i",
#     "Pragma":"no-cache",
#     "Cache-Control":"no-cache",
#     "TE":"trailers"
# }
#
# # POST request
# response = scraper.get("https://nycourts.gov/reporter/pdfs/2024/2024_30837.pdf", proxies=proxies)
# print(response.status_code)
# print("****************************************************************")
# print(response.text)
from datetime import datetime
import os

from pymongo import MongoClient
import requests

#*******************************************************************************************************************
# import requests
#
# from casemine.casemine_util import CasemineUtil
#
# link = 'https://nycourts.gov/reporter/slipidx/miscolo_2024_October.shtml'
# heads={
#     "Host":"nycourts.gov",
# "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
# "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
# "Accept-Language":"en-US,en;q=0.5",
# "Accept-Encoding":"gzip, deflate, br, zstd",
# "Connection":"keep-alive",
# "Cookie":"__cf_bm=02mWRvGtVEMaxUTEI8eQmXBjKEJ58DsRw0lR8wYbTV4-1749619448-1.0.1.1-iDaOswIAUbE0_MaFB0MTaZC2qN53620W1688FDUDMZuBS0zO7MZ5yExbV45fFvAmBfnMMUOuT4yOmvmgtf9GyvkW8ou75lhz1gQV4OhlP.c; cf_clearance=M3Wi1.DFXQ34IRtzpu94I1_1Gie_UP8ZQBU07HlT96s-1749619449-1.2.1.1-yz0JWw4kdE7UqR3fRrEVaOPiQaxMo_7VIbvePtXKAhLGh_LsOlUJn3EABsRKc0.A1gxyIU2LaAEDcxGvCE3jv2Vi.K6I2Nsy6NJ42HJrgvYvpK2bQlz0oBHX1501L8VdtQTZ_uWe9geosmVIyTALojqin9stOa.7WB5tBI_wGxEsBTRJhH6sBBqoH_g3gcFlJnk93urvWyN.sLZvHRoRz1h7sJFECkrmYKbTMRGxxcpo2Yw.p1QsScD7K71ymbTu6gOXI9w6HYSlfmB7hsh9gQZFyWHfHBz8tLpTghrLnDt.HPq4Y94yKkUMufoH_dXrw8k0x9HagWgEFuJN4bsGb30LOwWS.NndVPmBwG4EvcE",
# "Upgrade-Insecure-Requests":"1",
# "Sec-Fetch-Dest":"empty",
# "Sec-Fetch-Mode":"no-cors",
# "Sec-Fetch-Site":"same-origin",
# "Sec-Fetch-User":"?1",
# "If-Modified-Since":"Tue, 25 Mar 2025 12:30:40 GMT",
# "Priority":"u=0, i",
# "Pragma":"no-cache",
# "Cache-Control":"no-cache",
# "TE":"trailers"
# }
# us_proxy=CasemineUtil.get_us_proxy()
# resp = requests.get(url='https://nycourts.gov/reporter/slipidx/miscolo_2024_October.shtml',headers=heads)
# print(resp.status_code)
# print('----------------------------------------------------------------')
# print(resp.text)

# ******************************************************************************************************************************
# import requests
#
# headers={
# 'Host':'nycourts.gov',
# 'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0',
# 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
# 'Accept-Language':'en-US,en;q=0.5',
# 'Accept-Encoding':'gzip, deflate, br, zstd',
# 'Connection':'keep-alive',
# 'Cookie': '__cf_bm=WkK9r22gE4CKpmi86SLNBIkC6Gi3vkQhvbwm9ymByKg-1747645932-1.0.1.1-HT9BOAXLdTCEoAY.NfQBajoHkz7U41Vks00ri9cUmZ._w9TgH7PwnXofV8AfJ9mv_0U7aYLPg9ObFEOQ_xhR_DOoTz43bWzYDJZKGhVCIZ4'
# }
#
#
# proxies = {
#                     # "http": "http://23.226.137.155:8800", "https": "https://23.226.137.155:8800",
#                     # "http": f"{us_proxy.ip}:{us_proxy.port}", "https": f"{us_proxy.ip}:{us_proxy.port}",
#                     'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'
#                 }
# url = 'https://nycourts.gov/reporter/slipidx/miscolo_2024_October.shtml'
# # response = requests.post(url=url,headers=headers,proxies=proxies,data=data)
# response = requests.get(url=url, headers=headers)
# print(response.status_code)


# import requests
#
# from casemine import sample
# from casemine.sample import TorProxyGenerator
#
# url="https://www.govinfo.gov/wssearch/search"
# headers = {
#     'Host': 'www.govinfo.gov',
#     'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0',
#     'Accept': 'application/json, text/plain, */*',
#     'Accept-Language': 'en-US,en;q=0.5',
#     'Accept-Encoding': 'gzip, deflate, br, zstd',
#     'Connection': 'keep-alive',
#     'Content-Type': 'application/json',
# }
# data='{"historical":false,"offset":1,"query":"publishdate:range(2025-01-01,2025-05-01)","facetToExpand":"governmentauthornav","facets":{"accodenav":["USCOURTS"],"governmentauthornav":["United States District Court District of Minnesota"]},"filterOrder":["accodenav","governmentauthornav"],"sortBy":"2","pageSize":100}'
# i=0
# while i<10:
#     try:
#         proxy = TorProxyGenerator()
#         p=proxy.get_proxy()
#         resp = requests.post(url=url,headers=headers,data=data,proxies={
#             "http":p,
#             "https":p,
#         },timeout=60)
#         print(resp.status_code)
#     except Exception as ex:
#         print(ex)
#         if str(ex).__contains__('Max retries exceeded with url'):
#             i+=1
#             continue
#         else:
#             i+=1
#             raise ex


# from pymongo import MongoClient
#
# from casemine.constants import CRAWL_DATABASE_IP, DATABASE_NAME, DATABASE_PORT, MAIN_COLLECTION, MAIN_PDF_PATH
#
# client = MongoClient("mongodb://"+CRAWL_DATABASE_IP+":"+str(DATABASE_PORT))
# db = client[DATABASE_NAME]
# collection = db[MAIN_COLLECTION]
# lst = collection.find({'class_name':'ca11_u','year':2025,'pdf_url':{'$regex':"unpubhttp"}})
# i=1
# for data in lst:
#     pdf_url = data.__getitem__('pdf_url')
#     print(pdf_url)
#     pdf_url = "http" +str(pdf_url).replace("","").split("http")[2]
#     print(pdf_url)
#     print("=============================================")
#
#     year = int(data.__getitem__('year'))
#     court_name = data.get('court_name')
#     court_type = data.get('court_type')
#     state_name = data.get('circuit')
#     opinion_type = data.get('opinion_type')
#
#     path = MAIN_PDF_PATH + court_type + "/" + state_name + "/" + court_name + "/" + str(year)
#     obj_id = str(data.get('_id'))
#     download_pdf_path = os.path.join(path, f"{obj_id}.pdf")
#     os.makedirs(path, exist_ok=True)
#     try:
#         response = requests.get(url=pdf_url, headers={
#             "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"}, proxies={
#             "http": "http://192.126.217.76:8800", "https": "http://192.126.217.76:8800"}, timeout=120)
#         response.raise_for_status()
#         with open(download_pdf_path, 'wb') as file:
#             file.write(response.content)
#         print("pdf downloaded")
#         collection.update_one({"_id": obj_id}, {"$set": {"processed": 0,"pdf_url":pdf_url}})
#     except requests.RequestException as e:
#         collection.update_many({"_id": obj_id}, {"$set": {"processed": 2,"pdf_url":pdf_url}})
#     i+=1


# Query the collection
# query = {'state': STATE ,'processed':2}
# query = {'class_name':'md_fla','pdf_url':{'$regex':'https://example.com'}}
# count=collection.count_documents(query)
# print(count)
# crawl_cursor = collection.find(query)
# i=1
# for doc in crawl_cursor:
#     pdf_url = doc.get('pdf_url')
#     id = doc.get('_id')
#     processed = doc.get('processed')
#     new_pdf_url = str(pdf_url).replace("https://example.com/","")
#     update_query={}
#     if processed == 10:
#         update_query.__setitem__("processed", 5)
#     else:
#         update_query.__setitem__("processed", processed)
#     update_query.__setitem__("pdf_url", new_pdf_url)
#     collection.update_one({'_id': id}, {'$set': update_query})
#     print(f"{i} - {id} {pdf_url} {new_pdf_url} updated")
#     i+=1