"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""


"""
Note: Summaries collected through bookwolf require significant manual cleanup owing to the way the HTML is written
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
import pdb

# PARAMS
SUMMARY_DIR = '../../raw_summaries/bookwolf/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210120012015/http://www.bookwolf.com/'

# Summary list info
summary_list_file = 'literature_links.tsv.pruned'

#File for capturing the HTTP Errors, for webpages that are not found
f_errors = open("section_errors.txt","w")

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)

def get_overview_paragraphs(overview_links, specific_summary_dir):

    for index, (overview, name) in enumerate(overview_links):

        print (name, overview)

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
                print("No book summary for: ", overview, e)
                f_errors.write(overview + "\t" + name + "\t" + specific_summary_dir + "\n")
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
            print (name, section)
            soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
            section_data = soup.find("td", {"class": "TextObject"})
        except Exception as e:

            print (e)
            time.sleep(5)

            try:
                soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
                section_data = soup.find("td", {"class": "TextObject"})
            except Exception as e:
                print ("Chapter level summary not found for: ", section, e)
                f_errors.write(section + "\t" + name + "\t" + specific_summary_dir + "\n")
                continue


        section_paragraphs = []
        section_analysis = []

        # Recursive function to parse HTML with upper case tags
        def parse_upper_case_html_tags(paragraph):

            paragraph_text = paragraph.text

            if "<P STYLE=" in paragraph_text or 'SPAN' in paragraph_text:
                paragraph_soup = BeautifulSoup(paragraph_text, 'html.parser')
                paragraphs = paragraph_soup.findAll("p")
                para_text_list = []
                for para in paragraphs:
                    para_text = parse_upper_case_html_tags(para)
                    para_text_list.append(para_text)
                
                return " ".join(para_text_list)

            return paragraph_text

        for paragraph in section_data.findAll("p", recursive=True):

            paragraph_text = parse_upper_case_html_tags(paragraph).replace("&#8220", " ").replace("&#8221", " ")
            paragraph_text = " ".join(paragraph_text.split())

            if paragraph_text == 'advertisement' or 'Bookwolf' in paragraph_text:
                continue
            
            section_paragraphs.append(unidecode(paragraph_text.strip()))

        section_text = "<PARAGRAPH>".join(section_paragraphs)

        section_dict = {}
        section_dict["name"] = name
        section_dict["summary"] = section_text

        output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % (index-1))
        with open(output_fname, 'w', encoding="utf-8") as fp:
            json.dump(section_dict, fp)


# For each summary info
for k, (title, page_url) in enumerate(summary_infos):

    print('\n>>> {}. {} <<<'.format(k, title))

    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)
    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory.")
        # continue

    # Parse page
    print ("page_url: ", page_url)
    try:
        soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
    except Exception as e:
        print (page_url, e)
        f_errors.write(str(k) + "\t" + title + "\t" + page_url + "\t" + specific_summary_dir + "\n")
        continue


    # Parse general summary
    navigation_links = soup.find("table", {"id": "Table56"})
    if navigation_links == None:
        navigation_links = soup.find("td", {"class": "TextObject"})
    overview_links = [(urllib.parse.urljoin(MAIN_SITE, link.get("href")), link.text) for link in navigation_links.findAll("a")\
     if ("part" not in link.text.lower() and ("context" in link.get("href") or "summary" in link.get("href") or "synopsis" in link.get("href") ))]

    # Filter out some of the links that are obviously not chapter summary links
    # Since this source only has a handful of books, it was easy to hard code which links to fetch summaries from
    section_links = [(urllib.parse.urljoin(MAIN_SITE, link.get("href")), link.text) for link in navigation_links.findAll("a") \
    if  ("interpretation" not in link.text.lower() and "comment" not in link.text.lower() and "author" not in link.text.lower()\
    and "character" not in link.text.lower() and "questions" not in link.text.lower() and "life at the time" not in link.text.lower()\
    and "theme" not in link.text.lower() and "foreword" not in link.text.lower() and "background" not in link.text.lower()\
    and "symbolism" not in link.text.lower() and "introduction" not in link.text.lower() and "characterization" not in link.text.lower()\
    and "setting" not in link.text.lower() and "family life" not in link.text.lower() and "comment" not in link.text.lower() \
    and "context" not in link.text.lower() ) ]
    
    if len(overview_links) != 0:
        get_overview_paragraphs(overview_links, specific_summary_dir)

    if len(section_links) != 0:
        get_section_paragraphs(section_links, specific_summary_dir)

