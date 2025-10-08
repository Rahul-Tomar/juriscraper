import os
import shutil
import time
from time import time

from bs4 import BeautifulSoup
import pdfkit
import requests
from bson import ObjectId
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from casemine.constants import CRAWL_DATABASE_IP, DATABASE_PORT, DATABASE_NAME, \
    MAIN_COLLECTION

# STATE='New'
client = MongoClient("mongodb://"+CRAWL_DATABASE_IP+":"+str(DATABASE_PORT))
db = client[DATABASE_NAME]
collection = db[MAIN_COLLECTION]

# Query the collection
query = {'class_name':"nyappdiv_4th","response_html":{"$regex":"This site can’t be reached"}}
# query = {'circuit':'1st Circuit','processed':2}
# lst=["67358b58f2b8aa8ee26a1422","67359311f2b8aa8ee26a14ee","6735933af2b8aa8ee26a14fc","6735939ff2b8aa8ee26a1507","67359414f2b8aa8ee26a152e","67359492f2b8aa8ee26a1544","6735975dc1b626349b6cefe7","67359a2fc1b626349b6cf06e","67359e88c1b626349b6cf0e0","67359e96c1b626349b6cf0e4","67359f1cc1b626349b6cf0f9","6735a047c1b626349b6cf118","6735a113c1b626349b6cf12c","6735a41bc1b626349b6cf187","6735a55bc1b626349b6cf1af","6735a61ec1b626349b6cf1d7","6735a78cc1b626349b6cf1f0","6735a9aec1b626349b6cf22f","6735a20e0246406efd7107b2","6735a3019a3c0719f5fddba3",]
# for i in lst:
    # query = {'state':'Delaware',"_id":ObjectId(i)}
