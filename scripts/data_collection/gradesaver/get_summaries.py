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
SUMMARY_DIR = '../../raw_summaries/gradesaver/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210226083212/https://www.gradesaver.com/'

# Summary list info
summary_list_file = "literature_links.tsv"

errors_file = open("section_errors.txt","w")

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
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
    try:
        soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
    except Exception as e:
        print (page_url, e)
        errors_file.write(page_url + "\t" + str(e))
        continue


    # # Parse general summary
    navigation_links = soup.find("ul", {"class": "navSection__list js--collapsible"})
    overview_links = [(urllib.parse.urljoin(MAIN_SITE, link.find("a").get("href")), link.text.strip()) for link in navigation_links.findAll("li") if link.text.strip() == title + " Summary"]
    # print (overview_links)

    if len(overview_links) == 0:
        print ("No overview summaries found")
    else:
        for index, (overview, name) in enumerate(overview_links):
            try:
                print (name, overview)
                soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
                overview_data = soup.find("article", {"class": "section__article"})

                overview_paragraphs = []
                overview_analysis = []
                start = 1
                for paragraph in overview_data.findAll("p", recursive=False):

                    #Skip the first word if it is "Summary" or "Context"
                    if paragraph.text.strip().lower() in ["summary", "context"]:
                        continue

                    if paragraph.text.strip().lower() in ["analysis"]:
                        start = 0
                        continue
                    
                    if start:
                        overview_paragraphs.append(paragraph.text.strip())
                    else:
                        overview_analysis.append(paragraph.text.strip())
                    
                overview_text = "<PARAGRAPH>".join(overview_paragraphs)
                overview_analysis_text = "<PARAGRAPH>".join(overview_analysis)
                
                overview_dict = {}
                overview_dict["name"] = "Overview"
                overview_dict["summary"] = overview_text
                overview_dict["analysis"] = overview_analysis_text
                overview_dict["url"] = overview
                

                # print (overview_analysis_text)
                output_fname = os.path.join(specific_summary_dir, "overview.json")
                with open(output_fname, 'w', encoding="utf-8") as fp:
                    json.dump(overview_dict, fp)

            except Exception as e:
                print ("No overview summary for: ", overview)
                print (e)

    section_links = [link.find("ul").findAll("li") for link in navigation_links.findAll("li") if "Summary And Analysis" in link.text.strip()]
    
    if len(section_links) == 0:
        print ("No section summaries found")
    else:
        section_links = [(urllib.parse.urljoin(MAIN_SITE,link.find("a").get("href")), link.text.strip()) for link in section_links[0]]
        # print (section_links)

        for index, (section, name) in enumerate(section_links):
            try:
                print (name, section)
                soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
                section_data = soup.find("article", {"class": "section__article"})

                section_paragraphs = []
                section_analysis = []
                start = 1
                for paragraph in section_data.findAll(["p","h2"], recursive=False):
                    
                    #Skip the first word if it is "Summary" or "Context"
                    if paragraph.text.strip().lower() in ["summary", "context"]:
                        continue

                    if paragraph.text.strip().lower() in ["analysis"]:
                        start = 0
                        continue
                    
                    if start:
                        section_paragraphs.append(paragraph.text.strip())
                    else:
                        section_analysis.append(paragraph.text.strip())
                    
                section_text = "<PARAGRAPH>".join(section_paragraphs)
                section_analysis_text = "<PARAGRAPH>".join(section_analysis)
                
                section_dict = {}
                section_dict["name"] = name
                section_dict["summary"] = section_text
                section_dict["analysis"] = section_analysis_text
                section_dict["url"] = section
                

                output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % index)
                with open(output_fname, 'w', encoding="utf-8") as fp:
                    json.dump(section_dict, fp)

            except Exception as e:
                print ("No section summary for: ", section)
                print (e)
