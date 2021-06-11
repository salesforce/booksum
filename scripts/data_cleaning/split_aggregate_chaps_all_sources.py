"""
/*
 * Copyright (c) 2021, salesforce.com, inc.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 * For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
 */

This script is used to identify and separate summaries of the following kind from scraped summary files:

Chapter 1 Summary:
Chapter 2 Summary:
Chapter 3 Summary:
.
.

Not all combined summaries are separable, but using this script, we try to find the ones that are not a 'true'
combined summary, but rather just a collection of different chapter summaries in the same document.

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
matched_books = "../../alignments/summary_chapter_matched_intermediate.jsonl"
matched_books = "../../alignments/summary_chapter_matched_intermediate.jsonl"
chapterized_books_dir = "../../" # replace with whereever the chapterized books are extracted


f_matched = open(matched_books,"r")
all_matched_titles = []

for line in f_matched:
    x = json.loads(line)
    all_matched_titles.append(x['book_id'].split('.')[0])

# Error file to keep track of different error cases
f_all_errors = open("splitting_aggregates_errors.txt", "w")

# Log file to debug the section splits
f_matched_section_splits = open("matched_section_splits.txt", "w")

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

# Saves the summaries we have broken down into new section jsons, 
# Along with the new section name
def save_separated_summaries(separated_summaries, summary_json, summary_path, section_summary_title):


    old_section_name = os.path.basename(summary_path)
    old_section_name = old_section_name.split('_part_0.txt')[0]
    summary_dir = os.path.dirname(summary_path)

    # print ("summary_path: ", summary_path)

    count = 0
    for key, summary in separated_summaries.items():
        count += 1

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

        fout_name = os.path.join(summary_dir,old_section_name + "_part_{}.txt".format(str(count)))
        print ("fout_name: ", fout_name)

        fout = open(fout_name,"w")
        json.dump(section_json, fout)


    return count - 1


def replace_pat2(matched_str):
    # print (matched_str.groups())

    # try:
    if matched_str.group(1) != "":
        num = matched_str.group(1).strip()
    else:
        num = matched_str.group(2).strip()

    # print ("num: ", num)
    try:
        ret = matched_str.group(0).replace(num, str(w2n.word_to_num(num)))
    except ValueError:
        num = matched_str.group(2).strip()
        ret = matched_str.group(0).replace(num, str(w2n.word_to_num(num)))
    # print ("ret: ", ret, "\n")
    return ret

# Separates the multiple chapter summaries we have found
def separate_mulitple_summaries(summary_content, matched_numeric_roman, matched_numbers_nl, section_name_prefix, summary_path):

    # print ("summary_content: ", summary_content)

    # All patterns should match starting of line
    pat_num_rom = '^(?:PARAGRAPH>)?((chapter|scene) ([ivxl|0-9]{1,}))[^a-z0-9]?'

    pat_act_scene = '^(?:PARAGRAPH>)?((act) ([ivxl|0-9]{1,})[,-]{0,}[ ]{1,}(scene) ([ivxl|0-9]{1,}))[^a-z0-9]?'

    pat_nl = '^(?:PARAGRAPH>)?((chapter|scene) (twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([-|–]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)(.*$)'
    # Also need to convert in this case

    #Break the entire summary content into lines and check for <PARAGRAPH> tag too in the regex
    # We break on period, exclamation mark and question mark, all 3
    lines = list(filter(None, re.split("[.|!|?|\"]", summary_content)))

    # dict with both the summary and the section name
    summaries = {}
    summary = []
    section_name = ""
    for line in lines:
        line =  line.strip()

        line  = remove_prefixes_line(line)

        # Because we can have a mix of roman, numeric and natural language numbers... :(
        if re.match(pat_num_rom, line, re.IGNORECASE) or re.match(pat_nl, line, re.IGNORECASE) or re.match(pat_act_scene, line, re.IGNORECASE):
            
            # if 'chapter' in line or 'act' in line:  #What about act keyword?
            # Why do we even need this check?
            
            if summary == []:
                summary.append(line)
            else:
                if section_name_prefix != "" and 'act' not in section_name.strip().lower():
                    # print ("added section_name_prefix: ", section_name_prefix)
                    section_name = section_name_prefix + ", " + section_name
                
                if section_name not in summaries:
                    # print ("section_name adding: ", section_name)
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
                prev_section_name = section_name
                section_name = re.match(pat_num_rom, line, re.IGNORECASE).group(1)
                # section_name = section_name.strip()

                #Not considered a legit match. Will have to check manually
                # if section_name == 'chapter i':
                #     section_name = prev_section_name
                # print ("section_name: ", section_name)

            elif re.match(pat_act_scene, line, re.IGNORECASE):
                section_name = re.match(pat_act_scene, line, re.IGNORECASE).group(1)
                section_name = section_name.strip()
            
        else:
            summary.append(line)

    if summary != []:
        if section_name_prefix != "" and section_name != "" and 'act' not in section_name.strip().lower():
            section_name = section_name_prefix + ", " + section_name
        if section_name not in summaries:
            summaries[section_name] = ".".join(summary)

    return summaries

# Checks for the presence of muliple unqiue chapters present in the book
# If multiple keywords like 'Chapter' 'Scene' etc followed by a number are found,
# it points towards multiple individual summaries since we already know it is an aggregate
def check_multiple_summaries(summary):

    summary = summary.strip().replace("\n"," ")

    #Matches Chapter 1, followed by some string
    pat1 = "^[<PARAGRAPH>]{0,}(?:chapter|scene) (?:[ivxl|0-9]{1,})[^a-z](.*$)"

    #Matches chapter twenty-two followed by some string
    pat7 = '^[<PARAGRAPH>]{0,}(?:chapter|scene) ((twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([,-]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)(.*$)'

    #Matches Act 1, Scene 3 and Act 1 Scene 3
    pat_act_scene = '^[<PARAGRAPH>]{0,}((act) ([ivxl|0-9]{1,})[,-]{0,}[ ]{1,}(scene) ([ivxl|0-9]{1,}))[^a-z](.*$)'

    # Flag for matching with roman or numeric numbers
    matched_numeric_roman = 0

    # stands for matched numbers natural language
    matched_numbers_nl = 0

    if re.match(pat1, summary, re.IGNORECASE):
        matched_numeric_roman = 1
    
    if re.match(pat_act_scene, summary, re.IGNORECASE):
        matched_numeric_roman = 1

    if re.match(pat7, summary, re.IGNORECASE):
        matched_numbers_nl = 1

    return matched_numeric_roman, matched_numbers_nl
    
def check_book_num_prefix(summary_id):

    pat = '^((book|part) [ivxl|0-9]{1,})[, ]{0,}(.*$)'
    section_name_prefix = ""

    if re.match(pat, summary_id, re.IGNORECASE):
        section_name_prefix = re.match(pat, summary_id, re.IGNORECASE).group(1)
    
    return section_name_prefix


# Remove prefixes from every summary to further check for the combined/multiple summaries
def remove_prefixes_line(line):

    line = line.strip().replace("\n"," ")

    pat_translation = '^(Read a translation of.*?(scene|chapter) [ivxl|0-9]{1,}[ ]{0,}-[ ]{0,})(.*$)'

    # Remove the "Read a translation of.." line
    if re.match(pat_translation, line, re.IGNORECASE):
        to_replace = re.match(pat_translation, line, re.IGNORECASE).group(1)
        line = line.replace(to_replace,"")

    line = line.strip()

    # of Vol. II, 
    pat = '^((of Vol.)[ ]{0,}[ivxl][ ]{0,}[:|,|-]{0,})'

    if re.search(pat, line, re.IGNORECASE):
        to_replace = re.match(pat, line, re.IGNORECASE).group(0)
        line = line.replace(to_replace,"")

    line = line.strip()

    pat = '^((summary|summary and analysis|summary & analysis)[ ]{0,}[:|,|-]{0,})'

    if re.search(pat, line, re.IGNORECASE):
        to_replace = re.match(pat, line, re.IGNORECASE).group(0)
        line = line.replace(to_replace,"")

    line = line.strip()

    #Remove any leading punctuations
    line = line.lstrip(punctuation)

    return line.strip()


# Remove prefixes from every summary to further check for the combined/multiple summaries
def remove_prefixes_summary(summary):

    summary = summary.strip().replace("\n"," ")

    pat_chap = '(.*?)Chapter [ivxl|0-9]{1,}[^a-z]'
    pat_scene = '(.*?)Scene [ivxl|0-9]{1,}[^a-z]'   #Do this only if there is no 'Act' preceding the scene TODO
    #Why were we removing the 'Chapter' keyword instead of 'Chapters'?
    
    pat7 = '(.*?)(chapter|scene ((twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)([,-]?)(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|four|five|six|seven|eight|nine|ten)?)).*$'
    
    if re.search(pat_chap, summary, re.IGNORECASE):
        to_replace = re.search(pat_chap, summary, re.IGNORECASE).group(1)

        if len(to_replace.split()) < 150:  # If we are removing too many words, better to not remove!
            summary = summary.replace(to_replace,"")

    summary = summary.strip() #We can remove multiple prefixes

    if re.search(pat_scene, summary, re.IGNORECASE):
        to_replace = re.search(pat_scene, summary, re.IGNORECASE).group(1)
        if len(to_replace.split()) < 150:
            summary = summary.replace(to_replace,"")

    summary = summary.strip()

    if re.search(pat7, summary, re.IGNORECASE):
        to_replace = re.search(pat7, summary, re.IGNORECASE).group(1)
        if len(to_replace.split()) < 150:
            summary = summary.replace(to_replace,"")

    return summary.strip()

#combined summary doesn't have summaries of separate chapters combined together
def check_combined_summary(summary):

    #TODO: Should we add a check for a scene or act range too?

    pat = '^((summary|summary and analysis|summary & analysis)[ ]{0,}[:|,|-]{0,})'

    if re.search(pat, summary, re.IGNORECASE):
        to_replace = re.match(pat, summary, re.IGNORECASE).group(0)
        summary = summary.replace(to_replace,"")

    summary = summary.strip()

    pat2 = '^[ ]{0,}[<PARAGRAPH>]{0,}[ ]{0,}((chapters|chapter) ([ivxl|0-9+]{1,}[,|-|–]){1,}[ivxl|0-9+]{1,})(.*$)'
    combined_summary_flag = 0

    if re.search(pat2, summary, re.IGNORECASE):
        print (re.match(pat2, summary, re.IGNORECASE).groups())
        prefix = re.match(pat2, summary, re.IGNORECASE).group(1)
        summary = summary.replace(prefix,"")
        combined_summary_flag = 1
    
    # If there is no differentiating keyword it might still be a combined summary!

    return combined_summary_flag, summary.strip()

def get_summary_files_chapter_count(x):

    chapter_dir = dirname(x['chapter_path'])
    toc_path = os.path.join(chapterized_books_dir ,chapter_dir, "toc.txt")

    f_toc = open(toc_path, "r")

    f_toc_lines = f_toc.readlines()

    num_toc_lines = len(f_toc_lines)
    if "\n" in f_toc_lines:
        num_toc_lines = num_toc_lines - 1

    summary_dir = dirname(summary_path)

    summary_file_list = os.listdir(summary_dir)
    summary_dir_count = len(summary_file_list)

    if 'overview.txt' in summary_file_list or 'overview.json' in summary_file_list:
        summary_dir_count = summary_dir_count - 1

    return num_toc_lines, summary_dir_count


multiple_summaries = 0
not_flagged = 0
total_aggregates = 0
total_new_summaries = 0
counter = 0

books_set = []

fp = open(matched_books, "r")
fp_lines = fp.readlines()

for line in tqdm(fp_lines):
    line = line.rstrip().strip()
    x = json.loads(line)
    counter += 1
    books_set.append(x['bid'])

    summaries_counted = 0

    prev_book_unique_id = ""

    book_unique_id = x['book_id'].split('.')[0] +  "." + x['source']
    
    if x['is_aggregate']:

        total_aggregates += 1


        if (book_unique_id != prev_book_unique_id) and prev_book_unique_id != "":
            summaries_counted = 0

        summary_path =  os.path.join("../", x['summary_path'])

        if not os.path.exists(summary_path):
            # Summary directory missing
            continue

        num_toc_lines, summary_dir_count = get_summary_files_chapter_count(x)

        # No splitting needed if we have much lesser files that those exist in the TOC 
        # This is mainly for plays where we may have just Act 1, so trying to split Act 1 actually reduces a data point
        if summary_dir_count + 1 > num_toc_lines:  # number of toc lines are usually more only or the same. +1 to handle prologue, intro, epilogue etc
            f_all_errors.write("Too many files already:" + "\t" + summary_path)
            f_all_errors.write("\n")
            continue 

        print ("summary_dir_count: ", summary_dir_count)
        print ("num_toc_lines: ", num_toc_lines)

        # Error can occur if we have multiple occurences of the same book and source..        
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

        summary_content = remove_prefixes_summary(summary_content)

        combined_summary_flag, summary_content = check_combined_summary(summary_content)
        # Combined check may return true and the text can still have multiple summaries. Eg. Chapters 4-5 Chapter 4 ....
        # Treat the above as a prefix removing step for now
        # print ("x: ", x)

        matched_numeric_roman, matched_numbers_nl = check_multiple_summaries(summary_content)

        # If it is not a combined summary of multiple chapters,
        # But has multiple summaries with either roman, numeric or natural language numbers
        # if not combined_summary_flag and (matched_numeric_roman or matched_numbers_nl):
        if (matched_numeric_roman or matched_numbers_nl):

            # section_name_prefix = check_book_num_prefix(x['summary_id'])
            section_name_prefix = ""
            book_id_splits = x['book_id'].split('.')

            if len(book_id_splits) == 3:
                section_name_prefix = book_id_splits[1]

                #TODO: Look into fixing splits obtained from part 1-2.chapters 11-1 type of book ids. Use regex!
                # Ans: In this case we are currently just capturing the chapter number. Usually we are to match just on the basis
                # of that along with the order of the section files
                if '-' in section_name_prefix or section_name_prefix == 'epilogue':
                    section_name_prefix = ""
            
            section_summary_title = x['summary_id']

            #If there are multiple occurences of the section_name_prefix, then don't use any prefix
            if section_name_prefix != "":
                if len(re.findall("act ", section_summary_title)) > 1:
                    section_name_prefix = ""

            # print ("section_name_prefix: ", section_name_prefix)
            separated_summaries = separate_mulitple_summaries(summary_content, matched_numeric_roman, matched_numbers_nl, section_name_prefix, summary_path)

            print ("separated_summaries keys: ", separated_summaries.keys())

            # No need to separate and use the new section name if we only have one single summary found after breaking
            # Also protects against some false positives wrt splitting the sections
            if len(separated_summaries.keys()) == 1:
                #keep it saved normally
                continue
            else:
                multiple_summaries += 1

                # If there is an empty section name, it means we removed some part of the summary as a prefix, which doesn't have an associated
                # section name. In such a case, refrain from the splitting the summary into chapters
                if '' not in separated_summaries.keys() and ' ' not in separated_summaries.keys():
                    summaries_counted += save_separated_summaries(separated_summaries, summary_json, summary_path, section_summary_title)
                    
                    # Remove the old summary path
                    os.remove(summary_path)

                    f_matched_section_splits.write(section_summary_title + " : ")
                    for key, val in separated_summaries.items():
                        f_matched_section_splits.write(key + " | ")
                        total_new_summaries += 1
                    
                    f_matched_section_splits.write(summary_path)
                    f_matched_section_splits.write("\n")

        else:
            # No need to separate, save as is
            not_flagged += 1


print ("multiple_summaries to split: ", multiple_summaries)
print ("total_new_summaries: ", total_new_summaries)
print ("total books: ", len(set(books_set)))
print ("no need to separate: ", not_flagged)
print ("total aggregates: ", total_aggregates)

