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
import argparse, string

# PARAMS
SUMMARY_DIR = '../../raw_summaries/thebestnotes/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210111015641/http://thebestnotes.com/'

# Summary list info
summary_list_file = "literature_links.tsv"

# Create a fresh file for the links that throw HTTP errors, so that we can try access them again
f_errors = open("section_errors.txt","w")

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)

def unify_title(title):
    title_lower = title.lower().strip()
    title_clean = title_lower.translate(str.maketrans('', '', string.punctuation))
    return title_clean

def get_overview_paragraphs(overview):

    try:
        soup = BeautifulSoup(urllib.request.urlopen(overview), "html.parser")
    except Exception as e:
        print (overview, e)
        f_errors.write(overview + "\t" + str(e))
        return []

    overview_paragraphs = []
    flag = 0

    for paragraph in soup.findAll(["p", "h2", "h6"]):
        if 'synopsis' in " ".join(paragraph.text.strip().lower().split()) and paragraph.name in ["h2", "h6"]:
            flag = 1
            continue

        # continue collecting text from the rest of the p tags
        if flag == 1 and "thebestnotes" not in paragraph.text.strip().lower() and (paragraph.name == 'p' or (paragraph.name in ["h2", "h6"] and paragraph.text.replace("\r\n","").strip() == "")):
            if paragraph.text.strip() != "":
                overview_paragraphs.append(unidecode(paragraph.text.replace("\r\n","").strip()))
        else:
            flag = 0
            # end collecting the summary when the above conditions are not met
    
    return overview_paragraphs



def get_section_paragraphs(section, section_titles, section_title_orig, specific_summary_dir, index):
    try:
        soup = BeautifulSoup(urllib.request.urlopen(section), "html.parser")
    except Exception as e:
        print (section_title_orig, section, e)
        f_errors.write(str(index+1) + "\t" + section + "\t" + str(section_titles) + "\t" + section_title_orig + "\t" + specific_summary_dir + "\n")
        
        return []
    section_paragraphs = []
    flag = 0
    found = False

    # True if a structured page exists like -  https://web.archive.org/web/20210111015641/http://thebestnotes.com/booknotes/Invisible_Man_Wells/The_Invisible_Man_Study_Guide14.html
    structured_page = 0

    if soup.findAll("div", {"class": "large-12 columns"}) != []:
        structured_page = 1

    for section_title in section_titles:

        section_title = unify_title(section_title.strip())

        if structured_page:
            # The summary header doesn't exist on a structured page as shown in the example link
            # The <p> tag directly after the title contains the required info
            # However, this introduces several other elements like 'setting', 'themes' etc in the sections
            # we save for the structured pages, which shall hopefully be handled in the matching process

            for paragraph in soup.findAll(["p", "h2", "h6"]):

                if section_title in unify_title(" ".join(paragraph.text.strip().lower().split())) and paragraph.name in ["h2", "h6"]:
                    flag = 1
                    continue

                # continue collecting text from the rest of the p tags
                if flag == 1 and "thebestnotes" not in paragraph.text.strip().lower() and \
                (paragraph.name == 'p' or
                (paragraph.name in ["h2", "h6"] and paragraph.text.strip() == "")):
                    if paragraph.text.strip() != "":
                        section_paragraphs.append(paragraph.text.replace("\r\n","").strip())
                else:
                    flag = 0
                    # end collecting the summary 

            if (len(section_paragraphs) > 0):
                break
                
        else:

            for paragraph in soup.findAll(["p", "h2", "h6"]):

                if section_title in unify_title(" ".join(paragraph.text.strip().lower().split())) and paragraph.name in ["h2", "h6"]:
                    flag = 1
                    continue

                # continue collecting text from the rest of the p tags
                if flag == 1 and "thebestnotes" not in paragraph.text.strip().lower() and \
                (paragraph.name in ["h2", "h6"] and (paragraph.text.replace("\r\n","").strip() == "" or \
                paragraph.text.strip().lower() == "summary")):
                    if paragraph.text.strip() != "":
                        flag = 2
                        continue
                    else:
                        continue

                if flag == 2 and "thebestnotes" not in paragraph.text.strip().lower() and (paragraph.name == 'p' or (paragraph.name in ["h2", "h6"] and paragraph.text.strip() == "")):
                    if paragraph.text.strip() != "":
                        section_paragraphs.append(paragraph.text.replace("\r\n","").strip())
                else:
                    flag = 0
                    # end collecting the summary 
            
            if (len(section_paragraphs) > 0):
                break
            # else there might be some text we missed

    return section_paragraphs


def save_section_para(section_paragraphs, section_titles, section_title_orig, section, specific_summary_dir, index):

    print (section_titles[0], section)

    section_text = "<PARAGRAPH>".join(section_paragraphs)

    section_dict = {}
    section_dict["name"] = section_title_orig
    section_dict["summary"] = section_text
    section_dict["analysis"] = ""
    section_dict["url"] = section

    output_fname = os.path.join(specific_summary_dir, 'section_%d.txt' % int(index))
    with open(output_fname, 'w', encoding="utf-8") as fp:
        json.dump(section_dict, fp)

# For each summary info
for k, (title, page_url) in enumerate(summary_infos):
    print('\n>>> {}. {} - {} <<<'.format(k, title, page_url))


    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)
    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory")
        continue

    # Parse page
    soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")

    one_level_up_url = os.path.dirname(page_url) + "/"

    #fetch section
    section_paragraphs = []

    navigation_links = soup.findAll("a")

    index = -1 # For section numbers

    for link in navigation_links:
        if 'synopsis' in " ".join(link.text.strip().lower().split()):
            overview = urllib.parse.urljoin(one_level_up_url, link.get("href"))
            overview_title = link.text.strip().lower()
            print ("overview: ",overview)

            overview_paragraphs = get_overview_paragraphs(overview)

            overview_text = "<PARAGRAPH>".join(overview_paragraphs)

            overview_dict = {}
            overview_dict["name"] = "overview"
            overview_dict["summary"] = overview_text
            overview_dict["analysis"] = ""
            overview_dict["url"] = overview

            output_fname = os.path.join(specific_summary_dir, "overview.json")
            with open(output_fname, 'w', encoding="utf-8") as fp:
                json.dump(overview_dict, fp)

        else:

            section = urllib.parse.urljoin(one_level_up_url, link.get("href"))

            section_title_orig = " ".join(link.text.strip().lower().split())

            # Keep the original one first in the list of possible titles to match. For chapter numbers like "TWENTY-THREE" and "TWENTY-FOUR", which occur on the same web page.
            section_titles = [section_title_orig]

            # To handle cases where the og page says Chapter 1 - X, but the summary page just says X
            # Add the different kind of section titles we can have into a list
            if ('-' in section_title_orig):
                section_titles = section_titles + section_title_orig.strip().split('-')
            elif (':' in section_title_orig):
                section_titles = section_titles + section_title_orig.strip().split(':')

            if (section_title_orig == ""):
                continue

            section_paragraphs = get_section_paragraphs(section, section_titles, section_title_orig, specific_summary_dir, index)

            if (section_paragraphs != []):

                index += 1
                save_section_para(section_paragraphs, section_titles, section_title_orig, section, specific_summary_dir, index)
