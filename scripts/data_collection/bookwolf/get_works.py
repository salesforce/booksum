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
MAIN_SITE = 'https://web.archive.org/web/20210120012015/http://www.bookwolf.com/'
SEED_URL = 'https://web.archive.org/web/20210120012015/http://www.bookwolf.com/Welcome_to_Bookwolf1/welcome_to_bookwolf1.html'

def scrape_index_pages(seed_page):
# For each summary info
    scraped_links = []

    soup = BeautifulSoup(urllib.request.urlopen(seed_page), "html.parser")
    items = soup.findAll("tr", {"align": "LEFT", "valign": "TOP"})
    tables = items[0].findAll("table")
    books_table = tables[10].findAll("p")
    print("Found %d items." % len(books_table))

    # # Go over each section
    for index, item in enumerate(books_table):
        # Parse section to get bullet point text
        print (item)
        item_title = item.find("a").text
        item_url = item.find("a").get("href")[3:]

        print ("item_title: ", item_title)
        print ("item_url: ", item_url)

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
