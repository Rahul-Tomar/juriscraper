from time import strftime

from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.federal_appellate import scotus_slip

"""
Court Contact: https://www.supremecourt.gov/contact/contact_webmaster.aspx
"""


from datetime import date, datetime

from juriscraper.AbstractSite import logger
from juriscraper.lib.exceptions import InsanityException
from juriscraper.lib.string_utils import convert_date_string
from juriscraper.OpinionSite import OpinionSite


class Site(OpinionSite):
    required_headers = ["Date", "Docket", "Name", "J."]
    expected_headers = required_headers + ["Revised", "R-", "Pt."]
    justices = {
        "A": "Samuel Alito",
        "AB": "Amy Coney Barrett",
        "AS": "Antonin Scalia",
        "B": "Stephen Breyer",
        "BK": "Brett Kavanaugh",
        "D": "Decree",
        "DS": "David Souter",
        "EK": "Elana Kagan",
        "G": "Ruth Bader Ginsburg",
        "JS": "John Paul Stephens",
        "K": "Anthony Kennedy",
        "KJ": "Ketanji Brown Jackson",
        "NG": "Neil Gorsuch",
        "PC": "Per Curiam",
        "R": "John G. Roberts",
        "SS": "Sonia Sotomayor",
        "T": "Clarence Thomas",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.yy = self._get_current_term()
        self.back_scrape_iterable = list(range(5, int(self.yy) + 1))
        self.url_base = "https://www.supremecourt.gov/opinions"
        self.path_table = "//table[@class='table table-bordered']"
        self.path_row = f"{self.path_table}/tr[position() > 1]"
        self.precedential = "In-chambers"
        self.court = "in-chambers"
        self.headers = False
        self.url = False
        self.headers = []
        self.cases = []

    @staticmethod
    def _get_current_term():
        """The URLs for SCOTUS correspond to the term, not the calendar.

        The terms kick off on the first Monday of October, so we use October 1st
        as our cut off date.
        """
        today = date.today()
        term_cutoff = date(today.year, 10, 1)
        if today < term_cutoff:
            # Haven't hit the cutoff, return previous year.
            return int(today.strftime("%y")) - 1  # y3k bug!
        else:
            return today.strftime("%y")

    def _download(self, request_dict={}):
        if not self.test_mode_enabled():
            self.set_url()
        html = super()._download(request_dict)
        self.extract_cases_from_html(html)
        return html

    def set_url(self):
        self.url = f"{self.url_base}/{self.court}.aspx"

    def set_table_headers(self, html):
        # Do nothing if table is missing
        if html.xpath(self.path_table):
            path = f"{self.path_table}//th"
            self.headers = [
                cell.text_content().strip() for cell in html.xpath(path)
            ]
            # Ensure that expected/required headers are present
            if not set(self.required_headers).issubset(self.headers):
                raise InsanityException("Required table column missing")

    def extract_cases_from_html(self, html):
        self.set_table_headers(html)
        for row in html.xpath(self.path_row):
            case = self.extract_case_data_from_row(row)
            if case:
                # Below will raise key error is new judge key encountered (new SC judge appointed)
                jud = self.justices[case["J."]] if case["J."] else ""
                case["judge"] = [jud]
                self.cases.append(case)
                # for revision_data in case["revisions"]:
                #     revision = case.copy()
                case["Date"] = case["Date"]
                try:
                    case["Name_Url"] = case["href"]
                except Exception as e:
                    # print(e)
                    if str(e).__contains__("href"):
                        case["Name_Url"] = case["Name_Url"]
                    else:
                        raise e

                self.cases.append(case['revisions'])

    def extract_case_data_from_row(self, row):
        cell_index = 0
        case = {"revisions": []}
        # Process each cell in row
        for cell in row.xpath("./td"):
            text = cell.text_content().strip()
            # Skip rows with blank first cell
            if cell_index == 0 and not text:
                break
            label = self.headers[cell_index]
            if label in ["R-"]:
                # Ignore some columns that we don't need
                pass
            elif label == "Revised":
                # It is possible for an opinion to have
                # multiple revisions, so we need to iterate
                # over the links the the cell
                for anchor in cell.xpath("a"):
                    case["revisions"].append(
                        {
                            "href": anchor.xpath("@href")[0],
                            "date_string": anchor.text_content(),
                        }
                    )
            else:
                # Handle normal data cells
                if label == "Docket" or label == "Pt." or label == "Citation":
                    if label == "Pt." or label == "Citation":
                        label = "citations"
                    case[label] = [text]
                else:
                    case[label] = text
                href = cell.xpath("./a/@href")
                if href:
                    case[f"{label}_Url"] = href[0]
            cell_index += 1
        return case

    def _get_case_names(self):
        names = []
        for case in self.cases:
            if list(case).__len__() == 0:
                continue
            else:
                names.append(case["Name"])
        #         return [case["Name"] for case in self.cases]
        return names

    def _get_download_urls(self):
        name_urls = []
        for case in self.cases:
            if list(case).__len__()==0:
                continue
            else:
                pdf_url = str(case["Name_Url"])
                if not pdf_url.__contains__(""):
                    pdf_url = "https://www.supremecourt.gov"+pdf_url
                name_urls.append(pdf_url)
        return name_urls

    def _get_case_dates(self):
        converted_dates = []
        # Iterate over each case in self.cases
        for case in self.cases:
            # Apply the convert_date_string function to the date and append the result to the list
            # print(case)
            if list(case).__len__()==0:
                continue
            case_date = case["Date"]
            converted_date = convert_date_string(case_date)
            converted_dates.append(converted_date)
        return converted_dates

    def _get_docket_numbers(self):
        dockets = []
        for case in self.cases:
            if list(case).__len__() == 0:
                continue
            else:
                dockets.append(case["Docket"])
        # return [case["Docket"] for case in self.cases]
        return dockets

    def _get_citations(self):
        citations = []
        for case in self.cases:
            if list(case).__len__() == 0:
                continue
            else:
                citations.append(case["citations"])
        # return [case["citations"] for case in self.cases]
        return citations

    def _get_judges(self):
        judges=[]
        for case in self.cases:
            if list(case).__len__()==0:
                continue
            else:
                judges.append(case["judge"])
        # return [case["judge"] for case in self.cases]
        return judges

    def _get_precedential_statuses(self):
        return [self.precedential] * (int(len(self.cases)/2))

    def _download_backwards(self, d):
        self.yy = str(d if d >= 10 else f"0{d}")
        logger.info(f"Running backscraper for year: 20{self.yy}")
        self.html = self._download()

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        self.parse()
        return 0

    def get_class_name(self):
        return 'scotus_chambers'

    def get_court_name(self):
        return 'U.S. Supreme Court'

    def get_court_type(self):
        return 'Federal'

    def get_state_name(self):
        return "U.S. Supreme Court"
