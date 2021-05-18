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
from unidecode import unidecode
import time

# PARAMS
SUMMARY_DIR = '../../raw_summaries/bookwolf/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210120012015/http://www.bookwolf.com/'

# Summary list info
summary_list_file = "literature_links.tsv"

#File for capturing the HTTP Errors, for webpages that are not found
f_errors = open("section_errors.txt","w")

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)

def get_overview_paragraphs(overview_links, specific_summary_dir):

    for index, (overview, name) in enumerate(overview_links):
        try:
            soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
            overview_data = soup.find("td", {"class": "TextObject"})

            overview_paragraphs = [unidecode(paragraph.text.strip()) for paragraph in overview_data.findAll("p", recursive=False)[1:]]
            
        except Exception as e:
            print(e)
            time.sleep(5)
            try:
                soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
                overview_data = soup.find("td", {"class": "TextObject"})

                overview_paragraphs = [unidecode(paragraph.text.strip()) for paragraph in overview_data.findAll("p", recursive=False)[1:]]

            except Exception as e:
                print("No book summary for: ", e)
                f_errors.write(str(index) + "\t" + overview + "\t" + name + "\t" + specific_summary_dir + "\n")
                continue

            overview_text = "\n".join(overview_paragraphs)
            
            overview_dict = {}
            overview_dict["name"] = "Overview"
            overview_dict["summary"] = overview_text
        
            output_fname = os.path.join(specific_summary_dir, "overview.json")
            with open(output_fname, 'w', encoding="utf-8") as fp:
                json.dump(overview_dict, fp)

def get_section_paragraphs(section_links, specific_summary_dir):
    #Fetch chapter level summary
    for index, (section, name) in enumerate(section_links):
        
        try:
            
            print ("Section: ", section)
            soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
            section_data = soup.find("td", {"class": "TextObject"})
        except Exception as e:

            print (e)
            time.sleep(5)

            try:
                soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
                section_data = soup.find("td", {"class": "TextObject"})
            except Exception as e:
                print ("Chapter level summary not found: ", e)
                f_errors.write(str(index) + "\t" + section + "\t" + name + "\t" + specific_summary_dir + "\n")
                continue


        section_paragraphs = []
        section_analysis = []

        start = -1

        for paragraph in section_data.findAll("p", recursive=False):
            
            # Trim out anything before the actual summary starts
            if paragraph.text.strip().lower() in ["summary", "context"] or 'book' in paragraph.text.strip().lower():
                start = 1

            if start == -1:
                continue

            # If interpretation exists
            if paragraph.text.strip() == "Interpretation":
                start = 0
            
            if start:
                section_paragraphs.append(unidecode(paragraph.text.strip()))
            else:
                section_analysis.append(unidecode(paragraph.text.strip()))
                
            # print ("line: ", paragraph.text.strip())

        section_text = "\n".join(section_paragraphs)
        section_interpretation = "\n".join(section_analysis)

        section_dict = {}
        section_dict["name"] = name
        section_dict["summary"] = section_text
        section_dict["analysis"] = section_interpretation

        output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % (index-1))
        with open(output_fname, 'w', encoding="utf-8") as fp:
            json.dump(section_dict, fp)
        

# For each summary info
error_files, error_titles = [], []
for k, (title, page_url) in enumerate(summary_infos):

    print('\n>>> {}. {} <<<'.format(k, title))

    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)
    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory.")

    # Parse page
    soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")

    # Parse general summary
    navigation_links = soup.find("table", {"id": "Table56"})
    if navigation_links == None:
        navigation_links = soup.find("td", {"class": "TextObject"})
    overview_links = [(urllib.parse.urljoin(MAIN_SITE, link.get("href")), link.text) for link in navigation_links.findAll("a")\
     if ("part" not in link.text.lower() and ("context" in link.get("href") or "summary" in link.get("href") or "synopsis" in link.get("href") ))]

    #Filter out some of the links that are obviously not chapter summary links
    #Since this source only has a handful of books, it was easy to hard code which links to fetch/not fetch
    section_links = [(urllib.parse.urljoin(MAIN_SITE, link.get("href")), link.text) for link in navigation_links.findAll("a") \
    if  (("interpretation" not in link.text.lower() and "comment" not in link.text.lower() and "author" not in link.text.lower()\
    and "character" not in link.text.lower() and "questions" not in link.text.lower() and "life at the time" not in link.text.lower()\
    and "theme" not in link.text.lower() and "foreword" not in link.text.lower() and "background" not in link.text.lower()\
    and "symbolism" not in link.text.lower() and "introduction" not in link.text.lower() and "characterization" not in link.text.lower()\
    and "setting" not in link.text.lower() and "family life" not in link.text.lower() and "comment" not in link.text.lower() ) 
    
    print ("overview_links: ", overview_links)
    print ("section_links: ", section_links)

    if len(overview_links) != 0:
        get_overview_paragraphs(overview_links, specific_summary_dir)

    if len(section_links) != 0:
        get_section_paragraphs(section_links, specific_summary_dir)
    
