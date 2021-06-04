"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */
"""


import json
import os
from unidecode import unidecode
import re
from tqdm import tqdm
from os.path import basename

# We clean one source at a time
sources = ['gradesaver', 'shmoop',  'cliffnotes', 'sparknotes','pinkmonkey', 'bookwolf',  'novelguide', 'thebestnotes']

for ix, source in tqdm(enumerate(sources)):

    print ("Cleaning source: ", source)

    source_summary_dir_base = "../cleaning_phase/"
    dest_dir_base = "../finished_summaries/"


    source_summary_dir = os.path.join(source_summary_dir_base, source)
    dest_dir = os.path.join(dest_dir_base, source)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    """
    The script cleans the leftover unicode characters along with some analysis present in the text,
    as in /export/longsum/chaptersum/cleaned_summaries/gradesaver/Alice in Wonderland

    Weird - /export/longsum/chaptersum/cleaned_summaries/gradesaver/Winesburg, Ohio

    This one should be able to fix all the occurences of Analysis inside the summary
    Prefix cleanup we can leave for the next script? 
    Just cleanup prefixes with summary and summary & analysis
    """


    def remove_section_prefixes_suffixes(summary, name):

        pat_suffix = '(.*)(Commentary (.*))'

        if re.search(pat_suffix, summary, re.IGNORECASE):
            matched_str = re.match(pat_suffix, summary, re.IGNORECASE)
            to_remove = matched_str.group(2) # Everything after the Commentary keyword
            summary = summary.replace(to_remove, "")

        pat_prefix = '((.*?){}) (.*$)'.format(name)

        if re.search(pat_prefix, summary, re.IGNORECASE):
            matched_str = re.match(pat_prefix, summary, re.IGNORECASE)
            print (matched_str.groups())
            to_remove = matched_str.group(2) # Everything after the Commentary keyword
            # summary = summary.replace(to_remove, "")
            exit()


    def remove_summary_analysis_prefix(line):
        pat = '^((.*?)summary|analysis|summary and analysis|summary & analysis)[ ]{0,}[-:]?'

        if re.search(pat, line, re.IGNORECASE):
            to_replace = re.match(pat, line, re.IGNORECASE).group(0)
            line = line.replace(to_replace,"")

        return line.strip()

    def remove_chapter_prefixes(line):

        pat_act_scene = '(.*?)((act) ([ivxl|0-9]{1,})[,-]{0,}[ ]{1,}(scene) ([ivxl|0-9]{1,}))'

        pat2 = '^((chapters|chapter|act) ([ivxl|0-9]{1,}[,-]{1,}[ivxl|0-9]{1,}))(.*$)'

        of_pat2 = '^(of (chapters|chapter|act) ([ivxl|0-9]{1,}[,-]{1,}[ivxl|0-9]{1,}))(.*$)'


        pat3 = '^((chapters|chapter|act) ([ivxl|0-9]{1,})[:-]{0,})(.*$)'

        pat_nl = '^((chapter|act) (twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([-|–]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)(.*$)'
        
        of_pat_nl = '^((of (chapter|act) (twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([-|–]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)(.*$))'

        # Also removes chapter prefix
        # TODO:Check why not working

        #Should also remove everything before the section name

        if re.search(pat_act_scene, line, re.IGNORECASE):
            to_replace = re.match(pat_act_scene, line, re.IGNORECASE).group(2)
            line = line.replace(to_replace,"")
        
        if re.search(pat_nl, line, re.IGNORECASE):
            to_replace = re.match(pat_nl, line, re.IGNORECASE).group(0)
            line = line.replace(to_replace,"")

        if re.search(of_pat_nl, line, re.IGNORECASE):
            to_replace = re.match(of_pat_nl, line, re.IGNORECASE).group(0)
            line = line.replace(to_replace,"")

        if re.search(of_pat2, line, re.IGNORECASE):
            to_replace = re.match(of_pat2, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"")

        if re.search(pat2, line, re.IGNORECASE):
            to_replace = re.match(pat2, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"")

        if re.search(pat3, line, re.IGNORECASE):
            to_replace = re.match(pat3, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"")

        return line.strip()

    book_count = 0

    for item in os.listdir(source_summary_dir):

        book_count += 1

            
        item_dir = os.path.join(source_summary_dir, item)
        book_dir = os.path.join(dest_dir, item)

        print ("item_dir: ", item_dir)


        if not os.path.exists(book_dir):
            os.makedirs(book_dir)
        else:
            continue

        for section in os.listdir(item_dir):

            summary_path = os.path.join(item_dir, section)

            fp = open(summary_path,"r")

            try:
                summary_json = json.loads(fp.readlines()[0])
            except:
                print (item_dir, "=Error reading json==", section)
                # continue            

            new_json_dict = {}

            new_json_dict['name'] = unidecode(summary_json['name'])
            if 'url' in summary_json:
                new_json_dict['url'] = unidecode(summary_json['url'])

            summary_list = []
            analysis_list = []

            analysis_already_present = 0

            if 'analysis' in summary_json and summary_json['analysis'] is not None and summary_json['analysis'].strip() != "":
                # print ("Analysis already present")
                analysis_already_present = 1
                for line in summary_json['analysis'].split("<PARAGRAPH>"):
                    cleaned_line = remove_chapter_prefixes(remove_summary_analysis_prefix(unidecode(line.replace("\t"," ").replace("\n"," ")).strip()))
                    if cleaned_line != "":
                        analysis_list.append(cleaned_line)


            analysis_start = 0
            start_adding_lines = 0

            summary_content = remove_summary_analysis_prefix(summary_json['summary'])
            #Filter out all the notes and the commentary before the Summary keywords
            #So when we filter for Notes later, it won't conflict


            for line in summary_content.split("<PARAGRAPH>"):

                # if analysis keyword is present, break the lines by (.) period 
                # and then ignore the lines after the 'Analysis' keyword

                if 'Analysis' in line or 'Commentary' in line or 'Notes' in line:
                    
                    # print ("ANALYSIS/COMMENTARY/NOTES IN ABOVE LINE")

                    sub_lines = list(filter(None, re.split("[.'\"!?]", line)))
                    summary_sub_lines_to_include = []
                    analysis_sub_lines_to_include = []

                    # do not extract the analysis if there is already a separate section present for it
                    # 'Analysis' keyword should be at the beginning of the line for extraction

                    pat = "^(Analysis|Commentary|Notes)"

                    for sub_line in sub_lines:
                        sub_line = sub_line.strip()
                        
                        # if the line begins with the keyword 'Analysis'
                        if re.match(pat, sub_line):
                            analysis_start = 1

                        # if analysis_start and not analysis_already_present:
                        # We may have some left over analysis from the text
                        if analysis_start:
                            analysis_sub_lines_to_include.append(sub_line)
                            # we don't know if we want the whole line to be included
                            # But if there is only one line which has the summary as well as the analysis,
                            # all the sub-lines after the analysis keyword is found would be added
                        else:
                            summary_sub_lines_to_include.append(sub_line)


                    cleaned_summ_line = remove_chapter_prefixes(remove_summary_analysis_prefix(unidecode('. '.join(summary_sub_lines_to_include)).replace("\t"," ").replace("\n"," ").strip())) 
                    if cleaned_summ_line != "":
                        summary_list.append(cleaned_summ_line)

                    cleaned_analysis_line = remove_chapter_prefixes(remove_summary_analysis_prefix(unidecode('. '.join(analysis_sub_lines_to_include)).replace("\t"," ").replace("\n"," ").strip() ))
                    if cleaned_analysis_line != "":
                        analysis_list.append(cleaned_analysis_line)

                # If analysis_already_present in json = 1, then we don't need to wait for the anaysis start tag to add stuff the summary
                # Otherwise, we keep adding lines to the summary which do not belong to the analysis
                if analysis_start and analysis_already_present:
                    pass
                elif analysis_already_present or not analysis_start:
                    cleaned_line = remove_chapter_prefixes(remove_summary_analysis_prefix(unidecode(line.replace("\t"," ").replace("\n"," ")).strip()))
                    if cleaned_line != "":
                        summary_list.append(" ".join(cleaned_line.split()))

                
                # Only add to the analysis list if there 
                # 1. Analysis keyword was found in the beginning of sub-line, 2. We have skipped that whole line, 
                # and 3. The analysis wasn't already present in the json
                if analysis_start and start_adding_lines and not analysis_already_present:
                    cleaned_line = remove_chapter_prefixes(remove_summary_analysis_prefix(unidecode(line.replace("\t"," ").replace("\n"," ")).strip()))
                    if cleaned_line != "":
                        analysis_list.append(" ".join(cleaned_line.split()))

                if analysis_start == 1:
                    start_adding_lines = 1
                    # We start including the lines to the analysis from the next one after the one in which we found 'Analysis' keyword
                    

            section_path = os.path.join(book_dir, section)

            new_json_dict['summary'] = summary_list
            new_json_dict['analysis'] = analysis_list

            with open(section_path, "w") as fout:
                json.dump(new_json_dict, fout)

    print ("book_count: ", book_count)
