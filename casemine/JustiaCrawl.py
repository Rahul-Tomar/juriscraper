from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import base64
import os
import requests
import time
import traceback
from jurisdiction_codes import get_juris_code
from jurisdiction_codes import code_list
from jurisdiction_codes import level
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

proxy_index = 0

# ------------------------------------------------------------
# 🔥 MONGODB SETUP (same as Java)
# ------------------------------------------------------------
mongo = MongoClient("mongodb://192.168.1.11:27017")
db = mongo["justia"]
collection = db["JustiaData"]
config_collection = db["JustiaConfig"]
judis_code_and_name = get_juris_code()
codeList = code_list()
level = level()
# ============================================================
# 🔥 PLAYWRIGHT PAGE FETCHER
# ============================================================
def get_page_html(url):
    global proxy_index

    for attempt in range(10):
        try:
            with sync_playwright() as p:
                proxy = PROXIES[proxy_index]
                proxy_index = (proxy_index + 1) % len(PROXIES)

                print(f"\n Using Proxy: {proxy['server']}")

                browser = p.firefox.launch(headless=True, proxy=proxy)
                context = browser.new_context()
                page = context.new_page()

                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle")

                html = page.content()

                browser.close()
                return html

        except:
            print("❌ Proxy failed, retrying with next proxy...")
            continue

    return None


# ============================================================
# 🔥 PDF DOWNLOADER
# ============================================================
def download_pdf(pdf_url, case_id, year, court, court_type):
    base_dir = f"/synology/PDFs/US/Justia/{court_type}/{court}/{year}/"
    os.makedirs(base_dir, exist_ok=True)

    filepath = f"{base_dir}{case_id}.pdf"
    duplicate_filter = {"_id": case_id}

    try:
        r = requests.get(pdf_url, timeout=30, stream=True)
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

        # ✅ PDF downloaded successfully, set pipe = 0
        collection.update_one(duplicate_filter, {"$set": {"pipe": 0}})
        return True

    except Exception as e:
        traceback.print_exc()

        # ❌ PDF download failed, set pipe = 2
        collection.update_one(duplicate_filter, {"$set": {"pipe": 2}})
        return False

