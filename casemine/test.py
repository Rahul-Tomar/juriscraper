from juriscraper.opinions.united_states.federal_special import ptab, ttab
from juriscraper.opinions.united_states.state import ariz, arizctapp_div_1, massappct, mich, mich_orders, mo_min_or_sc, nyappdiv1_motions, ny_new, nyappdiv2_motions, nyappdiv3_motions, nyappdiv4_motions, nyappdiv_1st_new, nyappdiv_2nd_new, nyappdiv_3rd_new, nyappdiv_4th_new, nyappterm1_motions, nyappterm2_motions, nyappterm_1st_new, nyappterm_2nd_new, nycityct, nycivct, nycivil_motions, nycivil_motions, nyclaimsct, nycountyct, nycrim_motions, orctapp

# Create a site object
site = mich_orders.Site()

site.execute_job("mich_orders")

# site.parse()

# Print out the object
# print(str(site))

# Print it out as JSON
# print(site.to_json())

# Iterate over the item
i=1
for opinion in site:
    print(opinion)
    # print(f"{i} {opinion.get('case_dates')} || {opinion.get('case_names')} || {opinion.get('download_urls')} || {opinion.get('docket_numbers')}")
    i=i+1

# print(f"total docs - {i}")
