"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */

The script separates cleans the summary text along with separating the analysis, notes and commentary from the summaries.

"""


import json
import os
from unidecode import unidecode
import re
from tqdm import tqdm
from os.path import basename
from multiprocessing import Pool
import spacy
import string


sources = ['gradesaver', 'shmoop',  'cliffnotes', 'sparknotes', 'pinkmonkey', 'bookwolf',  'novelguide', 'thebestnotes']

def clean_summary(source):

    print ("Cleaning source: ", source)

    source_summary_dir_base = "../cleaning_phase/"
    dest_dir_base = "../finished_summaries/"

    spacy_nlp = spacy.load("en_core_web_lg")

    source_summary_dir = os.path.join(source_summary_dir_base, source)
    dest_dir = os.path.join(dest_dir_base, source)

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)


    def remove_initial_prefixes(line, full_summary_content = False):
    
        line = line.strip()

        #TODO: Need to pass source name for just pinkmonkey?
        # Required for some book summaries from pinkmonkey.com
        pat_story_summary = '(.*?)(SUMMARY.*$)'

        if re.match(pat_story_summary, line):
            to_replace = re.match(pat_story_summary, line).group(1)
            line = line.replace(to_replace, "", 1).strip()
        
        line = line.replace('Scene Summaries With Notes', "").strip()   # Conflicts with separating notes in pinkmonkey

        pat_pinkmonkey_noise = '^(History is littered with.*?)(Chapter|Scene|Summary)'

        if re.match(pat_pinkmonkey_noise, line):
            to_replace = re.match(pat_pinkmonkey_noise, line).group(1)
            line = line.replace(to_replace, "").strip()

        
        pat = '^((.*?)summary|analysis|summary and analysis|summary & analysis)[ ]{0,}[-:]{0,}'

        if re.search(pat, line, re.IGNORECASE):
            to_replace = re.match(pat, line, re.IGNORECASE).group(0)
             # summary keyword may occur at various places; need to keep the length of the prefix in check
             # if longer than 150 characters, we err on the side of caution and don't clean the text
            if len(to_replace) < 150:
                line = line.replace(to_replace,"", 1).strip()

        if not full_summary_content:

            line = line.replace("<PARAGRAPH>", " ").strip()
            line = line.replace("PARAGRAPH>", " ").strip()
        
        # Required to remove white noise in novelguide summaries
        pat_period_line_break = '.*(\.(\\n\\t)+[ ]?(\\n\\t)*).*'

        if re.match(pat_period_line_break, line):
            to_replace = re.match(pat_period_line_break, line).group(1)
            line = line.replace(to_replace, ". ")

        pat_line_break = '.*((\\n\\t)+[ ]?(\\n\\t)*).*'

        if re.match(pat_line_break, line):
            to_replace = re.match(pat_line_break, line).group(1)
            line = line.replace(to_replace, " . ")

        return line.strip()

    def unify_text(text):
        text_lower = text.lower().strip()
        text_unified = unidecode(text_lower.translate(str.maketrans('', '', string.punctuation)).replace(' ', '')).strip()
        return text_unified

    def remove_prefixes(line, summary_name, is_analysis_text = False):

        line = line.strip()

        # When removing the summary name prefix, we make sure that the text after the prefix has an upper case character, (or quotation marks)
        # This allows removing the prefix in cases where the text may read - "Chapter 5 The chapter begins with...", but doesn't remove prefixes where the prefix
        # may be a part of the sentence, eg. - "Chapter 5 begins with Sir Peter and ..."
        
        if summary_name != "":

            pat_summary_name = '^([ ,:]{0,}%s[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$)' % (summary_name)    # Some cases have punctuations before the summary name

            if re.search(pat_summary_name, line, re.IGNORECASE):
                to_replace = re.match(pat_summary_name, line, re.IGNORECASE).group(1)
                line = line.replace(to_replace,"", 1).strip()
        
        pat_part_chapter = '^(part [ivxl|0-9]{1,}[ ,]{1,}chapter [ivxl|0-9]{1,}[ :])(.*$)'

        pat_act_scene = '^(act ([ivxl|0-9]{1,})[ ,-]{0,}[ ]{1,}(scene) ([ivxl|0-9]{1,})[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$)'

        pat2 = '^([,]{0,}[ ]{0,}(chapters|chapter|act|scene) ([ivxl|0-9]{1,}[ ]{0,}[,-]{1,}[ ]{0,}[ivxl|0-9]{1,})[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$)'

        of_pat2 = '^(of (chapters|chapter|act|scene) ([ivxl|0-9]{1,}[ ]{0,}[,-]{0,}[ ]{0,}[ivxl|0-9]{0,})[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$)'

        pat3 = '^((chapters|chapter|act|scene) ([ivxl|0-9]{1,})[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$)'

        pat_nl = '^((chapters|chapter|act|scene) (twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([-|–]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$)'
        
        of_pat_nl = '^((of (chapters|chapter|act|scene) (twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([-|–]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?[ :,-.]{1,})(?-i:[A-Z|\"|\']+.*$))'

        if re.search(pat_part_chapter, line, re.IGNORECASE):
            to_replace = re.match(pat_part_chapter, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(pat_act_scene, line, re.IGNORECASE):
            to_replace = re.match(pat_act_scene, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()
        
        if re.search(pat_nl, line, re.IGNORECASE):
            to_replace = re.match(pat_nl, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(of_pat_nl, line, re.IGNORECASE):
            to_replace = re.match(of_pat_nl, line, re.IGNORECASE).group(2)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(of_pat2, line, re.IGNORECASE):
            to_replace = re.match(of_pat2, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(pat2, line, re.IGNORECASE):
            to_replace = re.match(pat2, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(pat3, line, re.IGNORECASE):
            to_replace = re.match(pat3, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(pat_part_chapter, line, re.IGNORECASE):
            to_replace = re.match(pat_part_chapter, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(pat3, line, re.IGNORECASE):
            to_replace = re.match(pat3, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        if re.search(pat3, line, re.IGNORECASE):
            to_replace = re.match(pat3, line, re.IGNORECASE).group(1)
            line = line.replace(to_replace,"", 1).strip()

        return line.strip()

    def check_download_links(line):
        if 'Click on' in line or 'Click over' in line or 'Click that' in line or 'Click to' in line or 'Check out' in line or 'download' in line:
            return ""
        return line

    def remove_misc_content(line):

        line = line.replace("See Important Quotations Explained", "").strip()
        line = line.replace("Your browser does not support the IFRAME tag.", "").strip()

        # Need to remove this noisy text from other alignments as well that are not aggregates
        pat_translation = '^(.*)(Read a translation of.*?(scene|scenes|chapter|chapters|act) [ivxl|0-9]{1,}(.*?)-[ ]{0,})(.*$)'


        # Remove the "Read a translation of.." line
        if re.match(pat_translation, line, re.IGNORECASE):
            while re.match(pat_translation, line, re.IGNORECASE):
                to_replace = re.match(pat_translation, line, re.IGNORECASE).group(2)
                line = line.replace(to_replace," ").strip()
        
        # Remove any left-over noisy text that wasn't caught by the regex
        line = line.replace("Read a translation of", " ").strip()

        # To handle a recurring noisy fragment
        if "aEUR\"" in line:
            line = line.replace("aEUR\"", "")

        line = check_download_links(line)

        return line.strip()

    book_count = 0

    for book_name in os.listdir(source_summary_dir):

        book_count += 1
            
        book_name_dir = os.path.join(source_summary_dir, book_name)
        book_dir = os.path.join(dest_dir, book_name)

        print ("book_name_dir: ", book_name_dir)

        if not os.path.exists(book_dir):
            os.makedirs(book_dir)

        for section in os.listdir(book_name_dir):

            summary_path = os.path.join(book_name_dir, section)

            fp = open(summary_path,"r")

            try:
                summary_json = json.loads(fp.readlines()[0])
            except:
                print (book_name_dir, "=Error reading json==", section)
                continue            

            new_json_dict = {}

            new_json_dict['name'] = unidecode(summary_json['name'])
            if 'url' in summary_json:
                new_json_dict['url'] = unidecode(summary_json['url'])

            summary_list = []
            analysis_list = []

            analysis_already_present = 0

            # Check for Analysis text first, if already found during data collection
            if 'analysis' in summary_json and summary_json['analysis'] is not None and summary_json['analysis'].strip() != "":
                analysis_already_present = 1
                for paragraph in list(filter(None, re.split("<PARAGRAPH>|PARAGRAPH>", summary_json['analysis']))):
                    cleaned_paragraph = remove_initial_prefixes(unidecode(paragraph.replace("\t"," ").replace("\n"," ")).strip())
                    if cleaned_paragraph != "":
                        analysis_list.append(cleaned_paragraph)

            analysis_start = 0
            start_adding_lines = 0

            # Handling some typos in summary text that affect cleaning

            if book_name == 'Pygmalion' and section == 'section_0_part_0.txt':
                summary_json['summary'] = summary_json['summary'].replace("Summary and Commentary on Preface", "")

            if source == 'pinkmonkey' and book_name == 'Main Street' and section == 'section_27_part_0.txt':
                summary_json['summary'] = summary_json['summary'].replace("Carol Notes that", "Carol notes that")

            if source == 'pinkmonkey' and book_name == 'Middlemarch' and section == 'section_1_part_0.txt':
                summary_json['summary'] = summary_json['summary'].replace('promptly Notes', 'promptly notes')

            if source == 'pinkmonkey' and book_name == 'Middlemarch' and section == 'section_27_part_0.txt':
                summary_json['summary'] = summary_json['summary'].replace('but Notes Casaubon\’s', 'but notes Casaubon\’s')

            if source == 'pinkmonkey' and book_name == 'Middlemarch' and section == 'section_28_part_0.txt':
                summary_json['summary'] = summary_json['summary'].replace('copies out his Notes', 'copies out his notes')
                

            # Filter out the noisy text before the Summary keywords
            summary_content = remove_initial_prefixes(summary_json['summary'], full_summary_content=True)

            # for line in summary_content.split("<PARAGRAPH>"):
            for paragraph in list(filter(None, re.split("<PARAGRAPH>|PARAGRAPH>", summary_content))):

                # Shmoop summaries have these keywords that affects the cleaning of Analysis
                if source == 'shmoop' and ("Character Analysis" in paragraph or "Character Clues" in paragraph):
                    continue

                if 'Analysis' in paragraph or 'Commentary' in paragraph or 'Notes' in paragraph or 'Interpretation' in paragraph:
                    
                    # if 'Analysis' keyword is present, sentence tokenize the paragraph and ignore the lines after the 'Analysis' keyword
                    sub_lines = [sent.text for sent in list(spacy_nlp(paragraph).sents)]
                    sub_lines = list(filter(None, sub_lines))

                    summary_sub_lines_to_include = []
                    analysis_sub_lines_to_include = []

                    # Capture text before the Analysis related keywords, in that sub-line
                    pat_analysis_separators = "^((.*?)(Analysis|Commentary|Notes|Interpretation))"

                    for sub_line in sub_lines:

                        sub_line = sub_line.strip()

                        if sub_line == "":
                            continue

                        # if the line begins with the keyword 'Analysis', 'Commentary' or 'Notes'
                        if re.match(pat_analysis_separators, sub_line):
                            analysis_start = 1

                        # Analysis text starts after the Analysis tag is found
                        if analysis_start:
                            if sub_line == '"' and analysis_sub_lines_to_include != []:
                                analysis_sub_lines_to_include[-1] = analysis_sub_lines_to_include[-1] + sub_line
                            else:
                                analysis_sub_lines_to_include.append(sub_line)
                        else:
                            if sub_line == '"' and summary_sub_lines_to_include != []:
                                summary_sub_lines_to_include[-1] = summary_sub_lines_to_include[-1] + sub_line
                            else:
                                summary_sub_lines_to_include.append(sub_line)

                    # Since spacy has been used to sentence tokenize the paragraph, we can just join on ' '
                    # Otherwise we might just introduce extra periods in the process
                    cleaned_summ_line = remove_misc_content(remove_initial_prefixes(unidecode(' '.join(summary_sub_lines_to_include)).replace("\t"," ").replace("\n"," ").strip())) 
                    
                    if cleaned_summ_line != "":
                        summary_list.append(cleaned_summ_line)
                        
                    cleaned_analysis_line = remove_misc_content(remove_initial_prefixes(unidecode(' '.join(analysis_sub_lines_to_include)).replace("\t"," ").replace("\n"," ").strip() ))
                    if cleaned_analysis_line != "":
                        analysis_list.append(cleaned_analysis_line)

                if not analysis_start:
                    cleaned_paragraph = remove_misc_content(remove_initial_prefixes(unidecode(paragraph.replace("\t"," ").replace("\n"," ")).strip()))
                    if cleaned_paragraph != "":
                        summary_list.append(" ".join(cleaned_paragraph.split()))

                
                # Only add to the analysis list if there 
                # 1. Analysis keyword was found in the beginning of sub-line, 
                # 2. We have skipped that whole line, 
                # 3. The analysis wasn't already present in the json
                if analysis_start and start_adding_lines and not analysis_already_present:
                    cleaned_paragraph = remove_misc_content(remove_initial_prefixes(unidecode(paragraph.replace("\t"," ").replace("\n"," ")).strip()))
                    if cleaned_paragraph != "":
                        analysis_list.append(" ".join(cleaned_paragraph.split()))

                # We start including the lines to the analysis from the next one after the one in which we found 'Analysis' keyword
                if analysis_start == 1:
                    start_adding_lines = 1

            section_path = os.path.join(book_dir, section)

            summary_text = " ".join(summary_list)
            analysis_text = " ".join(analysis_list)

            # Remove prefixes to have cleaner summaries
            if summary_text != "":
                summary_text = remove_prefixes(summary_text, new_json_dict['name'].strip(), is_analysis_text=False)
            
            if analysis_text != "":
                analysis_text = remove_prefixes(analysis_text, new_json_dict['name'].strip(), is_analysis_text=True)

            new_json_dict['summary'] = summary_text
            new_json_dict['analysis'] = analysis_text

            with open(section_path, "w") as fout:
                json.dump(new_json_dict, fout)

    print ("source: ", source, " book_count: ", book_count)

n_cpus = 8

with Pool(n_cpus) as p:
    p.map(clean_summary, sources)