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
MAIN_SITE = 'https://web.archive.org/web/20210223175142/https://www.sparknotes.com/'
SEED_URL = 'https://web.archive.org/web/20210223175142/https://www.sparknotes.com/lit'

errors_file = open("link_errors.txt","w")

def scrape_index_pages(seed_page):
# For each summary info
    scraped_links = []

    try:
        soup = BeautifulSoup(urllib.request.urlopen(seed_page), "html.parser")
    except Exception as e:
        print ("Skipping: ", seed_page)
        errors_file.write(seed_page + "\t" + str(e) + "\n")
        return []

    items = soup.findAll("li", {"class": "hub-AZ-list__card hub-AZ-list__card--byTitle"})
    print("Found %d items." % len(items))

    # Go over each section
    for index, item in enumerate(items):
        # Parse section to get bullet point text
        item_title = item.find("a", href=True).text
        item_url = item.find("a").get("href")

        scraped_links.append({
            "title": item_title.strip().replace(",",""),
            "url": urllib.parse.urljoin(MAIN_SITE, item_url.strip())
        })
    return scraped_links

# generate literature links
scraped_data = scrape_index_pages(SEED_URL)

with open("literature_links.tsv", "w") as fd:
    for data in scraped_data:
        fd.write("%s\t%s\n" % (data["title"], data["url"]))
