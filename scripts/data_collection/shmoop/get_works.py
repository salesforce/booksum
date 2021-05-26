"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""

from builtins import zip, str, range
import pdb, os, csv, re, io
import urllib.request, urllib.error, urllib.parse
from bs4 import BeautifulSoup
from tqdm import tqdm
from shutil import rmtree
from nltk.tokenize import word_tokenize, sent_tokenize

# PARAMS
MAIN_SITE = 'https://web.archive.org/web/20210225092515/https://www.shmoop.com/study-guides'

errors_file = open("link_errors.txt","w")

def generate_page_links(base_url, category_name, max_pages):
    return [os.path.join(base_url, category_name, "index?p=%d" % page_id) for page_id in range(1, max_pages+1)]


def scrape_index_pages(links):
# For each summary info
    error_files, error_titles = [], []
    scraped_links = []

    for k, page_url in enumerate(links):
        print('>>> {}. {} <<<'.format(k, page_url))

        try:
            soup = BeautifulSoup(urllib.request.urlopen(page_url), "html.parser")
        except Exception as e:
            print ("Skipping: ", page_url)
            errors_file.write(page_url + "\t" + str(e) + "\n")
            continue

        items = soup.findAll("div", {"class" : "item"})
        print("Found %d items." % len(items))

        # Go over each section
        for index, item in enumerate(items):
            # Parse section to get bullet point text
            item_title = item.find("div", {"class": "item-info"}).text
            item_url = item.find("a", {"class": "details"}).get("href")

            scraped_links.append({
                "title": item_title.strip(),
                "url": item_url.strip()
            })
    return scraped_links

# generate literature links

works_list = generate_page_links(MAIN_SITE, "literature", 95)
scraped_data = scrape_index_pages(works_list)

with open("literature_links.tsv", "w") as fd:
    for data in scraped_data:
        fd.write("%s\t%s\n" % (data["title"], data["url"]))
