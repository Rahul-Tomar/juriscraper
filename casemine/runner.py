import ast
from datetime import datetime

from casemine.casemine_util import CasemineUtil
# from juriscraper.opinions.united_states.federal_district import testtt
from juriscraper.opinions.united_states.state import arkctapp, mich_orders, \
    ny_new, nyappdiv1_motions, nyappdiv2_motions, nyappdiv4_motions, \
    nyappdiv_1st_new, nyappdiv_2nd_new, nyappdiv_3rd_new, nyappdiv_4th_new, \
    nyappterm1_motions, nyappterm_1st_new, nyappterm_2nd_new, nycivil_motions, \
    nycrim_motions, pasuperct, mass, nycityct, ga_granted, okla, \
    nysupct_commercial, kan_p, nycrimct, nyjustct, nh_u, guam, connappct, \
    lactapp_1, fla_new, alaskactapp_mo, texapp_4, kan_u, nyfamct, conn, \
    mo_min_or_sc, nh_p, fla, texcrimapp, texapp_6, ohioctapp_12, texapp_14, \
    oklacivapp, ark_admin_law, ohio, texapp_7, ohioctapp_1, sd, texag, \
    vtsuperct_environmental, ohioctapp_4, wva, kanctapp_u, ny, ariz_2, \
    arizctapp_div_1, ariz, massappct_u, lactapp_new, cal, nyappterm2_motions, \
    ga_interlocutory, haw, kanctapp_p, minn, tenn, tennctapp, hawapp, \
    tenncrimapp, la_ag, kyctapp, vtsuperct_civil, ohioctapp_10, \
    neb_ctapp_all_op, ohioctcl_beginningofyear, texapp_8, arizctapp_div_2, \
    vtsuperct_probate, calctapp_3rd, me_orders, texapp_9, gactapp, texapp_12, \
    calctapp_new_rg, me, ohioctapp_3, minnctapp_u, calctapp_4th_div1, \
    fladistctapp_2, mdctspecapp, nj, wis_ordr, oklaag, deljustpeacect, \
    delaware, nm, iowa, wash_ag, iowactapp, ark, nevapp, delfamct, delctcompl, \
    nmctapp, nev_u, la, nev, colo, minnctapp_p, idaho_civil, \
    idahoctapp_criminal, alaska, delch, delsuperct, ariz_tax, colo_u, \
    coloctapp, coloctapp_u, fladistctapp_1, fladistctapp_3, fladistctapp_4, \
    fladistctapp_5, fladistctapp_6, orsc, texapp_11, tex, washctapp_u, \
    washctapp_p, alaska_mo, ky, calctapp_new, mo, nc, miss, ohioctapp_9, neb, \
    nmariana, calctapp_app_div, ga_discretionary, illappct, michctapp_orders, \
    washctapp_p_inpart, njtaxct_u, calctapp_new_u, ohioctapp_8, mont, wash, \
    wvactapp, nebctapp, calctapp_1st, dc, njsuperctappdiv_u, alaskactapp_sd, \
    massappct, njsuperctappdiv_p, nevapp_u, tex_new, nycountyct, \
    nyappdiv3_motions, orctapp, nysupct, ala, alaska_orders, alaskactapp, \
    alaskactapp_bo, alaskactapp_orders, calctapp_2nd, calctapp_4th_div2, \
    calctapp_4th_div3, calctapp_5th, calctapp_6th, calag, ga, idaho_criminal, \
    idahoctapp_civil, idahoctapp_per_curiam, idahoctapp_u, ill, mass_dia, \
    masslandct, md, md_unreported, mdag, mesuperct, mich, michctapp, minnag, \
    neb_ag, neb_sup_all_op, ncctapp, nd, wis, wisctapp, vt, vt_criminal, \
    vtsuperct_family, va, vactapp_p, utah, utahctapp, sc, scapp_p, scctapp, \
    scscop_p, ri, ri_ordr, ri_supr, ri_trf_tri, pa, pacommwct, nydistct, \
    oklacrimapp, cal_work, alacivapp, ark_work_comp, ark_ag, nyappdiv_1st, \
    cal_work_panel, nycivct, nyclaimsct, nysurct, cal_work_sigpanel, \
    conn_super, tex_jpml, conn_work

# Create a site object
site = wisctapp.Site()

site.execute_job("wisctapp")

# print(f"Total judgements: {site.cases.__len__()}")

