"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */

This script is used to separate summaries of the following kind from the summary text:

Chapter 1 Summary:
Chapter 2 Summary:
Chapter 3 Summary:
.
.

Using a mapping of which chapter-summary alignments are aggregates, 
this script splits those summary texts into multiple summaries using various regexes and cleaning operations.

"""
import json
import os
import re
from os.path import basename, dirname
from word2number import w2n
from unidecode import unidecode
from tqdm import tqdm
from string import punctuation

#An intermediate matched file is required 
matched_books = "../../alignments/chapter_summary_aligned.jsonl.aggregate_splits"

chapterized_books_dir = "../../" # Path to the chapterized books directory. Modify paths if needed

# Error file to keep track of different error cases
f_all_errors = open("splitting_aggregates_errors.txt", "w")

def romanToInt(s):

    roman = {'i':1,'v':5,'x':10,'l':50,'c':100,'d':500,'m':1000,'iv':4,'ix':9,'xl':40,'xc':90,'cd':400,'cm':900}
    i = 0
    num = 0
    while i < len(s):
        if i+1<len(s) and s[i:i+2] in roman:
            num += roman[s[i:i+2]]
            i += 2
        else:
            num += roman[s[i]]
            i += 1
        
    return num

# Saves the summaries we have broken down into new section jsons, along with the new section name

def save_separated_summaries(separated_summaries, summary_json, summary_path, book_name):


    old_section_name = os.path.basename(summary_path)
    old_section_name = old_section_name.split('_part_0.txt')[0]
    summary_dir = os.path.dirname(summary_path)

    count = 0
    for key, summary in separated_summaries.items():
        count += 1

        fout_name = os.path.join(summary_dir,old_section_name + "_part_{}.txt".format(str(count)))
        print ("fout_name: ", fout_name)

        section_json = {}
        section_json['name'] = key
        section_json['summary'] = summary
        if 'analysis' in summary_json:
            section_json['analysis'] = summary_json['analysis']
        else:
            section_json['analysis'] = ""

        if 'url' in summary_json:
            section_json['url'] = summary_json['url']
        else:
            section_json['url'] = ""

        fout = open(fout_name,"w")
        json.dump(section_json, fout)


    return count - 1


def replace_pat2(matched_str):

    if matched_str.group(1) != "":
        num = matched_str.group(1).strip()
    else:
        num = matched_str.group(2).strip()

    try:
        ret = matched_str.group(0).replace(num, str(w2n.word_to_num(num)))
    except ValueError:
        num = matched_str.group(2).strip()
        ret = matched_str.group(0).replace(num, str(w2n.word_to_num(num)))

    return ret

# Separates the multiple chapter summaries we have found
def separate_mulitple_summaries(summary_content, section_name_prefix, summary_path):

    pat_num_rom = '^(?:PARAGRAPH>)?(?:In)?([ ]{0,}(chapter|book|scene)[ ]{1,}([ivxl|0-9]{1,}))[^a-z0-9]?'

    pat_act_scene = '^(?:PARAGRAPH>)?(?:In)?([ ]{0,}(act)[ ]{1,}([ivxl|0-9]{1,})[,-]{0,}[ ]{1,}(scene)[ ]{1,}([ivxl|0-9]{1,}))[^a-z0-9]?'

    pat_nl = '^(?:PARAGRAPH>)?(?:In)?([ ]{0,}(chapter|book|scene)[ ]{1,}(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([-|–]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)(.*$)'
    # Also need to convert in this case

    pat_part_chapter = '^(part [ivxl|0-9]{1,} chapter [ivxl|0-9]{1,}):(.*$)'


    #Break the entire summary content into lines and check for <PARAGRAPH> tag too in the regex
    # We break on period, exclamation mark and question mark, all 3
    lines = list(filter(None, re.split("[.|!|?]", summary_content)))

    # dict with both the summary and the section name
    summaries = {}
    summary = []
    section_name = ""
    for line in lines:
        line =  line.strip()

        if line == "":
            continue

        line  = remove_prefixes_line(line)

        if line == "":
            continue

        # Because we can have a mix of roman, numeric and natural language numbers
        if re.match(pat_num_rom, line, re.IGNORECASE) or re.match(pat_nl, line, re.IGNORECASE)\
        or re.match(pat_act_scene, line, re.IGNORECASE) or re.match(pat_part_chapter, line, re.IGNORECASE):
            
            if summary == []:
                summary.append(line)
            else:
                if section_name_prefix != "" and 'act' not in section_name.strip().lower():
                    section_name = section_name_prefix + ", " + section_name
                
                if section_name not in summaries:
                    summaries[section_name] = ". ".join(summary)

                    if section_name.strip() == "":
                        f_all_errors.write("Section name empty" + "\t" + summary_path)
                        f_all_errors.write("\n")

                summary = []
                summary.append(line)


            if re.match(pat_nl, line, re.IGNORECASE):
                section_name = re.match(pat_nl, line, re.IGNORECASE).group(1)

                splits = section_name.split()
                section_name = " ".join([splits[0], str(w2n.word_to_num(splits[1]))])
                section_name = section_name.strip()

            elif re.match(pat_num_rom, line, re.IGNORECASE):
                section_name = re.match(pat_num_rom, line, re.IGNORECASE).group(1)
                section_name = section_name.strip()

            elif re.match(pat_part_chapter, line, re.IGNORECASE):
                section_name = re.match(pat_part_chapter, line, re.IGNORECASE).group(1)
                section_name = section_name.strip()

            elif re.match(pat_act_scene, line, re.IGNORECASE):
                section_name = re.match(pat_act_scene, line, re.IGNORECASE).group(1)
                section_name = section_name.strip()
            
        else:
            summary.append(line)

    if summary != []:
        if section_name_prefix != "" and section_name != "" and 'act' not in section_name.strip().lower():
            section_name = section_name_prefix + ", " + section_name
        if section_name not in summaries:
            summaries[section_name] = ". ".join(summary)

    return summaries

    
# Remove prefixes from every summary to further check for the combined/multiple summaries
def remove_prefixes_line(line):

    line = line.strip().replace("\n"," ").replace("\t"," ").replace("<PARAGRAPH><PARAGRAPH>", "<PARAGRAPH>")
    
    # Remove the "See Important Quotations Explained" line
    line = line.replace("See Important Quotations Explained", "").strip()

    # Special cases for splitting sparknotes/A Tale of Two Cities, The Scarlet Letter
    line = line.replace("Chapter 5: The Wine-shop", "Chapter 5: The Wine shop").strip()
    line = line.replace("Chapter 13: Fifty-two", "Chapter 13: Fifty two").strip()
    line = line.replace("Chapter 1: The Prison-Door", "Chapter 1: The Prison Door").strip()
    line = line.replace("Chapter 19: The Child at the Brook-Side", "Chapter 19: The Child at the Brook Side").strip()


    #Remove any leading punctuations
    line = line.lstrip(punctuation).strip()

    pat_translation = '^([<PARAGRAPH>]{0,}Read a translation of.*?(scene|scenes|chapter|chapters|act) [ivxl|0-9]{1,}(.*?)-[ ]{0,})(.*$)'

    # Remove the "Read a translation of.." line
    if re.match(pat_translation, line, re.IGNORECASE):
        to_replace = re.match(pat_translation, line, re.IGNORECASE).group(1)
        line = line.replace(to_replace,"").strip()

    line = line.replace("The tension over George mounts in ", "").strip() # For a specific book chapter. TODO: Which one?
    
    # of Vol. II, 
    pat = '^((of Vol.)[ ]{0,}[ivxl][ ]{0,}[:|,|-]{0,})'

    if re.search(pat, line, re.IGNORECASE):
        to_replace = re.match(pat, line, re.IGNORECASE).group(0)
        line = line.replace(to_replace,"").strip()

    pat = '^([<PARAGRAPH>]{0,}(summary|summary and analysis|summary & analysis)[ ]{0,}[:|,|-|;]{0,})'

    if re.search(pat, line, re.IGNORECASE):
        to_replace = re.match(pat, line, re.IGNORECASE).group(0)
        line = line.replace(to_replace,"").strip()

    #Remove any leading punctuations
    line = line.lstrip(punctuation).strip()

    return line.strip()


# Remove prefixes from the summaries as a pre-processing step to splitting
def remove_prefixes_summary(summary):


    # regex for handling white spaces like '\n\t' that affect splitting of the summary text
    pat_period_line_break = '.*(\.(\\n\\t)+[ ]?(\\n\\t)*).*'

    if re.match(pat_period_line_break, summary):
        to_replace = re.match(pat_period_line_break, summary).group(1)
        summary = summary.replace(to_replace, ". ")

    pat_line_break = '.*((\\n\\t)+[ ]?(\\n\\t)*).*'

    if re.match(pat_line_break, summary):
        to_replace = re.match(pat_line_break, summary).group(1)
        summary = summary.replace(to_replace, " . ")

    summary = summary.strip().replace("\n"," ")

    # Handle specific typos in collected summaries that affect the splitting script
    summary = summary.replace("In \"Cloud,\" Chapter XXXVIII", "In Chapter XXXVIII")
    summary = summary.replace("Summary -- Act V, scene, i  Fifteen years later", "Summary -- Act V, scene i  Fifteen years later")
    summary = summary.replace("Act IV Scenes v-vii & Act V Scene i", "")
    summary = summary.replace("Indeed the whole tone of the Notes has shifted", "Indeed the whole tone of the notes has shifted")

    pat_chap = '(.*?)Chapter [ivxl|0-9]{1,}[^a-z]'
    pat_scene = '(.*?)Scene [ivxl|0-9]{1,}[^a-z]'
    
    pat7 = '(.*?)(chapter|scene ((twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([,-]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)).*$'
    
    if re.search(pat_chap, summary, re.IGNORECASE):
        to_replace = re.search(pat_chap, summary, re.IGNORECASE).group(1)

        if len(to_replace) < 150:   # Keep the length of the prefix to remove in check
            summary = summary.replace(to_replace,"")

    summary = summary.strip() #We can remove multiple prefixes

    if re.search(pat_scene, summary, re.IGNORECASE):
        to_replace = re.search(pat_scene, summary, re.IGNORECASE).group(1)
        if len(to_replace) < 150:
            summary = summary.replace(to_replace,"")

    summary = summary.strip()

    if re.search(pat7, summary, re.IGNORECASE):
        to_replace = re.search(pat7, summary, re.IGNORECASE).group(1)
        if len(to_replace) < 150:
            summary = summary.replace(to_replace,"")

    summary.strip()

    pat = '^((summary|summary and analysis|summary & analysis)[ ]{0,}[:|,|-]{0,})'

    if re.search(pat, summary, re.IGNORECASE):
        to_replace = re.match(pat, summary, re.IGNORECASE).group(0)
        summary = summary.replace(to_replace,"")

    summary = summary.strip()

    pat2 = '^[ ]{0,}[<PARAGRAPH>]{0,}[ ]{0,}((chapters|chapter) ([ivxl|0-9+]{1,}[,|-|–]){1,}[ivxl|0-9+]{1,})(.*$)'

    if re.search(pat2, summary, re.IGNORECASE):
        prefix = re.match(pat2, summary, re.IGNORECASE).group(1)
        summary = summary.replace(prefix,"")

    return summary.strip()

multiple_summaries = 0
total_new_summaries = 0
summary_path_missing = []
counter = 0


fp = open(matched_books, "r")
fp_lines = fp.readlines()

for line in tqdm(fp_lines):
    line = line.strip()
    x = json.loads(line)
    counter += 1
    
    summaries_counted = 0

    prev_book_unique_id = ""

    book_unique_id = x['book_unique_id']

    source = basename(dirname(dirname(x['summary_path'])))
    book_name = basename(dirname(x['summary_path']))
    
    section_name = basename(x['summary_path'])

    # Capture the number of splits required from each summary file
    splits_reqd = [item['summary_path'] for item in x['splits']]
    num_splits_reqd = len(splits_reqd)
    
    if (book_unique_id != prev_book_unique_id) and prev_book_unique_id != "":
        summaries_counted = 0

    summary_path =  os.path.join("../", x['summary_path'])

    if not os.path.exists(summary_path):
        # Summary path missing
        summary_path_missing.append(summary_path)
        continue

    try:
        fx = open(summary_path, "r")
    except Exception as e:
        print (e)
        f_all_errors.write("Error loading summary path" + "\t" +summary_path)
        f_all_errors.write("\n")
        continue

    summary_json = json.load(fx)
    
    summary_content = summary_json['summary']

    og_summary_content = summary_content

    # Handling typos in specific books that can make splitting summaries easier
    if source == 'cliffnotes' and book_name == "The Merry Wives of Windsor" and 'section_10_part_0.txt' in x['summary_path']:
        summary_content = "Scene 2 " + summary_content

    if "CHAPTER 1Summary" in summary_content:
        summary_content = summary_content.replace("CHAPTER SUMMARIES WITH NOTES   PHASE THE FIRST  - THE MAIDEN", "").replace("CHAPTER 1Summary", "CHAPTER 1 Summary")

    if source == 'sparknotes' and book_name == "Cyrano de Bergerac":
        summary_content = summary_content.replace("Act IV, scenes vi-x  Summary -- Act IV", "Summary -- Act IV")

    if source == 'novelguide' and book_name == "Henry VI Part 1" and section_name == 'section_4_part_0.txt':
        summary_content = summary_content.replace('scence 6', 'scene 6')

    if source == 'novelguide' and book_name == "Cyrano de Bergerac" and section_name == 'section_8_part_0.txt':
        summary_content = summary_content.replace('Act, 5, scene 5', 'Act 5, scene 5')

    if source == 'pinkmonkey' and book_name == 'Emma' and section_name == 'section_10_part_0.txt':
        summary_content = summary_content.replace('CHAPTERS 11 & 12', 'CHAPTER 11-12')
    
    if source == 'pinkmonkey' and book_name == 'Jude the Obscure' and section_name == 'section_4_part_0.txt': 
        summary_content = summary_content.replace('PART II CHAPTER 1 Summary', 'CHAPTER 1 Summary')

    summary_content = remove_prefixes_summary(summary_content)

    section_name_prefix = x['section_name_prefix']

    if '-' in section_name_prefix or section_name_prefix == 'epilogue':
        section_name_prefix = ""

    separated_summaries = separate_mulitple_summaries(summary_content, section_name_prefix, summary_path)

    total_new_summaries += len(separated_summaries.keys())

    print ("num_splits_reqd: ", splits_reqd, num_splits_reqd)
    print ("separated_summaries keys: ", separated_summaries.keys(), len(separated_summaries.keys()))
    
    assert num_splits_reqd <= len(separated_summaries.keys())
    # We can potentially split a summary text into more number of sections than we're able to match with the book chapters in gutenberg

    # No need to separate and use the new section name if we only have one single summary found after breaking
    # Also protects against some false positives wrt splitting the sections
    if len(separated_summaries.keys()) == 1:
        continue
    else:
        multiple_summaries += 1

        # If there is an empty section name, it means we couldn't find a section name to match that summary to a chapter
        if '' in separated_summaries.keys():
            separated_summaries.pop('')
            summaries_counted += save_separated_summaries(separated_summaries, summary_json, summary_path, book_name)
        else:
            summaries_counted += save_separated_summaries(separated_summaries, summary_json, summary_path, book_name)
        
        os.remove(summary_path)
            
