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

from urllib.error import HTTPError, URLError

# PARAMS
SUMMARY_DIR = '../../raw_summaries/pinkmonkey/summaries'
# Summary list info
summary_list_file = 'literature_links.tsv.pruned'

#Always create a new errors file when starting to run the script
f_errors = open("section_errors.txt","w")

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)

def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)

def chapter_section_check(link_text_lower, link_text_not_lower):
    return 'chapter' in link_text_lower or 'scene' in link_text_lower\
         or 'Act' in link_text_not_lower or 'part' in link_text_lower or 'prologue' in link_text_lower or 'epilogue' in link_text_lower\
          or 'story' in link_text_lower or 'preface' in link_text_lower or 'Section' in link_text_not_lower


def remove_toc(text):
    pat = '((.*)(table[ ]{1,}of contents.*))'

    if re.match(pat, text, re.IGNORECASE):
        to_replace = re.match(pat, text, re.IGNORECASE).group(3)

        text = text.replace(to_replace, "")
    
    return text

def get_overview_paragraphs(overview, specific_summary_dir):
    overview_paragraphs = []

    try:
        soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
    except Exception as e:
        print (e)
        time.sleep(4)
        try:
            soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
        except Exception as e:
            print ("Overview not found: ", e, overview)

            # with open("section_errors.txt","a") as f:
            f_errors.write(overview + "\t" + "Overview" + "\t" + specific_summary_dir + "\n")

            return overview_paragraphs

    flag = 0
    pat = "(.*\(synopsis\))"

    paragraphs = soup.findAll(["p","h3"])

    iframe_text = "Your browser does not support the IFRAME tag."

    for ix, paragraph in enumerate(paragraphs):
        overview_text = paragraph.text.strip().replace(iframe_text, "").replace("\r\n"," ").replace("\n"," ")
        if re.match(pat, overview_text, re.IGNORECASE):
            break

    if re.match(pat, overview_text, re.IGNORECASE):
        to_replace = re.match(pat, overview_text, re.IGNORECASE).group(1)

        overview_text = overview_text.replace(to_replace, "")

    overview_text = remove_toc(overview_text)
    overview_text = unidecode(overview_text)

    overview_text = ". ".join([line.strip().rstrip() for line in overview_text.split('. ')])

    return overview_text

def save_section_para(section_text, section_title, section_link, specific_summary_dir, index):

    section_text = remove_toc(section_text)
    section_text = remove_toc(section_text)

    section_dict = {}
    section_dict["name"] = section_title
    section_dict["summary"] = section_text
    section_dict["analysis"] = ""
    section_dict["url"] = section_link

    output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % index)
    with open(output_fname, 'w', encoding="utf-8") as fp:
        json.dump(section_dict, fp)

