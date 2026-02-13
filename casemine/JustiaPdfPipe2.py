from pymongo import MongoClient
import os
import time
import requests
import random

mongo = MongoClient("mongodb://192.168.1.11:27017")
db = mongo["justia"]
collection = db["JustiaData"]


def download_pdf_with_proxy(pdf_url, output_path, proxies_list, max_retries=5,
                            timeout=30):
    """
    Downloads a PDF file using rotating proxies.

    :param pdf_url: URL of the PDF
    :param output_path: Local file path to save PDF
    :param proxies_list: List of proxy dicts
    :param max_retries: Number of retry attempts
    :param timeout: Request timeout in seconds
    :return: True if success, False otherwise
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/pdf,application/octet-stream,*/*",
        "Connection": "keep-alive"
    }

    for attempt in range(max_retries):

        proxy = random.choice(proxies_list)
        proxy_dict = {
            "http": proxy["server"],
            "https": proxy["server"]
        }

        try:
            print(f"[Attempt {attempt + 1}] Using Proxy: {proxy['server']}")

            response = requests.get(
                pdf_url,
                headers=headers,
                proxies=proxy_dict,
                stream=True,
                timeout=timeout
            )

            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                print("Download successful.")
                return True

            else:
                print(f"Bad response: {response.status_code}")

        except Exception as e:
            print(f"Error: {str(e)}")

        time.sleep(2)

    print("All retries failed.")
    return False

PROXIES = [
    # {"server": "http://23.236.197.155:8800"},  # Us proxy
    # {"server": "http://23.236.154.202:8800"},   # Us Proxy
    {"server": "http://156.241.229.113:8800"},
    {"server": "http://156.241.229.153:8800"},
    {"server": "http://156.241.225.93:8800"},
    {"server": "http://23.236.197.227:8800"}, #Us proxy
    {"server": "http://156.241.224.167:8800"},
    {"server": "http://46.175.153.152:8800"},
    {"server": "http://23.236.197.153:8800"},  #Us proxy
    {"server": "http://46.175.153.155:8800"},
    {"server": "http://156.241.225.161:8800"},
    {"server": "http://23.236.154.249:8800"}, #us
    {"server": "http://156.241.224.171:8800"},
    {"server": "http://23.236.197.153:8800"}, # us
    {"server": "http://156.241.225.170:8800"},
    {"server": "http://46.175.152.240:8800"},
    {"server": "http://156.241.224.217:8800"},
    {"server": "http://46.175.154.18:8800"},
    {"server": "http://46.175.152.107:8800"},
    {"server": "http://46.175.153.171:8800"},
    {"server": "http://156.241.225.81:8800"},
    {"server": "http://156.241.229.198:8800"},
    {"server": "http://46.175.154.91:8800"},
    {"server": "http://46.175.154.132:8800"},
    {"server": "http://46.175.152.193:8800"},
    {"server": "http://46.175.154.148:8800"},
]

query = {'pipe':2}
count=collection.count_documents(query)
print(count)
crawl_cursor = collection.find(query)
for doc in crawl_cursor:
    pdfUrl = doc.get('pdfUrl')
    year = doc.get('year')
    courtName = doc.get('courtName')
    courtType = doc.get('courtType')
    objectId = doc.get('_id')
    update_query = {}
    path = "/synology/PDFs/US/Justia/" + courtType + "/" + courtName + "/" +str(year)
    obj_id = str(objectId)
    print(obj_id)
    download_pdf_path = os.path.join(path, f"{obj_id}.pdf")
    os.makedirs(path, exist_ok=True)
    try:
        success = download_pdf_with_proxy(
            pdf_url=pdfUrl,
            output_path=download_pdf_path,
            proxies_list=PROXIES
        )

        if success:
            collection.update_one(
                {"_id": objectId},
                {"$set": {"pipe": 0}}
            )
        else:
            collection.update_one(
                {"_id": objectId},
                {"$set": {"pipe": 2}}
            )
    except Exception as e:
        print("Unexpected error:", e)
        collection.update_one({"_id": objectId}, {"$set": {"pipe": 2}})