# ============================================================
# 🔥 MAIN JUSTIA SCRAPER — FULL LOGIC FROM JAVA
# ============================================================
def crawl_court(court, court_url, crawled_till, court_type):
    count = 0
    url = court_url
    latest_crawled_date = None
    while url:
        print(f"   Crawling Page: {url}")
        print(f"============================\n")

        html = get_page_html(url)
        if not html:
            print("⚠ Failed to load page")
            break

        soup = BeautifulSoup(html, "html.parser")

        # =====================================================
        # 🔥 CASE LIST (Your Java logic)
        # =====================================================
        case_blocks = soup.select("div.has-padding-content-block-30")

        for block in case_blocks:
            try:
                title = block.select_one("a.case-name").get_text(strip=True)
                href = block.select_one("a.case-name")["href"]
                next_url = "https://law.justia.com" + href
                date_text = block.select_one("span.color-emperor").get_text(strip=True)
                date_text_clean = date_text.replace("Date:", "").strip()

                # Base64 decode if needed
                if title == "Plaintiff v. Defendant":
                    script_tag = block.select_one("script")
                    if script_tag:
                        txt = script_tag.get_text().strip()
                        start = txt.find('"') + 1
                        end = txt.rfind('"')
                        encoded = txt[start:end]
                        title = base64.b64decode(encoded).decode().strip()

            except:
                continue

            # Parse date
            formated_date = datetime.strptime(date_text_clean, "%B %d, %Y")
            formated_date_str = formated_date.strftime("%d/%m/%Y")
            crawled_till_dt = datetime.strptime(crawled_till, "%d/%m/%Y")
            # Stop if older than crawledTill

            if latest_crawled_date is None:
                latest_crawled_date = formated_date_str
            else:
                latest_dt = datetime.strptime(latest_crawled_date, "%d/%m/%Y")
                if formated_date.date() > latest_dt.date():
                    latest_crawled_date = formated_date_str

            if formated_date.date() <= crawled_till_dt.date():
                print("Reached or passed crawledTill, stopping.")
                # if not latest_crawled_date:
                #     latest_crawled_date = formated_date_str
                return count , latest_crawled_date

            # # Bump crawled till
            # if formated_date.date() > crawled_till_dt.date():
            #
            #     latest_crawled_date = formated_date_str

            # ==============================================
            # Fetch inner case page
            # ==============================================
            case_html = get_page_html(next_url)
            case_soup = BeautifulSoup(case_html, "html.parser")

            try:
                description = case_soup.select_one(".wrapper p").get_text(strip=True)
            except:
                description = None

            # PDF extraction
            try:
                pdf_tag = case_soup.select_one(".pdf-icon")
                if pdf_tag:
                    # Get outer HTML
                    pdf_html = str(pdf_tag)

                    # Extract href manually like Java logic
                    start_idx = pdf_html.find('href="/') + 7
                    end_idx = pdf_html.find('" target="')
                    pdf_url = "https:/" + pdf_html[start_idx:end_idx]
                else:
                    pdf_url = None
            except:
                continue

            # Dockets
            # print(block)
            dockets = []

            try:
                court_name = court.strip()

                # -----------------------------------------
                # 1️⃣ Mississippi Courts → Use logic same as Java
                # -----------------------------------------
                if court_name in ["Supreme Court of Mississippi",
                                  "Mississippi Court of Appeals"]:

                    citation_tag = block.select_one(".justia-citation")

                    if citation_tag:
                        # own text = remove inside children
                        citation_text = citation_tag.get_text(strip=True)
                        parts = [p.strip() for p in citation_text.split(",") if
                                 p.strip()]
                        dockets.extend(parts)

                # -----------------------------------------
                # 2️⃣ All Other Courts → Extract "Docket Number"
                # -----------------------------------------
                else:
                    strong_tag = block.find("strong", string=lambda
                        x: x and "Docket Number" in x)

                    if strong_tag:
                        # Usually in the nextSibling (text node)
                        docket_raw = strong_tag.next_sibling

                        if docket_raw and docket_raw.strip():
                            dockets.append(docket_raw.strip())

                        else:
                            # fallback: search for next text anywhere
                            fallback = strong_tag.find_next(string=True)
                            if fallback and fallback.strip():
                                dockets.append(fallback.strip())

            except Exception as e:
                print("Docket extraction error:", e)

            # Split title
            if " v. " in title.lower():
                idx = title.lower().index(" v. ")
                appellant = title[:idx]
                respondent = title[idx + 4:]
            elif " v " in title.lower():
                idx = title.lower().index(" v ")
                appellant = title[:idx]
                respondent = title[idx + 3:]
            else:
                appellant = title
                respondent = ""

            year = formated_date.year
            jurisdiction_code = judis_code_and_name.get(court)
            try:
                clindex = codeList.index(jurisdiction_code.strip())
            except ValueError:
                clindex = -1

            # Determine jurisdiction level
            if clindex == -1:
                jurisdiction_level = -1
            else:
                jurisdiction_level = int(level[clindex])
            data = {
                "longTitle": title,
                "shortTitle": title,
                "date": formated_date,
                "appellant": appellant,
                "respondent": respondent,
                "courtName": court,
                "jurisdictionCode":jurisdiction_code,
                "jurisdiction_level":jurisdiction_level,
                "courtType": court_type,
                "year": year,
                "pdfUrl": pdf_url,
                "dockets": dockets,
                "linkingPending":1,
                "pipe": 333,
                "crawledAt": datetime.now(),
                "backEndInformation": {"source": "Justia"},
                "description": description,
            }

            # Insert/update MongoDB
            existing = collection.find_one({"pdfUrl": pdf_url})
            if not existing:
                _id = collection.insert_one(data).inserted_id
                print(f"✔ Inserted case: id : { _id} , title : { title} ")

                # Download PDF
                download_pdf(pdf_url, _id, year, court, court_type)
                count += 1
            else:
                print("---Duplicate---")

        # NEXT PAGE
        next_btn = soup.select_one("span.next.pagination.page > a")
        if next_btn:
            next_href = next_btn["href"]
            url = "https://law.justia.com" + next_href
        else:
            url = None

    return count , latest_crawled_date

def run_justia():

    config = config_collection.find_one({"ClassName": "JustiaCrawl"})
    courts = config["courtsName"]
    urls = config["courtsUrls"]
    crawled = config["CrawledTill"]
    types = config["courtType"]

    for i in range(len(courts)):

        court = courts[i]
        # if court!="Northern District of California":
        #     continue
        court_url = urls[i] + str(datetime.now().year) + "/"
        crawled_till = crawled[i]
        court_type = types[i]

        print(f"\n\n=========== CRAWLING {court} ===========")

        count , latest_crawled_date= crawl_court(court, court_url, crawled_till, court_type)
        print(f"✔ Total Added: {count}")
        print(f"latest_crawled_date for {court} id {latest_crawled_date}")
        if not latest_crawled_date:
            # raise Exception("Invalid latest_crawled_date ")
            latest_crawled_date=crawled_till
        print("#################################### End ############################################")
        crawled[i] = latest_crawled_date

    # update config
    config_collection.update_one(
        {"ClassName": "JustiaCrawl"},
        {"$set": {"CrawledTill": crawled}}
    )


# Run scraper
run_justia()
