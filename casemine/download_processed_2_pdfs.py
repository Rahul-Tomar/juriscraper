from datetime import datetime
import os

import requests
from PyPDF2 import PdfReader
from bson import ObjectId
from urllib.parse import urlparse
from pymongo import MongoClient
from casemine.constants import CRAWL_DATABASE_IP, DATABASE_PORT, DATABASE_NAME, \
    MAIN_COLLECTION

client = MongoClient("mongodb://"+CRAWL_DATABASE_IP+":"+str(DATABASE_PORT))
db = client[DATABASE_NAME]
collection = db[MAIN_COLLECTION]


def is_pdf_valid(file_path):
    """Return True if PDF exists, readable, and not an HTML/error page."""

    if not os.path.isfile(file_path):
        return False, "PDF does not exist"

    if os.path.getsize(file_path) < 1000:
        return False, "PDF is too small or empty"

    try:
        # Detect fake PDF / HTML response
        with open(file_path, "rb") as f:
            first_bytes = f.read(5000)

        # PDF must start with %PDF
        if not first_bytes.startswith(b"%PDF"):
            text = first_bytes.decode(errors="ignore").lower()

            if "404 error" in text or "file not found" in text:
                return False, "Downloaded file is a 404 HTML page"

            if "<html" in text or "<!doctype html" in text:
                return False, "Downloaded file is HTML instead of PDF"

            return False, "Invalid PDF format"

        # Validate PDF structure
        reader = PdfReader(file_path)

        if len(reader.pages) == 0:
            return False, "PDF has no pages"

        return True, "PDF is valid and readable"

    except Exception as e:
        return False, f"PDF is corrupted or unreadable: {e}"


def convert_url(old_url):
    new_base = "https://stwjbopinions.blob.core.usgovcloudapi.net/wsc-opinions/"

    # extract filename from URL
    filename = old_url.split("/")[-1]

    # construct new URL
    new_url = new_base + filename

    return new_url


query = {
    "processed": 2,
    "court_type": "state",
    "court_name": "California Court of Appeals",
    "date": {"$gt": datetime(2025, 3, 20)}
}

# query = {'class_name':"ny","response_html":{"$regex":"This site can’t be reached"}}
# query = {"processed": 2, "court_type":'state",crawledAt": {"$gte": datetime(2025, 1, 1)}}
# query = {'processed':2,'court_type':'state','year':2026 , 'court'}
# lst=["67358b58f2b8aa8ee26a1422","67359311f2b8aa8ee26a14ee","6735933af2b8aa8ee26a14fc","6735939ff2b8aa8ee26a1507","67359414f2b8aa8ee26a152e","67359492f2b8aa8ee26a1544","6735975dc1b626349b6cefe7","67359a2fc1b626349b6cf06e","67359e88c1b626349b6cf0e0","67359e96c1b626349b6cf0e4","67359f1cc1b626349b6cf0f9","6735a047c1b626349b6cf118","6735a113c1b626349b6cf12c","6735a41bc1b626349b6cf187","6735a55bc1b626349b6cf1af","6735a61ec1b626349b6cf1d7","6735a78cc1b626349b6cf1f0","6735a9aec1b626349b6cf22f","6735a20e0246406efd7107b2","6735a3019a3c0719f5fddba3",]
# for i in lst:
    # query = {'state':'Delaware',"_id":ObjectId(i)}
count=collection.count_documents(query)
print(count)
crawl_cursor = collection.find(query)
# print(i)
i=1
for doc in crawl_cursor:
    pdf_url = doc.get('pdf_url')
    id = str(doc.get('_id'))
    print(id)
    pdf_url = pdf_url.replace("https://www4.courts.ca.govh","h")
    # pdf_url=convert_url(pdf_url)
    print(pdf_url)
    year = doc.get('year')
    court_name = doc.get('court_name')
    print(court_name)
    if "Nevada" in court_name or "Texas" in court_name:
        continue
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
        # if not str(pdf_url).__contains__("https://www.courts.ca.gov"):
        #     pdf_url="https://www.courts.ca.gov"+pdf_url

        response = requests.get(url=pdf_url,
                                proxies={
                    # 'http': 'socks5h://127.0.0.1:9050','https': 'socks5h://127.0.0.1:9050',
                    "http": "http://23.236.154.202:8800", "https": "http://23.236.154.202:8800"
                }
                                )


        # response.raise_for_status()
        with open(download_pdf_path, 'wb') as file:
            file.write(response.content)
            status, message = is_pdf_valid(download_pdf_path)
            if status:
                update_query.__setitem__("processed", 0)
                update_query.__setitem__("pdf_url",pdf_url)
                collection.update_one({'_id':objectId},{'$set':update_query})
                print(f"{i} - {obj_id} updated")
        i = i + 1
    except Exception as e:
        print(f"{i} - Error while downloading the PDF: {e} for {objectId} , {court_name}")
        update_query.__setitem__("processed", 2)
        collection.update_one({"_id": objectId}, {"$set": update_query})
        i=i+1
client.close()