def get_section_paragraphs(page_url, specific_summary_dir):
    soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
    section_paragraphs = []
    all_links = []
    section_links = []
    flag = 0

    one_level_up_url = os.path.dirname(page_url)

    all_links = soup.findAll("a")

    overview_exists = 0
    for link in all_links:

        link_text_not_lower = link.text.strip().replace("\r\n"," ").replace("\n"," ")
        link_text_lower = link.text.strip().lower().replace("\r\n"," ").replace("\n"," ")
        if "summaries" in link_text_lower or 'synopsis' in link_text_lower or 'plot' in link_text_lower or chapter_section_check(link_text_lower, link_text_not_lower):
            
            section_path = os.path.join(one_level_up_url, link.get("href"))
            section_links.append((link.text.strip().rstrip(), section_path))

            if 'synopsis' in link_text_lower or 'plot' in link_text_lower:
                overview_exists = 1

    overview_found = 0
    index = -1

    for link_text, link in section_links:
        link_text = link_text.replace("\r\n"," ").replace("\n"," ")
        link_text_lower = link_text.strip().rstrip().lower().replace("\r\n"," ").replace("\n"," ")
        link_text_not_lower = link_text.strip().rstrip().replace("\r\n"," ").replace("\n"," ")


        #Fetch overview first
        if overview_exists and ('synopsis' in link_text_lower or 'plot' in link_text_lower) and overview_found == 0:

            overview = link
            overview_title = link_text

            print (overview_title, overview)
            
            overview_text = get_overview_paragraphs(overview, specific_summary_dir)

            overview_dict = {}
            overview_dict["name"] = "overview"
            overview_dict["summary"] = overview_text
            overview_dict["analysis"] = ""
            overview_dict["url"] = overview

            output_fname = os.path.join(specific_summary_dir, "overview.json")
            with open(output_fname, 'w', encoding="utf-8") as fp:
                json.dump(overview_dict, fp)

            overview_found = 1
            continue

        if (overview_found == 1 or not overview_exists) and chapter_section_check(link_text_lower, link_text_not_lower):

            chapter_url = link
            
            print(link_text, chapter_url)

            index += 1
            
            try:
                chapter_soup = BeautifulSoup(urllib.request.urlopen(chapter_url), "html.parser")
            except URLError as err:
                print (err, "Retrying after sleep")
                time.sleep(10)
                try:
                    chapter_soup = BeautifulSoup(urllib.request.urlopen(chapter_url), "html.parser")
                except Exception as e:
                    print (chapter_url, e)
                    f_errors.write(chapter_url + "\t" + str(e))
                    f_errors.write("\n")
                    continue
            except Exception as e:
                print (e)
                time.sleep(4)
                try:
                    chapter_soup = BeautifulSoup(urllib.request.urlopen(chapter_url), "html.parser")
                except Exception as e:
                    print ("Chapter not found: ", e, chapter_url)

                    # with open("section_errors.txt","a") as f:
                    f_errors.write(str(index) + "\t" + chapter_url + "\t" + link_text + "\t" + specific_summary_dir + "\n")

                    continue

            chapter_paras = chapter_soup.findAll(["p", "h3"])

            iframe_text = "Your browser does not support the IFRAME tag."

            section_text_paras = []

            for ix, chapter_para in enumerate(chapter_paras):
                try:
                    section_text = chapter_para.text.strip().replace(iframe_text, "").replace("\r\n"," ").replace("\n"," ")

                    section_text_paras.append(unidecode(section_text))
                        
                except Exception as e: # No text inside the para HTML
                    print ("Summary not found: ", e, chapter_url)

                    f_errors.write(str(index) + "\t" + chapter_url + "\t" + link_text + "\t" + specific_summary_dir + "\n")
                    continue
                    
            section_text = ' '.join(section_text_paras)

            section_text = ". ".join([line.strip().rstrip() for line in section_text.split('. ')])
            section_text = " ".join([word.strip() for word in section_text.split()])

            # Remove obvious noise from the summary text
            pat_toc = '.*?(Table of Contents(.*$))'

            if re.match(pat_toc, section_text):
                to_replace = re.match(pat_toc, section_text).group(1)
                section_text = section_text.replace(to_replace, "")

            section_text = section_text.replace("Help / FAQ", "").strip()   # why no remove?
            section_text = section_text.replace("Please Take our User Survey", "").strip()   # why no remove?
            
            section_title = link_text

            # print ("section_text SAVED: ", section_text)

            save_section_para(section_text, section_title, chapter_url, specific_summary_dir, index)
        

# For each summary info
for k, (title, page_url) in enumerate(summary_infos):
    print('\n>>> {}. {} - {} <<<'.format(k, title, page_url))

    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)
    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory, skipping.")
        # continue

    # Parse page
    try:
        soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
    except URLError as err:
        print (err, "Retrying after sleep")
        time.sleep(10)
        try:
            soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
        except Exception as e:
            print (page_url, e)
            f_errors.write(page_url + "\t" + str(e))
            f_errors.write("\n")
            continue
    except Exception as e:
        print ("page not found: ", e)
        continue
            
    get_section_paragraphs(page_url, specific_summary_dir)

    