# Iterate over the items
class_name = site.get_class_name()
court_name = site.get_court_name()
court_type = site.get_court_type()
state_name = site.get_state_name()

def check_none(field):
    if field is None:
        return ''
    else:
        return field

ctr = 1
for opinion in site:
    # print(opinion)
    date = opinion.get('case_dates')
    opinion_date = date.strftime('%d/%m/%Y')
    res = CasemineUtil.compare_date(opinion_date, site.crawled_till)
    if res == 1:
        site.crawled_till = opinion_date
    year = int(opinion_date.split('/')[2])
    jud = opinion.get('judges')
    if jud is None:
        jud = []

    citation = opinion.get('citations')
    if citation is None or citation == ['']:
        citation = []

    docket = opinion.get('docket_numbers')
    if docket is not None:
        if docket == '':
            docket = []
        else:
            try:
                # Try to evaluate as Python literal
                docket = ast.literal_eval(docket)
            except (SyntaxError, ValueError):
                # If it fails, just use it as a string
                docket = [str(docket)]

    else:
        docket = []


    revision_status = opinion.get('revision_status')
    if revision_status is not None:
        try:
            revision_status = int(revision_status)  # type cast to integer
        except ValueError:
            revision_status = ''  # fallback if it cannot be cast
    else:
        revision_status = ''

    lower_court_info = opinion.get('lower_court_info')
    # if lower_court_info is not None :

    parallel_citation = opinion.get('parallel_citations')
    if parallel_citation is None:
        parallel_citation = []

    lower_court_judges = opinion.get('lower_court_judges')
    if lower_court_judges is None:
        lower_court_judges = []

    dans = opinion.get('docket_attachment_numbers')
    if dans is None:
        dans = []

    ddns = opinion.get('docket_document_numbers')
    if ddns is None:
        ddns = []

    data = {
        # required
        'title' : check_none(opinion.get('case_names')),
        'pdf_url': check_none(opinion.get('download_urls')),
        'date': datetime.strptime(opinion_date,"%d/%m/%Y"),
        'case_status': check_none(opinion.get('precedential_statuses')),
        'docket': docket,
        # optional
        'date_filed_is_approximate': check_none(opinion.get('date_filed_is_approximate')),
        'judges': jud,
        'citation': citation,
        'parallel_citation': parallel_citation,
        'summary': check_none(opinion.get('summaries')),
        'lower_court': check_none(opinion.get('lower_courts')),
        'child_court': check_none(opinion.get('child_courts')),
        'adversary_number': check_none(opinion.get('adversary_numbers')),
        'division': check_none(opinion.get('divisions')),
        'disposition': check_none(opinion.get('dispositions')),
        'cause': check_none(opinion.get('causes')),
        'docket_attachment_number': dans,
        'docket_document_number': ddns,
        'nature_of_suit': check_none(opinion.get('nature_of_suit')),
        'lower_court_number': check_none(opinion.get('lower_court_numbers')),
        'lower_court_judges':lower_court_judges,
        'author': check_none(opinion.get('authors')),
        'per_curiam': check_none(opinion.get('per_curiam')),
        'type': check_none(opinion.get('types')),
        'joined_by': check_none(opinion.get('joined_by')),
        'other_date': check_none(opinion.get('other_dates')),
        # extra
        'blocked_statuses': check_none(opinion.get('blocked_statuses')),
        'case_name_shorts': check_none(opinion.get('case_name_shorts')),
        'opinion_type': check_none(opinion.get('opinion_types')),
        'html_url':check_none(opinion.get('html_urls')),
        'response_html': check_none(opinion.get('response_htmls')),
        # additional
        'revision_status':revision_status,
        'crawledAt': datetime.now(),
        'processed': 333,
        'court_name': court_name,
        'court_type': court_type,
        'class_name': class_name,
        'year': year,
    }

    if isinstance(site, tex_new.Site):
        data['lower_court_info'] = opinion.get('lower_court_info', [])

    if court_type.__eq__('Federal'):
        data["circuit"] = state_name
        data['teaser']= check_none(opinion.get("teasers"))
    else:
        data["state"] = state_name

    print(data)
    flag = site._process_opinion(data)
    if flag:
        print(f'{ctr} - {data}')
    else:
        print(f"{ctr} - !!..Duplicate..!!")
    ctr = ctr + 1

site.set_crawl_config_details(class_name, site.crawled_till)
