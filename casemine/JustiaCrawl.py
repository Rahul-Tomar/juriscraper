import random

from bs4 import BeautifulSoup
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import base64
import os
import requests
import time
import random
import time
import traceback
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from jurisdiction_codes import get_juris_code
from jurisdiction_codes import code_list
from jurisdiction_codes import level
from curl_cffi import requests


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
counter = 0

us_proxy_index = 0


USPROXIES = [
    "23.236.154.202:8800",
    "23.236.154.249:8800",
    "23.236.197.155:8800",
    "23.236.197.227:8800",
    "23.236.197.153:8800",
    "156.241.221.148:8800",
    "156.241.216.136:8800",
    "156.241.216.8:8800",
    "156.241.216.194:8800",
    "156.241.221.92:8800",
]


# ============================================================
# 🔥 FIREFOX SELENIUM SETUP
# HTML pages use your saved Firefox Justia profile/settings.
# No hardcoded proxy is applied to Firefox here.
# ============================================================
FIREFOX_PROFILE_PATH = "/home/gaugedata/.mozilla/firefox/dui0ot59.justia"

driver = None


def create_firefox_driver():
    """
    Uses your existing Firefox Justia profile.

    No proxy is hardcoded here.
    If you configured proxy manually inside this Firefox profile,
    Firefox will use that profile setting automatically.
    """
    options = Options()
    options.profile = FIREFOX_PROFILE_PATH

    # Keep browser visible
    # Do NOT use headless
    options.add_argument("--headless")

    return webdriver.Firefox(options=options)


def start_browser_if_needed():
    global driver
    if driver is None:
        driver = create_firefox_driver()
    return driver


def close_browser():
    global driver
    if driver is not None:
        driver.quit()
        driver = None

# ============================================================
# 🔥 FIREFOX PROFILE PAGE FETCHER
# ============================================================
def get_page_html(url):
    """
    Opens each URL using Firefox Justia profile.
    If verification page remains after manual solving,
    browser is restarted and URL is retried.
    """

    for attempt in range(1, 4):
        try:
            browser = start_browser_if_needed()

            print(f"[HTML] Attempt {attempt}: {url}")

            browser.get(url)
            time.sleep(random.uniform(2, 5))

            html = browser.page_source
            title = browser.title

            print(f"[HTML] Title: {title}")

            if is_fake_or_blocked_page(html):
                print("[HTML] Just a moment / verification page detected.")
                print("[HTML] Solve it manually in the visible Firefox window, then press Enter here.")
                input("[HTML] Press Enter after verification is completed...")

                time.sleep(random.uniform(2, 5))

                html = browser.page_source

                if is_fake_or_blocked_page(html):
                    print("[HTML] Still blocked after manual verification.")
                    print("[HTML] Closing current Firefox browser...")
                    close_browser()

                    print("[HTML] Starting fresh Firefox browser/session...")
                    time.sleep(random.uniform(2, 5))

                    browser = start_browser_if_needed()
                    continue

            return html

        except Exception as e:
            print("[HTML] Firefox page load failed")
            print(str(e))

            print("[HTML] Restarting Firefox after failure...")
            close_browser()
            time.sleep(30)

    return None

def is_fake_or_blocked_page(html):
    if not html:
        return True

    text = html.lower()

    cloudflare_markers = [
        "just a moment",
    ]

    return any(marker in text for marker in cloudflare_markers)

def get_next_us_proxy():
    global us_proxy_index
    proxy = USPROXIES[us_proxy_index]
    us_proxy_index = (us_proxy_index + 1) % len(USPROXIES)
    return proxy

