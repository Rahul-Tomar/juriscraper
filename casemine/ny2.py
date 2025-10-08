import os
import requests
from PyPDF2 import PdfReader
from datetime import datetime
import os

import requests
from bson import ObjectId
from pymongo import MongoClient
from casemine.constants import CRAWL_DATABASE_IP, DATABASE_PORT, DATABASE_NAME, \
    MAIN_COLLECTION

client = MongoClient("mongodb://"+CRAWL_DATABASE_IP+":"+str(DATABASE_PORT))
db = client[DATABASE_NAME]
collection = db[MAIN_COLLECTION]

# Folder containing PDFs
pdf_folder = os.path.expanduser("/synology/PDFs/US/juriscraper/state/Ohio")

# Function to check if a PDF is corrupted
def is_pdf_corrupted(file_path):
    try:
        reader = PdfReader(file_path)
        _ = reader.pages  # Attempt to access pages
        return False
    except Exception as e:
        # print(f"[!] Corrupted: {file_path} | Reason: {e}")
        return True

for root, dirs, files in os.walk(pdf_folder):
    # Check if we're in a folder named '2025'
    if os.path.basename(root) == "2025":
        print(f"🔍 Scanning folder: {root}")
        i=0
        for filename in files:
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(root, filename)
                if is_pdf_corrupted(file_path):
                    object_id = filename.lower().replace(".pdf","")
                    print(f"❌ Corrupted PDF: {object_id}")
                    doc = collection.find_one({"_id": ObjectId(object_id)})
                    pdf_url = doc.get('pdf_url')
                    year = doc.get('year')
                    court_name = doc.get('court_name')
                    court_type = doc.get('court_type')
                    if str(court_type).__eq__('Federal'):
                        state_name = doc.get('circuit')
                    else:
                        state_name = doc.get('state')
                    objectId = doc.get('_id')
                    update_query = {}
                    if not state_name is None:
                        path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + state_name + "/" + court_name + "/" + str(year)
                    else:
                        path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + court_name + "/" + str(year)
                    obj_id = str(objectId)
                    download_pdf_path = os.path.join(path, f"{obj_id}.pdf")
                    os.makedirs(path, exist_ok=True)
                    try:
                        response = requests.get(url=pdf_url, proxies={
                            # 'http': 'socks5h://127.0.0.1:9050','https': 'socks5h://127.0.0.1:9050',
                            "http": "http://104.223.126.88:8800", "https": "http://104.223.126.104:8800"
                        })
                        # response.raise_for_status()
                        with open(download_pdf_path, 'wb') as file:
                            file.write(response.content)
                        update_query.__setitem__("processed", 0)
                        update_query.__setitem__("pdf_url", pdf_url)
                        collection.update_one({'_id': objectId}, {'$set': update_query})
                        print(f"{i} - {obj_id} updated")
                        i = i + 1
                    except Exception as e:
                        print(f"{i} - Error while downloading the PDF: {e} for {objectId}")
                        update_query.__setitem__("processed", 2)
                        collection.update_one({"_id": objectId}, {"$set": update_query})
                        i = i + 1
client.close()
