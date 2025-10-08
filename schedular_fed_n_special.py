import os
import importlib
import schedule
import time
import logging
from datetime import datetime
import traceback
from casemine.casemine_util import CasemineUtil

FOLDERS_TO_SCAN = ["juriscraper/opinions/united_states/federal_appellate", "juriscraper/opinions/united_states/federal_special"]
RESTRICTED_CLASSES = {'acca_memorandum', 'acca_p', 'acca_summary', 'afcca', 'ag', 'armfor', 'uscgcoca', 'fisc', 'fiscr', 'nmcca', 'uscfc_vaccine_u', 'uscfc_u', 'uscfc', 'uscfc_vaccine', # Federal
    'ca3_u', 'cadc_u', 'cadc_pi'}


def setup_logging():
    today = datetime.now().strftime('%Y-%m-%d')
    log_dir = os.getenv("LOG_DIR", "../juriscraper-17-09-2024/logs")
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f"fed_n_special_{today}.log")

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("juriscraper_scheduler")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def get_module_name(file_path):
    return file_path.replace('.py', '').replace('/', '.')


def run_site(site_class, class_name, logger):
    if CasemineUtil is None:
        logger.error("CasemineUtil module not available. Skipping execution.")
        return

    try:
        site = site_class.Site()
        court_name = site.get_court_name()
        state_name = site.get_state_name()
        initial_crawl_date = site.get_crawl_till() or "No previous crawl date"

        start_time = datetime.now()
        logger.info(f"************[{class_name}, {court_name}, {state_name}]************")
        logger.info(f"Start: {start_time.strftime('%d/%m/%Y %I:%M:%S %p')}, From: {initial_crawl_date}")

        site.execute_job(class_name)
        court_type = site.get_court_type()

        total_records = unique_records = duplicate_records = 0

        for opinion in site:
            try:
                date = opinion.get('case_dates')
                opinion_date = date.strftime('%d/%m/%Y')
                if CasemineUtil.compare_date(opinion_date, site.crawled_till) == 1:
                    site.crawled_till = opinion_date
                year = int(opinion_date.split('/')[2])

                data = process_opinion_data(opinion, opinion_date, year, court_name, court_type, class_name, state_name)
                try:
                    site._process_opinion(data)
                    unique_records += 1
                except Exception as e:
                    if "Judgment already Exists" in str(e):
                        duplicate_records += 1
                    else:
                        logger.error(f"Opinion error: {e}")
                        logger.error(traceback.format_exc())
                total_records += 1
            except Exception as e:
                logger.error(f"Processing opinion error: {e}")
                logger.error(traceback.format_exc())

        site.set_crawl_config_details(class_name, site.crawled_till)
        end_time = datetime.now()
        logger.info(f"End: {end_time.strftime('%d/%m/%Y %I:%M:%S %p')} at {site.crawled_till}")
        logger.info(f"Processed: {total_records}, Inserted: {unique_records}, Duplicates: {duplicate_records}")

    except Exception as e:
        logger.error(f"Run error for {class_name}: {e}")
        logger.error(traceback.format_exc())


def process_opinion_data(opinion, opinion_date, year, court_name, court_type, class_name, state_name):
    def check_none(field): return '' if field is None else field

    docket = opinion.get('docket_numbers')
    if docket:
        try:
            docket = eval(docket) if docket != '' else []
        except:
            docket = []
    else:
        docket = []

    data = {
        'title': check_none(opinion.get('case_names')),
        'pdf_url': check_none(opinion.get('download_urls')),
        'date': datetime.strptime(opinion_date, "%d/%m/%Y"),
        'case_status': check_none(opinion.get('precedential_statuses')),
        'docket': docket,
        'date_filed_is_approximate': check_none(opinion.get('date_filed_is_approximate')),
        'judges': opinion.get('judges') or [],
        'citation': opinion.get('citations') or [],
        'parallel_citation': opinion.get('parallel_citations') or [],
        'summary': check_none(opinion.get('summaries')),
        'lower_court': check_none(opinion.get('lower_courts')),
        'child_court': check_none(opinion.get('child_courts')),
        'adversary_number': check_none(opinion.get('adversary_numbers')),
        'division': check_none(opinion.get('divisions')),
        'disposition': check_none(opinion.get('dispositions')),
        'cause': check_none(opinion.get('causes')),
        'docket_attachment_number': opinion.get('docket_attachment_numbers') or [],
        'docket_document_number': opinion.get('docket_document_numbers') or [],
        'nature_of_suit': check_none(opinion.get('nature_of_suit')),
        'lower_court_number': check_none(opinion.get('lower_court_numbers')),
        'lower_court_judges': opinion.get('lower_court_judges') or [],
        'author': check_none(opinion.get('authors')),
        'per_curiam': check_none(opinion.get('per_curiam')),
        'type': check_none(opinion.get('types')),
        'joined_by': check_none(opinion.get('joined_by')),
        'other_date': check_none(opinion.get('other_dates')),
        'blocked_statuses': check_none(opinion.get('blocked_statuses')),
        'case_name_shorts': check_none(opinion.get('case_name_shorts')),
        'opinion_type': check_none(opinion.get('opinion_types')),
        'html_url': check_none(opinion.get('html_urls')),
        'response_html': check_none(opinion.get('response_htmls')),
        'crawledAt': datetime.now(),
        'processed': 333,
        'court_name': court_name,
        'court_type': court_type,
        'class_name': class_name,
        'year': year,
    }

    if court_type == 'Federal':
        data['circuit'] = state_name
        data['teaser'] = check_none(opinion.get("teasers"))
    else:
        data['state'] = state_name

    return data


def discover_and_run_sites():
    logger = setup_logging()
    logger.info("Starting full site discovery run...")

    processed_classes = set()
    total_classes = 0
    successful_classes = set()
    error_classes = set()
    skipped_classes = set()

    for folder in FOLDERS_TO_SCAN:
        try:
            files = [f for f in os.listdir(folder) if f.endswith('.py') and f != '__init__.py']
            total_classes += len(files)

            for file in files:
                try:
                    module_path = os.path.join(folder, file)
                    module_name = get_module_name(module_path)
                    class_name = module_name.split('.')[-1]

                    if class_name in RESTRICTED_CLASSES:
                        skipped_classes.add(class_name)
                        logger.info(f"Skipping: {class_name}")
                        continue

                    module = importlib.import_module(module_name)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and attr_name == 'Site':
                            try:
                                run_site(module, class_name, logger)
                                successful_classes.add(class_name)
                            except Exception as e:
                                error_classes.add(class_name)
                                logger.error(f"Class error: {class_name} - {e}")
                                logger.error(traceback.format_exc())
                            processed_classes.add(class_name)
                            break
                except Exception as e:
                    logger.error(f"File error: {file} - {e}")
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Folder scan error: {folder} - {e}")
            logger.error(traceback.format_exc())

    logger.info("\n********* SUMMARY *********")
    logger.info(f"Total: {total_classes}, Success: {len(successful_classes)}, Errors: {len(error_classes)}, Skipped: {len(skipped_classes)}")
    logger.info("****************************\n")


def main():
    while True:
        discover_and_run_sites()
        time.sleep(24 * 60 * 60)  # sleep for one day


if __name__ == "__main__":
    main()