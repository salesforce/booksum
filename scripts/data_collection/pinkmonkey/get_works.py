"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""

from builtins import zip, str, range
import pdb, os, csv, re, io, string
import urllib.request, urllib.error, urllib.parse
from bs4 import BeautifulSoup
from tqdm import tqdm
from shutil import rmtree
from nltk.tokenize import word_tokenize, sent_tokenize


# All book summaries from barronsbooknotes.com redirect to pinkmonkey.com

# PARAMS
MAIN_SITE = 'https://web.archive.org/web/20180820042551/http://barronsbooknotes.com/'

alphabet_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u', 'v', 'w', 'z']

SEED_URL = 'https://web.archive.org/web/20180820042551/http://barronsbooknotes.com/'

def scrape_index_pages(seed_page):
# For each summary info

    scraped_links = []
    collected = []

    for char in alphabet_list:
        books_page = seed_page + char + ".html"

        soup = BeautifulSoup(urllib.request.urlopen(books_page), "html.parser")
        items = soup.findAll("div", {"align": "left"})
        books = items[0].findAll("a")

        # # # Go over each section
        for index, item in enumerate(books):
            # Parse section to get bullet point text
            try:

                item_title = " ".join(item.text.strip().split())
                item_url = [char for char in item.get("href")]
                item_url[-5] = '2'

                item_url = "".join(item_url)

                if item_title != "":

                    print ("item_title: ", item_title)
                    print ("item_url: ", item_url.strip())
                    print ("\n")

                
                    scraped_links.append({
                        "title": " ".join(item_title.split()),
                        "url": urllib.parse.urljoin(MAIN_SITE, item_url.strip())
                    })

            except Exception as e:
                print ("Link not found")
                print (e)
                
    return scraped_links

# generate literature links
scraped_data = scrape_index_pages(SEED_URL)

with open("literature_links_new.tsv", "w") as fd:
    for data in scraped_data:
        fd.write("%s\t%s\n" % (data["title"], data["url"]))
