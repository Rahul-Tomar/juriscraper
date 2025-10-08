from datetime import datetime
import os
import re
from time import sleep

from bson import ObjectId
from pymongo import MongoClient

import requests
import xmltodict
import logging

from casemine.constants import ACTS_COLLECTION, CRAWL_DATABASE_IP, DATABASE_NAME, DATABASE_PORT, MAIN_DATABASE_IP


class Statutes:

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    client = MongoClient("mongodb://"+CRAWL_DATABASE_IP+":"+str(DATABASE_PORT))
    db = client[DATABASE_NAME]
    acts_collection = db[ACTS_COLLECTION]

    client_2 = MongoClient("mongodb://" + MAIN_DATABASE_IP + ":" + str(DATABASE_PORT))
    db = client_2["GaugeDB"]
    us_col = db["USacts"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.govinfo.gov/wssearch/rb/uscode"
        self.param1 = "fetchChildrenOnly="
        self.proxies = {
            'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

    def hit_url(self, url):
        attempts = 5
        for attempt in range(attempts):
            try:
                resp = requests.get(url=url, proxies=self.proxies, timeout=10)
                resp.raise_for_status()  # raise HTTPError for bad status
                json_data = resp.json()  # directly parse JSON
                return json_data
            except Exception as e:
                print(f"Attempt {attempt + 1}/{attempts} failed: {e}")
                if attempt < attempts - 1:
                    sleep(2)  # wait before retry
        return None  # all attempts failed

    def convert_date_to_us_format(self, date_string):
        # Possible input formats
        formats = ["%Y-%m-%d",  # 2024-12-31
            "%B %d, %Y"  # January 6, 2025
        ]
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%d/%m/%Y")
            except ValueError:
                continue
        return ""

    def capitalize_all_words(self, text):
        words = re.findall(r'\b\w+\b|\W+', text)
        result = []
        for part in words:
            if re.match(r'\b\w+\b', part):  # If it's a word
                result.append(part.capitalize())
            else:  # If it's punctuation/whitespace
                result.append(part)
        return ''.join(result)

    def smart_quotes(self, s):
        """Convert straight single and double quotes to curly quotes (smart quotes)."""
        out = []
        double_open = True
        single_open = True
        for ch in s:
            if ch == '"':
                out.append('“' if double_open else '”')
                double_open = not double_open
            elif ch == "'":
                out.append('‘' if single_open else '’')
                single_open = not single_open
            else:
                out.append(ch)
        return ''.join(out)

    def create_matched_title(self, text):
        text = self.capitalize_all_words(text).replace(" - "," — ")
        text = self.smart_quotes(text)
        return text

    def fetch_duplicate(self, all_data):
        act_id = all_data['ID']
        long_title = all_data['longTitle']
        query = {"ID": act_id, "longTitle": long_title}
        data = self.acts_collection.find_one(query)
        if data is not None:
            return data.get("_id")
        return None

    def insert_meta_data(self,all_data,existing_id):
        if existing_id is None:
            inserted_result = self.acts_collection.insert_one(all_data)
            act_id = inserted_result.inserted_id
        else:
            update_query={"_id":ObjectId(existing_id)}
            self.acts_collection.update_one(update_query, {"$set":all_data})
            act_id = existing_id

        update_query = {"_id": ObjectId(act_id)}
        self.acts_collection.update_one(update_query,{"$set":{"processed":1}})
        return act_id

    def download_pdf_html(self, all_data, act_id):
        year=all_data['issuedYear']
        html_path = f'/synology/PDFs/US/acts/html/{year}'
        pdf_path = f'/synology/PDFs/US/acts/pdf/{year}'
        html_url = None
        pdf_url = None

        for entry in all_data["location"]["url"]:
            if entry["displayLabel"].lower() == "html rendition":
                html_url = entry["text"]
            elif entry["displayLabel"].lower() == "pdf rendition":
                pdf_url = entry["text"]

        download_pdf_path = os.path.join(pdf_path, f"{act_id}.pdf")
        download_html_path = os.path.join(html_path, f"{act_id}.html")
        os.makedirs(pdf_path, exist_ok=True)
        os.makedirs(html_path, exist_ok=True)
        try:
            # Downloading pdf...
            pdf_response = requests.get(url=pdf_url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"}, proxies=self.proxies, timeout=120)
            pdf_response.raise_for_status()
            with open(download_pdf_path, 'wb') as file:
                file.write(pdf_response.content)

            sleep(5)

            # Downloading html...
            html_response = requests.get(url=html_url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"}, proxies=self.proxies, timeout=120)
            html_response.raise_for_status()
            with open(download_html_path, 'wb') as file:
                file.write(html_response.content)

            # Updating processed
            self.acts_collection.update_one({"_id": ObjectId(act_id)}, {"$set": {"processed": 0}})

        except requests.RequestException as e:
            print(f"Error while downloading the PDF: {e}")
            self.acts_collection.update_many({"_id": ObjectId(act_id)}, {
                "$set": {"processed": 2}})
        return [download_pdf_path,download_html_path]

    def process_data(self,all_data):
        dup_id = self.fetch_duplicate(all_data)
        act_id = self.insert_meta_data(all_data,dup_id)
        paths = self.download_pdf_html(all_data,act_id)
        if dup_id==act_id:
            print(f"{act_id} - Record updated")
        else:
            print(f"{act_id} - Record inserted")

    def sanitize_json(self, data):
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                new_key = k.replace("@", "").replace("#", "")
                new_dict[new_key] = self.sanitize_json(v)
            return new_dict
        elif isinstance(data, list):
            return [self.sanitize_json(i) for i in data]
        elif isinstance(data, str):
            return data.replace("ยง", "§")
        else:
            return data

    def fetch_n_get_xml(self, xml_url, ctr):
        dict_data = None
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            try:
                xml_resp = requests.get(url=xml_url, proxies=self.proxies, timeout=10)
                xml_resp.raise_for_status()  # Raise exception for bad HTTP status codes
                xml_data = xml_resp.text.replace('<?xml version="1.0" encoding="UTF-8"?>', '').replace('@','').replace('#','')
                dict_data = xmltodict.parse(xml_data)
                self.logger.info(f"XML data successfully parsed - {ctr}")
                break  # Success, exit the loop
            except requests.exceptions.Timeout:
                self.logger.info(f"Timeout error on attempt {attempt}")
                sleep(10)
            except requests.exceptions.ConnectionError:
                self.logger.info(f"Connection error on attempt {attempt}")
                sleep(10)
            except requests.exceptions.HTTPError as http_ex:
                self.logger.info(f"HTTP error on attempt {attempt}: {http_ex}")
                sleep(10)
            except requests.exceptions.RequestException as req_ex:
                self.logger.info(f"Request error on attempt {attempt}: {req_ex}")
                sleep(10)
            except Exception as ex:
                if "mismatched tag" in str(ex).lower():
                    self.logger.info(f"Mismatched tag error on attempt {attempt}, waiting 15 seconds...")
                    sleep(10)
                else:
                    self.logger.info(f"Parsing error on attempt {attempt}: {type(ex).__name__}: {ex}")
                    sleep(10)
            if attempt == max_attempts:
                self.logger.info("All retry attempts failed!")
                dict_data = None

        del dict_data['mods']['@xmlns']
        del dict_data['mods']['@xmlns:xsi']
        del dict_data['mods']['@xmlns:xlink']
        del dict_data['mods']['@xsi:schemaLocation']
        del dict_data['mods']['@version']
        return dict_data

    def get_statutes(self,year):
        title_url = f"{self.base_url}/{year}/?{self.param1}1"
        title_json = self.hit_url(title_url)
        title_nodes = title_json["childNodes"]
        i=1
        for title in title_nodes:
            chapter_path = title['nodeValue']["searchPathAlias"]
            chapter_url = f"{self.base_url}/{chapter_path}?{self.param1}1"
            chapter_json = self.hit_url(chapter_url)
            chapter_nodes = chapter_json["childNodes"]
            for section in chapter_nodes:
                section_path = section['nodeValue']["searchPathAlias"]
                section_url = f"{self.base_url}/{section_path}?{self.param1}1"
                section_json = self.hit_url(section_url)
                section_nodes = section_json["childNodes"]
                for acts_node in section_nodes:
                    act_value = acts_node["nodeValue"]
                    granule_id = act_value.get("granuleid", "")
                    package_id = act_value.get("packageid", "")
                    dup = self.acts_collection.find_one({"ID":f"id-{granule_id}"})
                    if dup is not None:
                        print(f"{i} - id-{granule_id} Duplicate")
                        i+=1
                        continue

                    more_meta_url = f"https://www.govinfo.gov/wssearch/getContentDetail?packageId={package_id}&granuleId={granule_id}"
                    more_meta_json = self.hit_url(more_meta_url)
                    mods_link = str(more_meta_json["download"]["modslink"]).replace('//','')

                    mods_link = f"https://{mods_link}"
                    dict_data = self.fetch_n_get_xml(mods_link,i)
                    processed_data =  self.sanitize_json(dict_data['mods'])

                    # creating matched citation_string
                    cite_str = str(processed_data['identifier'][2]['text'])
                    cite_arr = cite_str.split(' ')
                    if list(cite_arr).__len__()==2:
                        cite_str = ''
                    else:
                        cite_str = f"{cite_arr[0]} {cite_arr[1]} § {cite_arr[2]}"

                    # creating matched long_title
                    book = str(processed_data['extension'][1]["searchTitle"]['text'].split(";")[1]).strip()
                    chapter = str(processed_data['extension'][1]["chapterTitle"]).strip()
                    title =   str(processed_data['titleInfo']["title"]).strip()
                    long_title = self.create_matched_title(f"{book} - {chapter} - {title}")

                    processed_data['citationString'] = cite_str
                    processed_data['longTitle'] = long_title
                    processed_data['processed'] = 333
                    processed_data['crawledTill'] = datetime.today()
                    issued_date = processed_data['relatedItem'][-1]['originInfo']['dateIssued']['text']
                    processed_data['issuedYear'] = datetime.strptime(issued_date,"%Y-%m-%d").year
                    self.process_data(processed_data)
                    i+=1
        self.client.close()

act = Statutes()
act.get_statutes(2012)