# ============================================================
# 🔥 PDF DOWNLOADER
# PDFs use hardcoded USPROXIES and rotate to next proxy on failure.
# ============================================================
def download_pdf(pdf_url, case_id, year, court, court_type):
    base_dir = f"/synology/PDFs/US/Justia/{court_type}/{court}/{year}/"
    os.makedirs(base_dir, exist_ok=True)

    filepath = f"{base_dir}{case_id}.pdf"
    duplicate_filter = {"_id": case_id}

    for attempt in range(1, 21):
        proxy_server = get_next_us_proxy()

        proxies = {
            "http": f"http://{proxy_server}",
            "https": f"http://{proxy_server}",
        }

        print(f"[PDF] Attempt {attempt}/20 using US proxy: {proxy_server}")

        try:
            r = requests.get(
                pdf_url,
                timeout=30,
                stream=True,
                proxies=proxies,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Accept": "application/pdf,*/*",
                    "Referer": "https://law.justia.com/",
                },
            )

            if r.status_code == 200:
                content_type = r.headers.get("content-type", "").lower()

                first_chunk = next(r.iter_content(5), b"")

                if not first_chunk.startswith(b"%PDF"):
                    print(f"❌ Not a PDF. Content-Type: {content_type}")
                    continue

                with open(filepath, "wb") as f:
                    f.write(first_chunk)

                    for chunk in r.iter_content(1024):
                        if chunk:
                            f.write(chunk)

                collection.update_one(
                    duplicate_filter,
                    {"$set": {"pipe": 0}}
                )

                print("✅ PDF Downloaded Successfully")
                return True

            print(f"❌ Bad Status Code: {r.status_code}")

        except Exception as e:
            print(f"❌ Proxy failed: {proxy_server}")
            print("Error:", str(e))

        time.sleep(random.uniform(1, 6))

    collection.update_one(
        duplicate_filter,
        {"$set": {"pipe": 2}}
    )

    print("❌ All US proxies failed for PDF download")
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

            if formated_date.date() < crawled_till_dt.date():
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
            description = None
            pdf_url = None

            for pdf_attempt in range(1, 4):
                # print(f"[PDF URL] Attempt {pdf_attempt}/3 for case page: {next_url}")
                try:
                    case_html = get_page_html(next_url)
                    if not case_html:
                        # print("[PDF URL] Case page HTML is empty. Retrying...")
                        time.sleep(random.uniform(2, 5))
                        continue
                    case_soup = BeautifulSoup(case_html, "html.parser")
                    # Description extraction
                    try:
                        description_tag = case_soup.select_one(".wrapper p")
                        description = description_tag.get_text(
                            strip=True) if description_tag else None
                    except Exception as e:
                        print("[DESCRIPTION] Extraction failed:", e)
                        description = None

                    # PDF extraction
                    pdf_tag = case_soup.select_one(".pdf-icon")

                    if not pdf_tag:
                        pdf_tag = case_soup.select_one('a[href*=".pdf"]')

                    if not pdf_tag:
                        print("[PDF URL] PDF tag not found. Retrying...")
                        time.sleep(random.uniform(2, 5))
                        continue

                    href = pdf_tag.get("href")

                    if not href:
                        print("[PDF URL] PDF href is empty. Retrying...")
                        time.sleep(random.uniform(2, 6))
                        continue

                    if href.startswith("//"):
                        pdf_url = "https:" + href
                    elif href.startswith("/"):
                        pdf_url = "https://cases.justia.com" + href
                    elif href.startswith("https"):
                        pdf_url = href
                    else:
                        pdf_url = None

                    if pdf_url:
                        # print(f"[PDF URL] Found: {pdf_url}")
                        break

                    print("[PDF URL] Invalid PDF href format. Retrying...")
                    time.sleep(random.uniform(2, 6))

                except Exception as e:
                    print(f"[PDF URL] Attempt {pdf_attempt}/3 failed:", e)
                    time.sleep(random.uniform(2, 7))

            if not pdf_url:
                raise Exception("Pdf is Null")

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
                "htmlUrl":next_url
            }

            # Insert/update MongoDB
            existing = collection.find_one({"pdfUrl": pdf_url})
            flag=False
            if not existing:
                _id = collection.insert_one(data).inserted_id
                print(f"✔ Inserted case: id : { _id} , title : { title} ")
                flag=True
                global counter
                counter += 1
                # Download PDF
                download_pdf(pdf_url, _id, year, court, court_type)
                count += 1
            else:
                print(f"---Duplicate--- { title}")
                id = str(existing["_id"])
                # download_pdf(pdf_url, id, year, court, court_type)
                flag=True
            # time.sleep(150)
            if not flag:
                raise Exception(
                    "Data cannot be skipped — neither inserted nor marked duplicate")


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

        # if i > 3 :
        #     break
        # if i < 15:
        #     continue

        court = courts[i]
        # if court!="Western District of Washington":
        #     continue
        court_url = urls[i] + str(datetime.now().year) + "/"
        # court_url = "https://law.justia.com/cases/missouri/court-of-appeals/2025/"
        crawled_till = crawled[i]
        court_type = types[i]

        print(f"\n\n=========== CRAWLING {court} ===========")

        count , latest_crawled_date= crawl_court(court,court_url, crawled_till, court_type)
        print(f"✔ Total Added: {count}")

        if not latest_crawled_date:
            # raise Exception("Invalid latest_crawled_date ")
            latest_crawled_date=crawled_till
            print(f"latest_crawled_date for {court} id {latest_crawled_date}")
        print("#################################### End ############################################")
        crawled[i] = latest_crawled_date
        config_collection.update_one(
            {"ClassName": "JustiaCrawl"},
            {"$set": {f"CrawledTill.{i}": latest_crawled_date}}
        )

    # update config
    # config_collection.update_one(
    #     {"ClassName": "JustiaCrawl"},
    #     {"$set": {"CrawledTill": crawled}}
    # )
    global counter
    print("Total records inserted are " , counter)

# Run scraper
try:
    run_justia()
finally:
    close_browser()
