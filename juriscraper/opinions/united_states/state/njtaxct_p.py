import re
from datetime import datetime

from juriscraper.AbstractSite import logger
from juriscraper.lib.string_utils import titlecase
from juriscraper.opinions.united_states.state import nj


class Site(nj.Site):
    first_opinion_date = datetime(2017, 5, 25)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.base_url = self.url = (
            "https://www.njcourts.gov/attorneys/opinions/published-tax"
        )
        self.status = "Published"

    def _process_html(self) -> None:
        """Process the html and extract out the opinions

        :return: None
        """
        for row in self.html.xpath("//div[@class='card-body']"):
            container = row.xpath(".//a[@class='text-underline-hover']")
            if not container:
                logger.warning(
                    "Skipping row with no URL: %s",
                    re.sub(r"\s+", " ", row.text_content()),
                )
                continue

            url = container[0].xpath("@href")[0]
            # name is sometimes inside a span, not inside the a tag
            name_content = container[0].xpath("string(.)")
            name_str, _, _ = name_content.partition("(")

            docket = row.xpath(
                './/*[contains(@class, "one-line-truncate me-1 mt-1")]/text()')[
                0
            ].strip()

            date = row.xpath(
                ".//div[@class='col-lg-12 small text-muted mt-2']/text()"
            )[0]

            if not str(url).__contains__("https://www.njcourts.gov"):
                url="https://www.njcourts.gov"+url
                
            case = {
                "date": date,
                "docket": [docket],
                "name": titlecase(name_str.strip()),
                "url": url,
            }

            if self.status == "Published":
                summary = row.xpath(".//div[@class='modal-body']/p/text()")
                case["summary"] = "\n".join(summary)

            self.cases.append(case)

    def get_class_name(self):
        return "njtaxct_p"

    def get_court_name(self):
        return "New Jersey Tax Court"
