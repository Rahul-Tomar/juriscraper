from datetime import datetime
import requests
from bs4 import BeautifulSoup

from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear
class Site(OpinionSiteLinear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"
        self.url = "https://search.txcourts.gov/CaseSearch.aspx?coa=cossup"
        self.proxies = {
            "http": "http://23.236.197.153:8800",
            "https": "http://23.236.197.153:8800"
        }
        self.lower_court_info = []
        self._opt_attrs = [
            "adversary_numbers",
            "causes",
            "dispositions",
            "divisions",
            "docket_attachment_numbers",
            "docket_document_numbers",
            "docket_numbers",
            "judges",
            "lower_courts",
            "lower_court_judges",
            "lower_court_numbers",
            "nature_of_suit",
            "citations",
            "parallel_citations",
            "summaries",
            "case_name_shorts",
            "child_courts",
            "authors",
            "joined_by",
            "per_curiam",
            "types",
            "other_dates",
            "html_urls",
            "response_htmls",
            "opinion_types",
            "teasers",
            "lower_court_info"
        ]
        self._all_attrs = self._req_attrs + self._opt_attrs
        self.startdate = ""
        self.end_date = ""
        self.headers= {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cookie": "__utma=211709392.113509422.1745220527.1763618714.1763701236.5; __utma=143868855.2101498572.1745220860.1763639573.1763700775.8; ASP.NET_SessionId=xp1ojkraaqswz0ormh4m54hf; __utmc=143868855; __utmz=143868855.1763552230.2.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utmc=211709392; __utmz=211709392.1763701236.5.2.utmcsr=search.txcourts.gov|utmccn=(referral)|utmcmd=referral|utmcct=/; _clck=ul2xw5%5E2%5Eg17%5E0%5E2149; _clsk=8t4rqg%5E1763701264802%5E4%5E1%5Eo.clarity.ms%2Fcollect; __utmb=143868855.0.10.1763700775; __utmb=211709392.4.10.1763701236; __utmt=1",
            "Host": "search.txcourts.gov",
            "Priority": "u=0, i",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "TE": "trailers",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        }

    def hidden(self,soup, name):
        tag = soup.find("input", {"name": name})
        return tag["value"] if tag else ""

    def _download(self, request_dict={}):
        session = requests.Session()
        response = session.get(url=self.url,proxies=self.proxies,headers=self.headers)
        # print(response.status_code)
        # print(response.text)
        soup = BeautifulSoup(response.text,"html.parser")
        # viewstate = self.hidden(soup, "__VIEWSTATE")
        # viewstate_gen = self.hidden(soup, "__VIEWSTATEGENERATOR")
        # event_validation = self.hidden(soup, "__EVENTVALIDATION")
        page_flag=True
        p = 1
        event_target = ""
        viewstate = self.hidden(soup, "__VIEWSTATE")
        viewstate_gen = self.hidden(soup, "__VIEWSTATEGENERATOR")
        event_validation = self.hidden(soup, "__EVENTVALIDATION")
        scroll_x = soup.find("input", {"name": "__SCROLLPOSITIONX"})
        scroll_y = soup.find("input", {"name": "__SCROLLPOSITIONY"})

        scroll_x_val = scroll_x.get("value") if scroll_x else "0"
        scroll_y_val = scroll_y.get("value") if scroll_y else "0"

        start_dt = datetime.strptime(self.startdate, "%d/%m/%Y")
        end_dt = datetime.strptime(self.end_date, "%d/%m/%Y")

        # Different useful formats
        start_iso = start_dt.strftime("%Y-%m-%d")
        end_iso = end_dt.strftime("%Y-%m-%d")

        start_input = start_dt.strftime("%-m/%-d/%Y")  # 1/31/2025
        end_input = end_dt.strftime("%-m/%-d/%Y")

        start_validation = start_dt.strftime("%Y-%m-%d-00-00-00")
        end_validation = end_dt.strftime("%Y-%m-%d-00-00-00")

        start_calendar = f"[[{start_dt.year},{start_dt.month},{start_dt.day}]]"
        end_calendar = f"[[{end_dt.year},{end_dt.month},{end_dt.day}]]"

        post_data = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",                       # <-- MISSING
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_gen,
            "__SCROLLPOSITIONX": scroll_x_val,        # <-- MISSING
            "__SCROLLPOSITIONY": scroll_y_val,        # <-- MISSING
            "__EVENTVALIDATION": event_validation,
            "ctl00$ContentPlaceHolder1$SearchType": "rbSearchByDocument",
            "ctl00$ContentPlaceHolder1$chkListCourts$0": "on",
            "ctl00$ContentPlaceHolder1$ddlCourts": "2f9a4941-9b55-463d-a622-b6b304b19142",
            "ctl00$ContentPlaceHolder1$txtSearchText": "",
            "ctl00$ContentPlaceHolder1$Stemming": "on",
            "ctl00$ContentPlaceHolder1$Fuzziness": "0",
            "ctl00$ContentPlaceHolder1$dtDocumentFrom": start_iso,
    "ctl00$ContentPlaceHolder1$dtDocumentFrom$dateInput": start_input,

    "ctl00_ContentPlaceHolder1_dtDocumentFrom_dateInput_ClientState":
        f'{{"enabled":true,"emptyMessage":"","validationText":"{start_validation}",'
        f'"valueAsString":"{start_validation}","minDateStr":"1900-01-01-00-00-00",'
        f'"maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":"{start_input}"}}',

    "ctl00_ContentPlaceHolder1_dtDocumentFrom_calendar_SD": start_calendar,
    "ctl00_ContentPlaceHolder1_dtDocumentFrom_calendar_AD":
        f'[[1900,1,1],[2099,12,30],{start_calendar.strip("[]")}]',

    "ctl00_ContentPlaceHolder1_dtDocumentFrom_ClientState":
        '{"minDateStr":"1900-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00"}',

    # ---------------- TO DATE ----------------

    "ctl00$ContentPlaceHolder1$dtDocumentTo": end_iso,
    "ctl00$ContentPlaceHolder1$dtDocumentTo$dateInput": end_input,

    "ctl00_ContentPlaceHolder1_dtDocumentTo_dateInput_ClientState":
        f'{{"enabled":true,"emptyMessage":"","validationText":"{end_validation}",'
        f'"valueAsString":"{end_validation}","minDateStr":"1900-01-01-00-00-00",'
        f'"maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":"{end_input}"}}',

    "ctl00_ContentPlaceHolder1_dtDocumentTo_calendar_SD": end_calendar,
    "ctl00_ContentPlaceHolder1_dtDocumentTo_calendar_AD":
        f'[[1900,1,1],[2099,12,30],{end_calendar.strip("[]")}]',

    "ctl00_ContentPlaceHolder1_dtDocumentTo_ClientState":
        '{"minDateStr":"1900-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00"}',
            "ctl00$ContentPlaceHolder1$chkAllFiles": "on",
            "ctl00$ContentPlaceHolder1$btnSearchText": "Search",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl04_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl06_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl08_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl10_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl12_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl14_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl16_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl18_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl20_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl22_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl24_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl26_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl28_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl30_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl32_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl34_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl36_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl38_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl40_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl42_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl44_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl46_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl48_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl50_caseNumberCOA_ClientState": "",
            "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl52_caseNumberCOA_ClientState": "",

            "ctl00_ContentPlaceHolder1_grdDocuments_ClientState": "",
            "ctl00$ContentPlaceHolder1$hdnCount": "",
            "ctl00$ContentPlaceHolder1$hdnMode": "false"
        }
        post_response = session.post(self.url, headers=self.headers,
                                     data=post_data,
                                     proxies=self.proxies)
        # print(post_response.text)
        # print(post_response.status_code)
        soup = BeautifulSoup(post_response.text,
                                           "html.parser")
        cases = self._extract_cases_from_soup(soup)

        for case in cases:
            print(
                f"Date: {case['date']}, Case: {case['docket']}, Link: {case['pdf_url']}")

        next_btn = soup.find("input", {
            "type": "submit",
            "class": "rgPageNext"
        })

        if not next_btn:
            # No next button at all → only 1 page or pagination broken
            page_flag = False

        elif next_btn.get("onclick") == "return false;":
            # Next exists but is disabled → last page
            page_flag = False

        else:
            # Next exists and is active → more pages to fetch
            page_flag = True
            current = soup.find("a",
                                {"class": "rgCurrentPage"})
            next_page = current.find_next(
                "a")  # gives <a> for page 2, 3, ...

            if next_page:
                href = next_page.get("href")
                event_target = href.split("'")[1]


        while event_target:
            viewstate = self.hidden(soup, "__VIEWSTATE")
            viewstate_gen = self.hidden(soup, "__VIEWSTATEGENERATOR")
            event_validation = self.hidden(soup, "__EVENTVALIDATION")
            scroll_x = soup.find("input", {"name": "__SCROLLPOSITIONX"})
            scroll_y = soup.find("input", {"name": "__SCROLLPOSITIONY"})

            scroll_x_val = scroll_x.get("value") if scroll_x else "0"
            scroll_y_val = scroll_y.get("value") if scroll_y else "0"

            post_data3 = {
                "__EVENTTARGET": event_target,
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": viewstate,
                "_VIEWSTATEGENERATOR": viewstate_gen,
                "__SCROLLPOSITIONX": scroll_x_val,
                "__SCROLLPOSITIONY": scroll_y_val,
                "ctl00$ContentPlaceHolder1$SearchType": "rbSearchByDocument",
                "ctl00$ContentPlaceHolder1$chkListCourts$0": "on",
                "ctl00$ContentPlaceHolder1$ddlCourts": "2f9a4941-9b55-463d-a622-b6b304b19142",
                "ctl00$ContentPlaceHolder1$txtSearchText": "",
                "ctl00$ContentPlaceHolder1$Stemming": "on",
                "ctl00$ContentPlaceHolder1$Fuzziness": "0",

                "ctl00$ContentPlaceHolder1$dtDocumentFrom": start_iso,
    "ctl00$ContentPlaceHolder1$dtDocumentFrom$dateInput": start_input,

    "ctl00_ContentPlaceHolder1_dtDocumentFrom_dateInput_ClientState":
        f'{{"enabled":true,"emptyMessage":"","validationText":"{start_validation}",'
        f'"valueAsString":"{start_validation}","minDateStr":"1900-01-01-00-00-00",'
        f'"maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":"{start_input}"}}',

    "ctl00_ContentPlaceHolder1_dtDocumentFrom_calendar_SD": start_calendar,
    "ctl00_ContentPlaceHolder1_dtDocumentFrom_calendar_AD":
        f'[[1900,1,1],[2099,12,30],{start_calendar.strip("[]")}]',

    "ctl00_ContentPlaceHolder1_dtDocumentFrom_ClientState":
        '{"minDateStr":"1900-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00"}',

    # ---------------- TO DATE ----------------

    "ctl00$ContentPlaceHolder1$dtDocumentTo": end_iso,
    "ctl00$ContentPlaceHolder1$dtDocumentTo$dateInput": end_input,

    "ctl00_ContentPlaceHolder1_dtDocumentTo_dateInput_ClientState":
        f'{{"enabled":true,"emptyMessage":"","validationText":"{end_validation}",'
        f'"valueAsString":"{end_validation}","minDateStr":"1900-01-01-00-00-00",'
        f'"maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":"{end_input}"}}',

    "ctl00_ContentPlaceHolder1_dtDocumentTo_calendar_SD": end_calendar,
    "ctl00_ContentPlaceHolder1_dtDocumentTo_calendar_AD":
        f'[[1900,1,1],[2099,12,30],{end_calendar.strip("[]")}]',

    "ctl00_ContentPlaceHolder1_dtDocumentTo_ClientState":
        '{"minDateStr":"1900-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00"}',

                "ctl00$ContentPlaceHolder1$chkAllFiles": "on",

                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl04_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl06_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl08_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl10_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl12_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl14_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl16_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl18_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl20_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl22_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl24_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl26_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl28_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl30_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl32_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl34_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl36_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl38_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl40_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl42_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl44_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl46_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl48_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl50_caseNumberCOA_ClientState": "",
                "ctl00_ContentPlaceHolder1_grdDocuments_ctl00_ctl52_caseNumberCOA_ClientState": "",

                "ctl00_ContentPlaceHolder1_grdDocuments_ClientState": "",
                "ctl00$ContentPlaceHolder1$hdnCount": "",
                "ctl00$ContentPlaceHolder1$hdnMode": "false"
            }
            post_response = session.post(self.url, headers=self.headers,
                                         data=post_data3,
                                         proxies=self.proxies)
            # print(post_response.text)
            # print(post_response.status_code)
            soup = BeautifulSoup(post_response.text,
                                 "html.parser")
            next_cases = self._extract_cases_from_soup(soup)
            cases.extend(next_cases)

            for case in next_cases:
                print(
                    f"Date: {case['date']}, Case: {case['docket']}, Link: {case['pdf_url']}")
            next_btn = soup.find("input", {
                "type": "submit",
                "class": "rgPageNext"
            })

            if not next_btn:
                # No next button at all → only 1 page or pagination broken
                page_flag = False
                event_target = None

            elif next_btn.get("onclick") == "return false;":
                # Next exists but is disabled → last page
                page_flag = False
                event_target = None

            else:
                # Next exists and is active → more pages to fetch
                page_flag = True
                current = soup.find("a",
                                    {"class": "rgCurrentPage"})
                next_page = current.find_next(
                    "a")
                event_target = None# gives <a> for page 2, 3, ...

                if next_page:
                    href = next_page.get("href")
                    event_target = href.split("'")[1]

    def _process_html(self):
        pass


    def _extract_cases_from_soup(self, soup):
        """
        Extracts case date, number, and link from the HTML soup of the page.
        Returns a list of dictionaries with keys: 'date', 'case_number', 'link'.
        """
        cases = []
        row = soup.find("tr", id="ctl00_ContentPlaceHolder1_grdDocuments_ctl00__0")

        if not row:
            return cases  # return empty list if no rows found

        tbody = row.find_parent("tbody")
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue

            # Extract date
            case_date = tds[1].get_text(strip=True)

            # Extract case number and link
            case_td = tds[4]
            case_a = case_td.find("a")
            if case_a:
                case_number = str(case_a.get_text(strip=True))
                case_href = case_a.get("href")
                case_url = f"https://search.txcourts.gov/Case.aspx?cn={case_number}&coa=cossup"
                # print(case_url)
                case_response = requests.get(url=case_url,headers=self.headers,proxies=self.proxies)
                # print(case_response.status_code)
                case_soup = BeautifulSoup(case_response.text,"html.parser")
                # print(case_response.text)
                for row in case_soup.find_all("tr"):
                    tds = row.find_all("td")

                    if len(tds) >= 5:
                        # Check if 2nd td contains 'opinion issued' (case-insensitive)
                        if "opinion issued" in tds[1].get_text(
                            strip=True).lower():
                            # 3rd td → disposition
                            disposition = tds[2].get_text(strip=True)

                            # 5th td → PDF links
                            pdf_td = tds[4]
                            first_link_tag = pdf_td.select_one("td.docLink a")

                            if first_link_tag:
                                pdf_url = first_link_tag["href"]
                                if not pdf_url.startswith("https"):
                                    pdf_url = "https://search.txcourts.gov/"+pdf_url
                                print(pdf_url)
                            else:
                                pdf_url = ""
                                print(f"pdf url is null for {case_number} ,  case_date : {case_date}")

                            print("Disposition:", disposition)
                            print("PDF URLs:", pdf_url)

                            panel = case_soup.find("div", id="panelTextSelection")
                            if not panel:
                                raise ValueError(
                                    "panelTextSelection not found")

                            # Step 2: Find all rows inside this panel
                            rows = panel.find_all("div", class_="row-fluid")

                            plaintiff = ""
                            defendant = ""

                            for row in rows:
                                label = row.find("label", class_="form1")
                                span10 = row.find("div", class_="span10")
                                if label and span10:
                                    label_text = label.get_text(
                                        strip=True).rstrip(':').lower()
                                    text = span10.get_text(strip=True)
                                    if label_text == "style":
                                        plaintiff = text
                                    elif label_text == "v.":
                                        defendant = text

                            # Step 3: Combine as title
                            if defendant:
                                title = f"{plaintiff} v. {defendant}"
                            else :
                                title = plaintiff

                            print(f"Title: {title} , date : {case_date}", )

                            coa_info_div = case_soup.find("div",
                                                     id="ctl00_ContentPlaceHolder1_divCOAInfo")

                            coa_info_dict = {}
                            for row in coa_info_div.find_all("div",
                                                             class_="row-fluid"):
                                label_tag = row.find("label", class_="form1")
                                value_tag = row.find("div", class_="span4")
                                if label_tag and value_tag:
                                    label = label_tag.get_text(strip=True)
                                    value = value_tag.get_text(
                                        strip=True).replace("\xa0", " ")
                                    coa_info_dict[label] = value

                            trial_dict = {}

                            trial_panel = case_soup.find("div",
                                                    id="ctl00_ContentPlaceHolder1_pnlTrialCourt2")
                            if trial_panel:
                                rows = trial_panel.find_all("div",
                                                            class_="row-fluid")
                                for row in rows:
                                    label_div = row.find("label",
                                                         class_="form1")
                                    value_div = row.find("div", class_="span4")
                                    if label_div and value_div:
                                        key = label_div.get_text(strip=True)
                                        value = value_div.get_text(strip=True)
                                        trial_dict[key] = value
                            combined_dict = {
                                "Court of Appeals Information": coa_info_dict,
                                "Trial Court Information": trial_dict
                            }
                            if not case_number:
                                continue
                            self.lower_court_info.append(combined_dict)
                            self.cases.append({
                                "name":title,
                                'date':case_date,
                                'docket':case_number,
                                'url':pdf_url,
                                'disposition':disposition,
                                'status':self.status,
                                "lower_court_info":self.lower_court_info
                            })
            else:
                case_number = None
                case_href = None

            print(f"date : {case_date} , case_number : {case_number}")


        return cases

    def _process_html(self):
        pass

    def _get_lower_court_info(self):
        """
        Returns the lower court information list.
        If the list is empty, returns an empty list.
        """
        return self.lower_court_info if self.lower_court_info else []

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.startdate = "01/12/2025"
        self.end_date = "31/12/2025"
        self.parse()
        return len(getattr(self, "cases", []))

    def get_class_name(self):
        return 'tex_new'

    def get_court_name(self):
        return 'Supreme Court of Texas'

    def get_court_type(self):
        return 'state'

    def get_state_name(self):
        return 'Texas'

