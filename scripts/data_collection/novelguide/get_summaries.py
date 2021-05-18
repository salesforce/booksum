"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""

from builtins import zip, str, range

import pdb, os, csv, re, io, json, time
import urllib.request, urllib.error, urllib.parse

from bs4 import BeautifulSoup
from tqdm import tqdm
from shutil import rmtree
from nltk.tokenize import word_tokenize, sent_tokenize
from unidecode import unidecode
import argparse

PARSER = argparse.ArgumentParser(description='For processing HTTP errors separately')
PARSER.add_argument("--fix_scraping_errors", action="store_true", help="Flag indicating \
that script should recrape the links it missed")
ARGS = PARSER.parse_args()

# PARAMS
SUMMARY_DIR = '../../raw_summaries/gradesaver/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210225014436/https://www.novelguide.com/'

def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)

def get_section_level_data(section_links):

    http_errors = []

    for index, (section, name), specific_summary_dir in section_links:
        try:
            soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
            section_data = soup.find("div", {"class": "content clear-block"})

            section_paragraphs = []
            section_analysis = []

            section_paras = section_data.findAll("p")

            for para in section_paras:
                section_paragraphs.append(unidecode(para.text.strip()))

            section_text = "<PARAGRAPH>".join(section_paragraphs)
            section_analysis_text = "<PARAGRAPH>".join(section_analysis)
            #Actual analysis text to be extracted later

            section_dict = {}

            # All section names have colons, so we can get the section name by splitting on colons and taking the last item
            section_dict["name"] = unidecode(name.split(':')[-1].strip())
            section_dict["summary"] = section_text
            section_dict["analysis"] = section_analysis_text
            section_dict["url"] = unidecode(section)
            
            #Check for the overview
            if section_dict["name"] in ["Overview", "Novel Summary",  "NovelSummary", "Summary"]:
                output_fname = os.path.join(specific_summary_dir, 'overview.txt')
                with open(output_fname, 'w', encoding="utf-8") as fp:
                    json.dump(section_dict, fp)
                
            else:  #Must be section file
                output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % int(index))
                with open(output_fname, 'w', encoding="utf-8") as fp:
                    json.dump(section_dict, fp)

        except Exception as e:
            print ("No section summary for: ", section)
            print (e)
            time.sleep(5)

            http_errors.append((index, section, name, specific_summary_dir))
            print ("http_errors: ", http_errors)

    #Errors File is created for saving urls that are not found, before calling this function
    f_errors = open("section_errors.txt","a")

    for (index, section, name, specific_summary_dir) in http_errors:
        f_errors.write(str(index) + "\t" + section + "\t" + name + "\t" + specific_summary_dir + "\n")

    if http_errors != []:
        print ("Http errors written to {}".format(f_errors))

# fetch only the links that resulted in an http error
if ARGS.fix_scraping_errors:
    if not os.path.exists("section_errors.txt"):
        print ("No errors file found\nRun without scraping errors flag")
        exit()
    else:
        f_errors = open("section_errors.txt","r")
        section_links = []
        for line in f_errors:
            line_splits = line.rstrip().split("\t")
            section_links.append((line_splits[0],(line_splits[1], line_splits[2]), line_splits[3]))
        
        f_errors.close()

        if len(section_links) == 0:
            print ("No errors found\nRun without scraping errors flag")
            exit()
        
        print ("Links with scraping errors scraped again: ", section_links)

        
        #Create the errors file every time when starting to scrape the summaries
        #Should overwrite the same file we opened for reading
        f_errors = open("section_errors.txt","w")

        #fetch the summaries using the links that threw an error
        get_section_level_data(section_links)

    exit()

# Summary list info
summary_list_file = "literature_links.tsv"

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)


#Create the errors file every time when starting to scrape the summaries
f_errors = open("section_errors.txt","w")
print ("Errors file created")

# For each summary info
for k, (title, page_url) in enumerate(summary_infos):
    print('\n>>> {}. {} <<<'.format(k, title))

    overview_found = 0

    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)

    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory.")

    # Parse page
    try:
        soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
    except urllib.error.HTTPError:
        print ("HTTP error raised. Trying again")
        time.sleep(10)
        try:
            soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
        except urllib.error.HTTPError:
            #Page not accessible at the moment
            with open("book_not_found.txt","a") as f:
                f.write(k, title, page_url)
                f.write("\n")
            continue

    # # Parse general summary
    navigation_links = soup.find("div", {"id": "block-booknavigation-3"})
    # print (navigation_links)
    section_links = [(urllib.parse.urljoin(MAIN_SITE, link.find("a").get("href")), link.text.strip()) for link in navigation_links.findAll("li")\
     if 'chapter' in link.text.strip().lower() or 'summary' in link.text.strip().lower() or 'section' in link.text.strip().lower() or 'stave' in link.text.strip().lower() \
     or 'chp' in link.text.strip().lower() or 'scene' in link.text.strip().lower() or 'act ' in link.text.strip().lower() \
     or 'part' in link.text.strip().lower() or 'pages' in link.text.strip().lower() or 'lines' in link.text.strip().lower() \
     or 'book' in link.text.strip().lower() or hasNumbers(link.text.strip().lower()) or 'overview' in link.text.strip().lower()\
     or 'prologue' in link.text.strip().lower() or 'epilogue' in link.text.strip().lower()]
     #Why not checking for the keyword 'summary'??

    # Append index to all the section links
    section_links_with_index = []
    for index, (section, name) in enumerate(section_links):
        section_links_with_index.append((index,(section, name), specific_summary_dir))

    print (section_links_with_index, "\n")

    
    if len(section_links_with_index) == 0:
        print ("No section summaries found")
    else:
        get_section_level_data(section_links_with_index)
