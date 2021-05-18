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
SUMMARY_DIR = '../../raw_summaries/sparknotes/summaries'
# Summary list info
summary_list_file = "literature_links.tsv"


def wrap_data(name, summary, analysis, url):
    return {
        "name": name,
        "summary": summary,
        "analysis": analysis,
        "url": url
    }

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)

# For each summary info
error_files, error_titles = [], []
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
    overview_url = urllib.parse.urljoin(page_url, "summary")
    soup = BeautifulSoup(urllib.request.urlopen(overview_url), "html.parser")

    # Parse general summary
    overview_data = soup.find("div", {"id": "plotoverview"})
    if overview_data:
        overview_summary_paragraphs = [paragraph.text.strip().replace("\n", " ") for paragraph in overview_data.findAll("p")]
        overview_summary = "\n".join(overview_summary_paragraphs)

        overview_data = wrap_data("Overview", overview_summary, None, str(overview_url))
        output_fname = os.path.join(specific_summary_dir, 'overview.txt')
        with open(output_fname, 'w', encoding="utf-8") as f:
            f.write(json.dumps(overview_data))

    # Parse sections summary 
    soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
    summary_section = soup.find("span", {"id": "Summary"}).find_parent("div")
    summary_links = summary_section.findAll("a")
    summary_links = [link.get("href") for link in summary_links if "section" in link.get("href")]

    for index, section in enumerate(summary_links):
        print('Parsing section: {}'.format(index))
        output_fname = os.path.join(specific_summary_dir, "section_%d.txt" % index)
        if os.path.exists(output_fname):
             print('Found section: {}'.format(index))
             continue

        section_url = urllib.parse.urljoin(page_url, section)
        soup = BeautifulSoup(urllib.request.urlopen(section_url), "html.parser")
        subsection_links = soup.find("div", {"class": "interior-sticky-nav"})
        num_subsections = max(1, len(subsection_links.findAll("a") if subsection_links else []))
        subsection_links = ["page/%d/" % page_ix for page_ix in range(1, num_subsections+1)]
        section_header = " ".join([x.strip() for x in soup.title.string.replace(" | SparkNotes", "").split(":")[1:]])

        print(section_url)
        print(subsection_links)
        section_paragraphs = []
        for subsection_link in subsection_links:
            subsection_url = urllib.parse.urljoin(section_url, subsection_link)
            soup = BeautifulSoup(urllib.request.urlopen(subsection_url), "html.parser")
            subsection_data = soup.find("div", {"id": "section"})
            section_paragraphs.append(subsection_data.text.strip().replace("\n", " "))
        section_text = "<PARAGRAPH>".join(section_paragraphs)

        if "Summary:" in section_text and "Analysis:" in section_text:
            section_text_split = section_text.split("Analysis:")
            summary_text = " ".join([summary for summary in section_text_split if "Summary:" in summary]).replace("Summary:", "").strip()
            analysis_text = " ".join([analysis for analysis in section_text_split if "Summary:" not in analysis]).replace("Analysis:", "").strip()
        else:
            summary_text = section_text.replace("Summary:", "").strip()
            analysis_text = None

        section_data = wrap_data(section_header, summary_text, analysis_text, section_url)
        with open(output_fname, 'w', encoding="utf-8") as f:
                f.write(json.dumps(section_data))