count=collection.count_documents(query)
print(count)
crawl_cursor = collection.find(query)
# print(i)
i=1
for data in crawl_cursor:
    pdf_url = data.__getitem__('pdf_url')
    year = int(data.__getitem__('year'))
    court_name = data.get('court_name')
    court_type = data.get('court_type')
    state_name = data.get('state')
    objectId = data.get('_id')

    update_query = {}
    if str(pdf_url).__contains__('motions'):
        update_query.__setitem__("opinion_type", "motion")
    else:
        update_query.__setitem__("opinion_type", "opinion")

    if str(court_type).__eq__('state'):
        path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + state_name + "/" + court_name + "/" + str(year)
    else:
        path = "/synology/PDFs/US/juriscraper/" + court_type + "/" + court_name + "/" + str(year)

    obj_id = str(objectId)
    download_pdf_path = os.path.join(path, f"{obj_id}.pdf")
    os.makedirs(path, exist_ok=True)
    # Create a temporary download directory
    temp_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "temp_pdf_downloads")
    os.makedirs(temp_download_dir, exist_ok=True)
    try:
        if str(pdf_url).endswith(".htm") or str(pdf_url).endswith(".html"):
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--headless")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36")
            options.add_argument("--disable-blink-features=AutomationControlled")

            # Use proxy as required
            proxy = "http://66.63.171.8:8800"  # Replace with your proxy
            options.add_argument(f"--proxy-server={proxy}")

            # Create a WebDriver instance
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get(pdf_url)
            driver_content = driver.page_source
            if (driver_content.__contains__('Sorry, but the page you requested') and driver_content.__contains__('We apologize for any inconvenience this may have caused you.')) or (driver_content.__contains__("This site can’t be reached")) or (driver_content.__contains__("Bandwidth limit reached. Please upgrade to continue using the proxy")) :
                raise Exception(obj_id+' Html not found')
            soup = BeautifulSoup(driver_content, 'html.parser')
            # print(soup.text)
            center_divs = soup.find_all('div', align='center')
            for div in center_divs:
                if div and div.find('input', {'value': 'Return to Decision List'}):
                    div.decompose()

            # # Find all anchor tags and remove the href attribute
            # for tag in soup.find_all('a'):
            #     del tag['href']

            # Find all <p> tags and remove the ones that are empty
            for p in soup.find_all('p'):
                if not p.get_text(strip=True):  # Check if the <p> tag is empty or contains only whitespace
                    p.decompose()  # Remove the <p> tag

            # Remove <script> and <style> tags
            for tag in soup(["script", "style"]):
                tag.decompose()

            # Remove <link> tags (external CSS)
            for link in soup.find_all("link", href=True):
                link.decompose()
            # Remove <img> tags with data or blob URLs
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src.startswith("data:") or src.startswith("blob:") or not src.startswith("http"):
                    img.decompose()

            # Remove problematic anchor hrefs
            for a in soup.find_all("a", href=True):
                if a["href"].startswith("javascript:") or not a["href"].startswith("http"):
                    del a["href"]

            safe_html = soup.prettify()

            file = '/usr/bin/wkhtmltopdf'  # Make sure this is correct path and executable
            config = pdfkit.configuration(wkhtmltopdf=file)

            pdfkit.from_string(safe_html, download_pdf_path, configuration=config)

            update_query.__setitem__("response_html", safe_html)
            update_query.__setitem__("processed", 0)
            collection.update_one({'_id': objectId}, {'$set': update_query})
            print(f"{objectId} updated")
            driver.quit()

        elif str(pdf_url).endswith(".pdf"):
            # Use a more reliable approach for PDF downloads
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--headless")
            options.add_argument("--window-size=1920x1080")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36")
            options.add_argument("--disable-blink-features=AutomationControlled")

            # Use proxy as required
            proxy = "http://66.63.171.8:8800"  # Replace with your proxy
            options.add_argument(f"--proxy-server={proxy}")

            # Set preferences for downloading PDFs automatically without a prompt
            prefs = {
                "download.default_directory": temp_download_dir, "download.prompt_for_download": False, "download.directory_upgrade": True, "plugins.always_open_pdf_externally": True, "safebrowsing.enabled": True}
            options.add_experimental_option("prefs", prefs)

            # Create a WebDriver instance
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            try:
                # Navigate to the PDF URL
                print(f"Attempting to download PDF from: {pdf_url}")
                driver.get(pdf_url)

                # Wait for download to complete (up to 30 seconds)
                max_wait = 30
                wait_time = 0
                pdf_filename = pdf_url.split('/')[-1]
                expected_file = os.path.join(temp_download_dir, pdf_filename)

                while not os.path.exists(expected_file) and wait_time < max_wait:
                    # sleep
                    wait_time += 1
                    print(f"Waiting for download to complete... {wait_time}s")

                if os.path.exists(expected_file):
                    # Move the file to the final destination
                    shutil.move(expected_file, download_pdf_path)
                    print(f"{obj_id} PDF successfully downloaded to: {download_pdf_path}")
                    update_query.__setitem__("processed", 0)
                    collection.update_one({'_id': objectId}, {'$set': update_query})
                else:
                    # Try direct download with requests as fallback, still using proxy
                    print("Selenium download failed, trying direct download with requests...")
                    proxies = {
                        "http":"http://66.63.171.8:8800", "https":"http://66.63.171.8:8800"}
                    response = requests.get(pdf_url, stream=True, proxies=proxies)
                    if response.status_code == 200:
                        with open(download_pdf_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print(f"PDF successfully downloaded with requests to: {download_pdf_path}")
                        update_query.__setitem__("processed", 0)
                        collection.update_one({'_id': objectId}, {'$set': update_query})
                        print(f"{i} - {objectId} updated.")
                    else:
                        raise Exception(f"Failed to download PDF. Status code: {response.status_code}")
            finally:
                driver.quit()
        else:
            print(f"Invalid pdf extension: {pdf_url}")
            raise Exception(f"Invalid pdf extension: {pdf_url}")
    except Exception as e:
        print(f"{objectId} - Error while downloading the PDF: {e}")
        update_query.__setitem__("processed", 2)
        collection.update_one({"_id": objectId}, {"$set": update_query})
        # If there was an error, return None to indicate failure
client.close()
