"""
The script gathers summary and chapter data into a single jsonl file that we can later break into paragraphs
that align with the sentences from the summaries. The script is run separately for the train/test/val splits.

"""
import argparse
import json
import os
import re
import spacy

from tqdm import tqdm




def fix_leftover_headers(summary_content):
    """
    Function removes leftover prefixes from the summary text, such as: Chapter 1, Chapter V, Analysis, etc.

    :param summary_content: summary text
    """
    # remove 'chapter' text
    summary_content = [sent for sent in summary_content if not re.match(r"^[- ]*Chapter[ ]?([0-9]{1,3}|[XVIL]{1,6})[ :.-]*$", sent)]

    # remove 'analysis' text
    summary_content = [sent for sent in summary_content if not sent == "Analysis"]

    # remove floating punctuations
    summary_content = [sent for sent in summary_content if not sent == "-" or not sent == "."]

    return summary_content


def fix_prefix_punctuation(summary_content):
    """
    Function merges sentences that start with a punctuation character

    :param summary_content: summary text
    """
    # fix sentences starting with puncutation
    ix = 0
    fixed_content = []
    while ix < len(summary_content):
        sentence = summary_content[ix]

        if fixed_content and re.match(r"^[,.?!:-]", sentence):
            fixed_content[-1] = fixed_content[-1] + sentence
            ix += 1
        else:
            fixed_content.append(sentence)
            ix += 1

    return fixed_content


def fix_prefix_quotations(summary_content):
    """
    Merge unclosed quotations with previous sentences

    :param summary_content: summary text
    """
    # merge floating quotations
    ix = 0
    fixed_content = []
    while ix < len(summary_content):
        sentence = summary_content[ix]

        if fixed_content and re.match(r"^[\"\']$", sentence):
            fixed_content[-1] = fixed_content[-1] + sentence
            ix += 1
        elif fixed_content and re.match(r"^[\"\'] [a-z]", sentence):
            fixed_content[-1] = fixed_content[-1] + sentence
            ix += 1
        elif re.match(r"^[\"\'] [A-Z]", sentence):
            sent_split = sentence.split(" ")
            fixed_content[-1] = fixed_content[-1] + sent_split[0].strip()
            fixed_content.append(" ".join(sent_split[1:]).strip())
            ix += 1
        else:
            fixed_content.append(sentence)
            ix += 1

    return fixed_content


def fix_unclosed_quotations(summary_content):
    """
    Merge unclosed quotations with previous sentences

    :param summary_content: summary text
    """
    ix = 0
    fixed_content = []
    while ix < len(summary_content):
        sentence = summary_content[ix]

        if fixed_content and sum([True for ch in sentence if ch == '"']) % 2 == 1 and sum([True for ch in fixed_content[-1] if ch == '"']) % 2 == 1:
            fixed_content[-1] = fixed_content[-1].rstrip() + " " +  sentence.lstrip()
            ix += 1
        else:
            fixed_content.append(sentence)
            ix += 1

    return fixed_content


def fix_noncapitalized_prefix(summary_content):
    """
    Merge noncapitalized texts with previous sentences

    :param summary_content: summary text
    """
    # merge short sentences
    ix = 0
    fixed_content = []
    while ix < len(summary_content):
        sentence = summary_content[ix]

        if fixed_content and re.match("^[ ]?[a-z]", sentence):
            fixed_content[-1] = fixed_content[-1] + " " + sentence
            ix += 1
        else:
            fixed_content.append(sentence)
            ix += 1

    return fixed_content


def fix_short_sentences(summary_content):
    """
    Merge short sentences with previous sentences

    :param summary_content: summary text
    """
    LEN_95_PERCENTILE = 20

    # merge short sentences
    ix = 0
    fixed_content = []
    while ix < len(summary_content):
        sentence = summary_content[ix]

        if len(sentence) < LEN_95_PERCENTILE:
            if fixed_content and sentence[0].islower():
                fixed_content[-1] = fixed_content[-1] + " " + sentence
                ix += 1
            elif ix+1 < len(summary_content):
                fixed_content.append(sentence + " " + summary_content[ix+1])
                ix += 2
            else:
                try:
                    fixed_content[-1] = fixed_content[-1] + " " + sentence
                except:
                    print ("sentence: ", sentence)
                    print ("summary_content: ", summary_content)
                    print ("fixed_content: ", fixed_content)
                ix += 1
        else:
            fixed_content.append(sentence)
            ix += 1

    return fixed_content


def main(args):

    CHAPTER_SUMMARY_MATCHED_FILE = args.matched_file

    # load matched data
    with open(CHAPTER_SUMMARY_MATCHED_FILE) as fd:
        raw_data = [json.loads(line) for line in fd]

    spacy_nlp = spacy.load('en_core_web_lg', disable=["tagger", "ner", "textcat","lemmatizer"])

    # gather data
    processed_data = []
    for example in tqdm(raw_data):
        with open(example["chapter_path"]) as fd:
            if args.join_strings:
                chapter_content = " ".join([line.strip() for line in fd.readlines()])
            elif args.split_paragraphs:
                chapter_content = fd.read().split("\n\n")
                chapter_content = [par.replace("\n", " ").strip() for par in chapter_content]
                chapter_content = [par for par in chapter_content if par]
            else:
                raise RuntimeError("Unknown processing option")

        with open(example["summary_path"]) as fd:
            if args.join_strings:
                summary_content = " ".join([line.strip() for line in json.loads(fd.read())["summary"]])
            elif args.split_paragraphs:
                summary_content = " ".join([line.strip() for line in json.loads(fd.read())["summary"]])
                summary_content = [sent.text.strip() for sent in spacy_nlp(summary_content).sents]
                summary_content = [sent for sent in summary_content if sent]

                summary_content = fix_leftover_headers(summary_content)
                summary_content = fix_prefix_punctuation(summary_content)
                summary_content = fix_prefix_quotations(summary_content)
                summary_content = fix_unclosed_quotations(summary_content)
                summary_content = fix_noncapitalized_prefix(summary_content)
                try:
                    summary_content = fix_short_sentences(summary_content)
                except:
                    print ("Example: ", example)
            else:
                raise RuntimeError("Unknown processing option")

        example["text"] = chapter_content
        example["summary"] = summary_content

        processed_data.append(example)

   # save gathered data
    with open(CHAPTER_SUMMARY_MATCHED_FILE + ".gathered", "w") as fd:
        for example in processed_data:
            fd.write(json.dumps(example) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--join_strings', action='store_true')
    parser.add_argument('--split_paragraphs', action='store_true')
    parser.add_argument('--matched_file', type=str, required=True)
    args = parser.parse_args()

    if args.join_strings and args.split_paragraphs or (not args.join_strings and not args.split_paragraphs):
        raise RuntimeError("Chose only one of the splitting options: `join_strings` or `split_paragraphs`")

    main(args)


