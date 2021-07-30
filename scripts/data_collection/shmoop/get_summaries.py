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
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup
from tqdm import tqdm
from shutil import rmtree
from nltk.tokenize import word_tokenize, sent_tokenize
import time
from multiprocessing import Pool

# PARAMS
SUMMARY_DIR = '../../raw_summaries/shmoop/summaries'
MAIN_SITE = 'https://web.archive.org/web/20210225092515/https://www.shmoop.com/'

# Summary list info
summary_list_file = 'literature_links.tsv.pruned'

errors_file = open("section_errors.txt","w")

def wrap_data(name, summary, analysis, url):
    return {
        "name": name,
        "summary": summary,
        "analysis": analysis,
        "url": url
    }


def get_summary(summary_infos):
    print ("summary_infos: ", summary_infos)
    # For each summary info
    # for k, (title, url) in enumerate(summary_infos):
    title = summary_infos[0]
    url = summary_infos[1]
    print('\n>>> {} <<<'.format(title))

    # Create a directory for the work if needed
    specific_summary_dir = os.path.join(SUMMARY_DIR, title)
    if not os.path.exists(specific_summary_dir):
        os.makedirs(specific_summary_dir)
    else:
        print("Found existing directory, skipping.")
        # continue

    # Parse page
    html_address = urllib.parse.urljoin(url + "/", "summary")

    try:
        soup = BeautifulSoup(urllib.request.urlopen(html_address), "html.parser")
    except Exception as e:
        time.sleep(5)
        try:
            soup = BeautifulSoup(urllib.request.urlopen(html_address), "html.parser")
        except Exception as e:
            print (html_address, e)
            errors_file.write(html_address + "\t" + str(e))
            errors_file.write("\n")
            return

    # Parse general summary
    overview_section = soup.find("div", {"data-class": "SHPlotOverviewSection"})
    overview_section = soup.find("div", {"class": "content-wrapper"})
    overview_summary_paragraphs = [paragraph.text.strip() for paragraph in overview_section.findAll("p")]
    overview_summary = "<PARAGRAPH>".join(overview_summary_paragraphs)

    overview_data = wrap_data("Overview", overview_summary, None, str(html_address))
    output_fname = os.path.join(specific_summary_dir, 'overview.txt')
    with open(output_fname, 'w', encoding="utf-8") as f:
        f.write(json.dumps(overview_data))

    # Parse sections summary 
    summary_sections = [(link.text, urllib.parse.urljoin(MAIN_SITE, link.get("href"))) for link in soup.find("div", {"class": "nav-menu"}).findAll("a", href=True) if "summary" in link.get("href")]
    # Go over each section
    for index, (section_title, section_url) in enumerate(summary_sections):
        output_fname = os.path.join(specific_summary_dir, "section_%d.txt" % index)

        print (section_title, section_url)
        
        # Parse section to get bullet point text
        try:
            soup = BeautifulSoup(urllib.request.urlopen(section_url), "html.parser")
        except URLError as err:
            print (err, "Retrying after sleep")
            time.sleep(10)
            try:
                soup = BeautifulSoup(urllib.request.urlopen(section_url), "html.parser")
            except Exception as e:
                print (section_url, e)
                errors_file.write(section_url + "\t" + str(e))
                errors_file.write("\n")
                continue
            
        except Exception as e:
            print (section_url, e)
            errors_file.write(section_url + "\t" + str(e))
            errors_file.write("\n")
            continue

        try:
            section_points = soup.find("div", {"data-element": "collapse_target"})
            section_text = "<PARAGRAPH>".join([bullet.text.strip() for bullet in section_points.findAll("li")])

            # Try alternate
            if section_text == '':
                section_text = "<PARAGRAPH>".join([bullet.text.strip() for bullet in section_points.findAll("p")])

            section_data = wrap_data(section_title, section_text, None, str(section_url))
            # Save in a file
            with open(output_fname, 'w', encoding="utf-8") as f:
                f.write(json.dumps(section_data))
            print ("Saved to file")
        except Exception as e:
            print (section_url, e)
            errors_file.write(section_url + "\t" + str(e))
            errors_file.write("\n")
            continue
                

# Get contents of the summary file
with open(summary_list_file, 'r') as tsvfile:
    reader = csv.reader(tsvfile, delimiter='\t')
    summary_infos = list(reader)

with Pool(1) as p:
    p.map(get_summary, summary_infos)
