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
import time

# PARAMS
MAIN_SITE = 'https://web.archive.org/web/20210111015641/http://thebestnotes.com/'

alphabet_list = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'QR', 'S', 'T', 'UV', 'W', 'XYZ']

SEED_URL = 'https://web.archive.org/web/20210111015641/http://thebestnotes.com/list/titles'

errors_file = open("link_errors.txt","w")

def scrape_index_pages(seed_page):
# For each summary info

    scraped_links = []

    for char in alphabet_list:
        books_page = seed_page + char + ".html"

        try:
            soup = BeautifulSoup(urllib.request.urlopen(books_page), "html.parser")
            items = soup.findAll("div", {"class": "large-7 columns"})
            books = items[0].findAll("p")
        except Exception as e:
            time.sleep(10)
            
            # In order to handle timeouts
            try:
                soup = BeautifulSoup(urllib.request.urlopen(books_page), "html.parser")
                items = soup.findAll("div", {"class": "large-7 columns"})
                books = items[0].findAll("p")
            except Exception as e:
                print ("Skipping: ", books_page, str(e))
                errors_file.write(books_page + "\t" + str(e) + "\n")
                continue

        # # # Go over each section
        for index, item in enumerate(books):
            # Parse section to get bullet point text
            
            try:
                item_title = item.find("a").text
                item_url = item.find("a").get("href")

                print ("item_title: ", " ".join(item_title.split()))
                print ("item_url: ", item_url.strip(), "\n")

                #Don't add the book to the list if it isn't freely available
                if 'store' in item_url:
                    continue

                scraped_links.append({
                    "title": " ".join(item_title.split()),
                    "url": urllib.parse.urljoin(MAIN_SITE, item_url.strip())
                })
            
            except Exception as e:
                print ("Skipping: ", str(item), str(e), "\n")
                errors_file.write(str(item) + "\t" + str(e) + "\n")

    return scraped_links

# generate literature links
scraped_data = scrape_index_pages(SEED_URL)

with open("literature_links.tsv", "w") as fd:
    for data in scraped_data:
        fd.write("%s\t%s\n" % (data["title"], data["url"]))
