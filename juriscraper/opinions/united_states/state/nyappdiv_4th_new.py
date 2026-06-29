import os
from datetime import datetime
from urllib.parse import urljoin

import cloudscraper
import requests
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
import pdfkit
from playwright.sync_api import sync_playwright

from casemine.casemine_util import CasemineUtil
from juriscraper.opinions.united_states.state import nyappdiv_2nd_new


class Site(nyappdiv_2nd_new.Site):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.court_type = "aidxtable_4"
        self.BASE_URL = "https://www.nycourts.gov/reporter/current/index/"
        self.CURRENT_URL = self.BASE_URL + f"{self.court_type}.shtml"
        print("-> ",self.CURRENT_URL)

    def get_court_name(self):
        return "Appellate Division of the Supreme Court, New York"

    def get_class_name(self):
        return "nyappdiv_4th_new"
