# from juriscraper.opinions.united_states.federal_special import ptab, ttab
# from juriscraper.opinions.united_states.state import ariz, arizctapp_div_1, massappct, mich, mich_orders, mo_min_or_sc, nyappdiv1_motions, ny_new, nyappdiv2_motions, nyappdiv3_motions, nyappdiv4_motions, nyappdiv_1st_new, nyappdiv_2nd_new, nyappdiv_3rd_new, nyappdiv_4th_new, nyappterm1_motions, nyappterm2_motions, nyappterm_1st_new, nyappterm_2nd_new, nycityct, nycivct, nycivil_motions, nycivil_motions, nyclaimsct, nycountyct, nycrim_motions, orctapp
#
# # Create a site object
# site = mich_orders.Site()
#
# site.execute_job("mich_orders")
#
# # site.parse()
#
# # Print out the object
# # print(str(site))
#
# # Print it out as JSON
# # print(site.to_json())
#
# # Iterate over the item
# i=1
# for opinion in site:
#     print(opinion)
#     # print(f"{i} {opinion.get('case_dates')} || {opinion.get('case_names')} || {opinion.get('download_urls')} || {opinion.get('docket_numbers')}")
#     i=i+1
#
# # print(f"total docs - {i}")



import os
import mimetypes
import cloudscraper
from PyPDF2 import PdfReader

SAVE_DIR = "/home/gaugedata/Downloads/"


def is_valid_pdf(file_path: str) -> bool:
    """
    Validates that the file is a real PDF using PyPDF2.
    Removes the file automatically if invalid.
    """
    try:
        with open(file_path, "rb") as f:
            PdfReader(f)  # Will throw error if PDF is invalid
        return True
    except Exception:
        # Delete corrupted or non-PDF file
        if os.path.exists(file_path):
            os.remove(file_path)
        return False


def download_pdf(url: str, filename: str = None) -> str:
    """
    Downloads PDF from any URL using cloudscraper.
    Ensures valid PDF and saves in SAVE_DIR.
    """
    scraper = cloudscraper.create_scraper()

    # Send request
    response = scraper.get(url, stream=True)
    response.raise_for_status()

    # Try to detect filename
    if not filename:
        filename = (
            url.split("/")[-1].split("?")[0]
            or "downloaded_file.pdf"
        )

    # Force .pdf extension
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    # Build full file path
    file_path = os.path.join(SAVE_DIR, filename)

    # Download content
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)

    # Validate MIME type (optional but strong check)
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type != "application/pdf":
        # Still verify using PyPDF2 in case server gave wrong MIME
        if not is_valid_pdf(file_path):
            raise Exception("Downloaded file is not a valid PDF!")

    # Final verification
    if not is_valid_pdf(file_path):
        raise Exception("Invalid or corrupted PDF removed automatically.")

    print(f"PDF downloaded successfully: {file_path}")
    return file_path


# -----------------------------
# Example Call
# -----------------------------
if __name__ == "__main__":
    url = "https://www.vermontjudiciary.org/media/18598"
    download_pdf(url)
