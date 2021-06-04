"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""


# Also converts files from unicode_cleaned directory by adding part_0.txt to all the files before splitting

import json
import os
import re
from unidecode import unidecode

sources = ['gradesaver', 'shmoop',  'cliffnotes', 'sparknotes', 'pinkmonkey', 'bookwolf',  'novelguide', 'thebestnotes']

BASE_DIR = "../raw_summaries/"

for src in sources:

    print ("src: ", src)

    books_dir = os.path.join(BASE_DIR, src, "summaries")
    dest_dir = os.path.join("../cleaning_phase" , src)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for book in os.listdir(books_dir):
        
        book_path = os.path.join(books_dir, book)
        print (book, "===")     

        book_dest = os.path.join(dest_dir, unidecode(book))
        if not os.path.exists(book_dest):
            os.makedirs(book_dest)

        for section in os.listdir(book_path):
            
            summary_path = os.path.join(book_path, section)

            fp = open(summary_path,"r")

            try:
                summary_json = json.loads(fp.readlines()[0])
            except Exception as e:
                print (book, "=Error reading json==", section)
                print (e)           
                continue

            #Remove text inside paranthesis first
            #Sometimes 'Click here' could be inside braces

            #Remove paranthesis first
            if type(summary_json['summary']) is list:
                summary_json['summary'] = " ".join(summary_json['summary'])
            summary_json['summary'] = re.sub("[\(\[].*?[\)\]]", "", summary_json['summary'])
            
            if 'analysis' in summary_json and summary_json['analysis'] is not None:
                if type(summary_json['analysis']) is list:
                    summary_json['analysis'] = " ".join(summary_json['analysis'])
                summary_json['analysis'] = re.sub("[\(\[].*?[\)\]]", "", summary_json['analysis'])

            # print (summary_json['summary'])
            if 'Click' in summary_json['summary']:
                lines = summary_json['summary'].split(".")
                summary_json['summary'] = ""
                new_lines = []
                # print (lines)
                for index, line in enumerate(lines):
                    
                    # Can we just delete the line like that? OR do we need to look the line actually
                    if 'Click on' in line or 'Click over' in line\
                    or 'Click that' in line or 'Click to' in line or 'Check out' in line:
                        continue
                    else:
                        new_lines.append(unidecode(line))

                summary_json['summary'] = ". ".join(new_lines)

            if 'analysis' in summary_json and summary_json['analysis'] is not None and 'Click' in summary_json['analysis']:
                lines = summary_json['analysis'].split(".")
                summary_json['analysis'] = ""
                new_lines = []
                # print (lines)
                for index, line in enumerate(lines):

                    if 'Click on' in line or 'Click over' in line\
                    or 'Click that' in line or 'Click to' in line or 'Check out' in line:
                        continue
                    else:
                        new_lines.append(unidecode(line))

                summary_json['analysis'] = ". ".join(new_lines)

            section_out = section

            if '.txt' in section_out and 'overview' not in section_out:
                section_out = section[0:-4] + "_part_0.txt" #add _part_0 to every summary file for splitting later

            book_dest_path = os.path.join(book_dest, section_out)

            with open(book_dest_path, 'w') as outfile:
                json.dump(summary_json, outfile)
