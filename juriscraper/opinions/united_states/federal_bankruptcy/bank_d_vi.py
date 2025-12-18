import sys
import re
from datetime import datetime
from lxml import html
from casemine.casemine_util import CasemineUtil
from juriscraper.OpinionSiteLinear import OpinionSiteLinear

if sys.version_info[0] < 3:
    import urlparse
    urljoin = urlparse.urljoin
else:
    from urllib.parse import urljoin


class Site(OpinionSiteLinear):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Published"

    def _process_html(self):
        rows = self.html.xpath('//div[contains(@class,"views-row")]')
        if not rows:
            return

        for row in rows:
            # --- Title / URL ---
            title_anchor = row.xpath(
                './/div[contains(@class,"views-field-title")]//a'
            )
            if not title_anchor:
                continue

            anchor = title_anchor[0]
            full_title = " ".join(anchor.xpath('.//text()')).strip()

            pdf_url = anchor.get("href", "").strip()
            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = urljoin("https://www.vid.uscourts.gov", pdf_url)

            # --- Date ---
            date_text = ""
            curr_date = ""
            date_tag = anchor.xpath(
                './/span[contains(@class,"date-display-single")]/text()'
            )
            if date_tag:
                date_text = date_tag[0].strip()
                try:
                    curr_date = datetime.strptime(
                        date_text, "%m/%d/%Y"
                    ).strftime("%d/%m/%Y")
                except:
                    curr_date = ""

            if curr_date:
                try:
                    if CasemineUtil.compare_date(self.crawled_till, curr_date) == 1:
                        return "STOP"
                except:
                    pass

            # --- Clean case name (remove date span text) ---
            # --- Clean case name (remove docket + date) ---
            name = full_title

            docket = []

            patterns = [
                r'\d+:\d{2}-(?:cv|cr)-\d+(?:-[A-Z]+)*',
                # 1:23-cv-00059-WAL-EAH
                r'\d+-\d{2}-(?:cv|cr)-\d+(?:-[A-Z]+)*',
                # 3-24-cv-00023-RAM-GAT
                r'\d{2}-(?:cv|cr)-\d+(?:-[A-Z]+)*',  # 21-cv-241-MEM-EAH
                r'\d{3}-(?:cv|cr)-\d+(?:-[A-Z]+)*',  # 325-cr-36-RAM-EAH
            ]

            for pat in patterns:
                docket.extend(re.findall(pat, full_title, flags=re.I))

            # normalize 3-24-cv-00023 → 3:24-cv-00023
            normalized = []
            for d in docket:
                if ':' not in d and re.match(r'\d+-\d{2}-', d):
                    p = d.split('-', 1)
                    d = f"{p[0]}:{p[1]}"
                normalized.append(d.upper())

            docket = list(dict.fromkeys(normalized))

            if any(':' in d for d in docket):
                docket = [d for d in docket if ':' in d]

            # remove date at end
            name = re.sub(r'\s+\d{2}/\d{2}/\d{4}$', '', name)

            # remove docket numbers like 1:23-cv-00059-WAL-EAH or 3:25-cr-0035
            name = re.sub(
                r',?\s*(?:\d+:\d{2}|\d+-\d{2}|\d{2}|\d{3})-(?:cv|cr)-\d+(?:-[A-Z]+)*',
                '',
                name,
                flags=re.I
            )

            # remove trailing "Case No."
            name = re.sub(r'\s*Case\s+No\.?\s*$', '', name, flags=re.I)
            name = name.strip(" ,")

            # --- Docket extraction ---
            # docket = re.findall(
            #     r'\d+:\d{2}-(?:cv|cr)-\d+[-A-Z]*', name, flags=re.I
            # )

            # --- Judge ---
            judge = ""
            judge_tag = row.xpath(
                './/address/em[contains(text(),"Author")]/text()'
            )
            if judge_tag:
                judge = judge_tag[0].replace("Author:", "").strip()

            # --- Summary (not provided on this site) ---
            summary = ""

            self.cases.append({
                "name": name,
                "url": pdf_url,
                "docket": docket,
                "date": date_text,
                "judge": [judge] if judge else [],
                "summary": summary
            })

    def crawling_range(self, start_date: datetime, end_date: datetime) -> int:
        base = "https://www.vid.uscourts.gov"
        next_url = "/judges-info/opinions"

        while next_url:
            self.downloader_executed = False
            self.url = urljoin(base, next_url)
            self.parse()

            next_link = self.html.xpath(
                '//li[contains(@class,"pager__item--next")]/a/@href'
            )
            next_url = next_link[0] if next_link else None

        return len(self.cases)

    def get_class_name(self):
        return "bank_d_vi"

    def get_court_type(self):
        return 'Bankruptcy'

    def get_state_name(self):
        return "3d Circuit"

    def get_court_name(self):
        return "Bankruptcy Court District of the Virgin Islands"
