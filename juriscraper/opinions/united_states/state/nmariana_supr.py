"""
Scraper for the Tennessee Court of Criminal Appeals
CourtID: tennctcrimapp
Court Short Name: Tenn. Ct. Crim. App.
"""
from datetime import datetime

from juriscraper.opinions.united_states.state import tenn, nmariana


class Site(nmariana.Site):
    court = "Superior"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _process_html(self):
        rows = self.html.xpath(
            "//table[contains(@class, 'doctable')]//tbody/tr"
        )

        for row in rows:
            cells = row.xpath("./td")

            if len(cells) < 6:
                continue

            name = cells[0].text_content().strip()
            docket_text = cells[1].text_content().strip()
            order_text = cells[2].text_content().strip()

            case_date = cells[3].get("data-sort")

            if not case_date:
                case_date = cells[3].text_content().strip()

            judge_text = cells[4].text_content().strip()

            pdf_links = cells[5].xpath(
                ".//a[contains(@class, 'pdf-link')]/@href"
            )

            if not pdf_links:
                pdf_links = cells[5].xpath(
                    ".//a[contains("
                    "translate(@href, "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                    "'abcdefghijklmnopqrstuvwxyz'), "
                    "'.pdf')]/@href"
                )

            if not pdf_links:
                continue

            pdf_url = pdf_links[0].strip()

            if not pdf_url:
                continue

            if not pdf_url.startswith(("http://", "https://")):
                pdf_url = "https://cnmilaw.gov" + pdf_url

            docket = []

            if docket_text:
                docket = [docket_text]

            judge = []

            if judge_text:
                judge = [judge_text]

            self.cases.append(
                {
                    "name": name,
                    "citation": [],
                    "date": case_date,
                    "judge": judge,
                    "author": judge_text,
                    "url": pdf_url,
                    "docket": docket,
                    "summary": order_text,
                }
            )

    def get_court_name(self):
        return "Superior Court of Northern Mariana Islands"

    def get_court_type(self):
        return "state"

    def get_state_name(self):
        return "Northern Mariana Islands"

    def get_class_name(self):
        return "nmariana_supr"
