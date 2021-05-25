
"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""

from builtins import zip, str, range

import pdb, os, csv, re, io, json
import urllib.request, urllib.error, urllib.parse

from bs4 import BeautifulSoup
from tqdm import tqdm
from shutil import rmtree
from nltk.tokenize import word_tokenize, sent_tokenize


# PARAMS
SUMMARY_DIR = '../../raw_summaries/cliffnotes/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210312193150/https://www.cliffsnotes.com/'

# Summary list info
summary_list_file = "literature_links.tsv"

errors_file = open("section_errors.txt","w")

def wrap_data(name, summary, analysis, url):
    return {
        "name": name,
        "summary": summary,
        "analysis": analysis,
        "url": url
    }


def scrape_section_continuation(parent_soup, section_header):
    section_data = parent_soup.find("article", {"class": "copy"})

    # For some links, the html structure is different
    if section_data == None:
        section_data = parent_soup.find("div", {"class": "contentArea"})
        link = parent_soup.findAll("a", {"class": "cf-next icon-Next_Arrow"}, href=True)[-1]
        next_link_title = link.findAll("p")[-1].text.strip()
    else:
        link = parent_soup.findAll("a", {"class": "nav-bttn-filled"}, href=True)[-1]
        next_link_title = link.findAll("span")[-1].text.strip()

    section_paragraphs = [paragraph.text.strip() for paragraph in section_data.findAll("p", recursive=False)]
    
    if not section_header == next_link_title:
        return section_paragraphs
    else:
        soup = BeautifulSoup(urllib.request.urlopen(urllib.parse.urljoin(MAIN_SITE, link.get("href"))), "html.parser")
        return section_paragraphs + scrape_section_continuation(soup, section_header)

# Get contents of the summary file
with open(summary_list_file, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    summary_infos = list(reader)

# For each summary info
for k, (title, page_url) in enumerate(summary_infos):
    print('\n>>> {}. {} <<<'.format(k, title))

    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)
    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory, skipping.")
        continue

    # Parse page
    soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")

    # Parse general summary
    navigation_links = soup.find("section", {"class": "secondary-navigation"})
    overview_links = [urllib.parse.urljoin(MAIN_SITE, link.get("href")) for link in navigation_links.findAll("a") if re.match(".*book-summary$", link.get("href"))]
    section_links = [urllib.parse.urljoin(MAIN_SITE, link.get("href")) for link in navigation_links.findAll("a") if "summary-and-analysis" in link.get("href")][1:]

    for index, overview in enumerate(overview_links):
        try:
            soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
            overview_data = soup.find("article", {"class": "copy"})
            overview_paragraphs = filter(None, [paragraph.text.strip() for paragraph in overview_data.findAll("p", recursive=False)])
            overview_text = "<PARAGRAPH>".join(overview_paragraphs).replace("Continued on next page...", "")
            overview_data = wrap_data("Overview", overview_text, None, overview)

            output_fname = os.path.join(specific_summary_dir, 'overview.txt')
            with open(output_fname, 'w', encoding="utf-8") as f:
                f.write(json.dumps(overview_data))
        except Exception:
            print("No book summary")

            
    for index, section in enumerate(section_links):
        try:
            soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
            section_header = soup.title.string.strip()

            section_paragraphs = list(filter(None, scrape_section_continuation(soup, section_header)))

        except Exception as e:

            print (section, e)
            errors_file.write(section + "\t" + str(e) + "\n")

        section_text = "<PARAGRAPH>".join(section_paragraphs).replace("Continued on next page...", "")

        # clean up and parse
        if "Summary\n" in section_text and "Analysis\n" in section_text:
            section_text_split = section_text.split("Analysis\n")
            summary_text = "".join([summary for summary in section_text_split if "Summary\n" in summary]).replace("Summary\n", "").strip()
            analysis_text = "".join([analysis for analysis in section_text_split if "Summary\n" not in analysis]).replace("Analysis\n", "").strip()
        else:
            summary_text = section_text.replace("Summary\n", "").strip()
            analysis_text = None

        section_data = wrap_data(section_header, summary_text, analysis_text, section)
        output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % index)
        with open(output_fname, 'w', encoding="utf-8") as f:
            f.write(json.dumps(section_data))
