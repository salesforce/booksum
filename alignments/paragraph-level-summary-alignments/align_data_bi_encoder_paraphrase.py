"""
Script used to generate bi-encoder paraphrase alignment of the paragraphs with sentences from the summary.
It is recommended to run this script on a GPU machine.
"""

#!/usr/bin/env python
# coding: utf-8
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter("ignore", ResourceWarning)

import argparse
import io
import json
import os
from os.path import basename
import re
import six
import sys
import pprint
import spacy
import rouge
import numpy as np
import rouge.rouge_score as rouge_score
import warnings
from collections import Counter
from tqdm import tqdm
from matplotlib import pyplot as plt
from nltk.stem.snowball import SnowballStemmer
from matching.games import HospitalResident
from nltk.translate.meteor_score import meteor_score
from bert_score import BERTScorer
from transformers import AutoTokenizer
from nltk.tokenize import word_tokenize, sent_tokenize

from sentence_transformers import SentenceTransformer, util

# change recursion limit
sys.setrecursionlimit(5000)

# https://huggingface.co/sentence-transformers/paraphrase-distilroberta-base-v1
model_bi_encoder_paraphrase = SentenceTransformer('paraphrase-distilroberta-base-v1')


model_bi_encoder_paraphrase.max_seq_length = 512

pp = pprint.PrettyPrinter(indent=2)

error_logs_file = open("error_logs.jsonl","a")

warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


# Breaks down chapter text into smaller length paragraphs that we can align ground truth summary sentences to
def merge_text_paragraphs(paragraphs, min_sent=3, max_sent=12):
    spacy_nlp = spacy.load("en_core_web_lg")

    new_paragraphs = []
    temp_paragraphs = []
    temp_paragraphs_cnt = 0

    for paragraph in paragraphs:
        paragraph_len = len(list(spacy_nlp(paragraph).sents))

        if paragraph_len > min_sent:
            if temp_paragraphs:

                assert len(temp_paragraphs) <=  max_sent
                joined = " ".join(temp_paragraphs)
                
                new_paragraphs.append(joined)
                temp_paragraphs = []
                temp_paragraphs_cnt = 0
            new_paragraphs.append(paragraph)
        else:
            if temp_paragraphs_cnt + paragraph_len > max_sent:

                assert len(temp_paragraphs) <=  max_sent
                joined = " ".join(temp_paragraphs)
                
                new_paragraphs.append(joined)
                temp_paragraphs = [paragraph]
                temp_paragraphs_cnt = paragraph_len
            else:
                temp_paragraphs.append(paragraph)
                temp_paragraphs_cnt += paragraph_len

    if temp_paragraphs:
        assert len(temp_paragraphs) <=  max_sent

        joined = " ".join(temp_paragraphs)
        new_list_len = list(spacy_nlp(joined).sents)
        new_paragraphs.append(joined)
        temp_paragraphs = []
        temp_paragraphs_cnt = 0

    return new_paragraphs


def align_data_greedy_matching(similarity_matrix):
    summ_cnt, text_cnt = similarity_matrix.shape

    # extract alignments
    alignments = np.argmax(similarity_matrix, axis=1).tolist()

    # create alignment matrix
    return alignments


def align_data_stable_matching(similarity_matrix, text_capacity):
    # text paragraphs -> hospital
    # summary paragraphs -> resident
    summ_cnt, text_cnt = similarity_matrix.shape

    summ_ids = ["%dS" % ix for ix in range(summ_cnt)]
    text_ids = ["%dT" % ix for ix in range(text_cnt)]
    ids_summ = {key: ix for ix, key in enumerate(summ_ids)}
    ids_text = {key: ix for ix, key in enumerate(text_ids)}

    # organize summary sentences preferences
    summ_prefs = {key: [] for _, key in enumerate(summ_ids)}
    for summ_ix, summ_id in enumerate(summ_ids):
        alignment = np.argsort(similarity_matrix[summ_ix, :])[::-1]
        summ_prefs[summ_id] = [text_ids[ix] for ix in alignment]

    # organize text paragraph preferences
    text_prefs = {key: [] for _, key in enumerate(text_ids)}
    for text_ix, text_id in enumerate(text_ids):
        alignment = np.argsort(similarity_matrix[:, text_ix])[::-1]
        text_prefs[text_id] = [summ_ids[ix] for ix in alignment]

    # update matching capacity
    capacity = {key: text_capacity for key in text_ids}

    # run matching algorithm
    game = HospitalResident.create_from_dictionaries(summ_prefs, text_prefs, capacity)
    matching = game.solve(optimal="hospital")

    # extract alignments
    alignments = [-1] * summ_cnt
    for t_key, s_keys in matching.items():
        for s_key in s_keys:
            alignments[ids_summ[s_key.name]] = ids_text[t_key.name]

    return alignments


#Matrix of bi-encoder scores b/w all pairwise paras and summaries #summaries X #paras
#Using paraphrase-distilroberta-base-v1 bi encoder alignments
#https://www.sbert.net/docs/usage/semantic_textual_similarity.html
def compute_similarities_bi_encoder(paragraphs, summaries):

    paragraphs_embeddings_paraphrase = model_bi_encoder_paraphrase.encode(paragraphs, convert_to_tensor=True)
    summaries_embeddings_paraphrase = model_bi_encoder_paraphrase.encode(summaries, convert_to_tensor=True)

    similarity_matrix_bi_encoder_paraphrase = util.pytorch_cos_sim(summaries_embeddings_paraphrase, paragraphs_embeddings_paraphrase).numpy()

    return similarity_matrix_bi_encoder_paraphrase


def gather_data(alignments_bi_encoder_paraphrase, paragraphs, summaries, similarity_matrix_bi_encoder_paraphrase, title):
    examples = []

    all_alignments = alignments_bi_encoder_paraphrase

    for s_ix, t_ix_bienc_p in enumerate(all_alignments):
        # print (s_ix, t_ix)
        example = {
            "summary sentence": summaries[s_ix],
            "bi-encoder-paraphrase alignment": paragraphs[t_ix_bienc_p],
            "bi-encoder-paraphrase score":  str(similarity_matrix_bi_encoder_paraphrase[s_ix][t_ix_bienc_p]),
            "title": title + "-" + str(s_ix)
        }
        
        examples.append(example)

    return examples


def visualize_alignments(similarity_matrix, alignments, title, output_dir=None):
    summ_cnt = len(alignments)

    alignment_matrix = np.zeros_like(similarity_matrix)
    for ix in range(summ_cnt):
        alignment_matrix[ix][alignments[ix]] = 1

    plt.figure(figsize=(20,10))

    fig, (ax1, ax2) = plt.subplots(2, sharey=True, figsize=(20, 10))
    fig.suptitle(title)
    ax1.imshow(similarity_matrix, cmap='gray', interpolation='nearest')
    ax1.set_title("Similarity matrix")
    ax2.imshow(alignment_matrix, cmap='gray', interpolation='nearest')
    ax2.set_title("Alignment matrix")

    if output_dir:
        plt.savefig(os.path.join(output_dir, title + ".png"), dpi=100)

    plt.close()


def main(args):
    # load data
    with open(args.data_path) as fd:
        data = [json.loads(line) for line in fd]

    # align each example

    for ix, example in tqdm(enumerate(data)):
        if example['summary'] == []:
            continue

        chap_path  = example["chapter_path"]
        print ("chap path: ", chap_path)

        # merge text paragraphs
        summaries = [sent for sent in example["summary"] if sent]
        paragraphs_before_merge = [sent for sent in example["text"] if sent]

        #Convert long book chapters into paragraphs
        paragraphs = merge_text_paragraphs(paragraphs_before_merge, args.merging_min_sents, args.merging_max_sents)

        # compute similarities
        #Initially we tried both roberta and paraphrase bi encoder
        similarity_matrix_bi_encoder_paraphrase = compute_similarities_bi_encoder(paragraphs, summaries)

        # For all our experimental results, we perform stable alignment        
        if args.stable_alignment:
            stable_alignments_bi_encoder_paraphrase = align_data_stable_matching(similarity_matrix_bi_encoder_paraphrase, args.alignment_capacity)
            # print ("stable_alignments_bi_encoder_paraphrase: ", stable_alignments_bi_encoder_paraphrase)

            # Add a title to uniquely distinguish paragraphs. Has source, book and chapter info
            title = "%s.%s-stable" % (example["book_id"].lower().replace(" ", "_"), example["source"].lower())
            stable_examples = gather_data(stable_alignments_bi_encoder_paraphrase, paragraphs, summaries, similarity_matrix_bi_encoder_paraphrase, title)

            # visualize_alignments(similarity_matrix_bi_encoder_paraphrase, stable_alignments_bi_encoder_paraphrase, title, args.output_dir)

            with open(basename(args.data_path) + ".stable.bi_encoder_paraphrase", "w") as fd:
                for stable_example in stable_examples:
                    fd.write(json.dumps(stable_example) + "\n")


        if args.greedy_alignment:
            title = "%s.%s-greedy" % (example["book_id"].lower().replace(" ", "_"), example["source"].lower())

            greedy_alignments = align_data_greedy_matching(similarity_matrix_bi_encoder_paraphrase)
            greedy_examples = gather_data(greedy_alignments, paragraphs, summaries, similarity_matrix_bi_encoder_paraphrase, title)

            with open(basename(args.data_path) + ".greedy", "w") as fd:
                for greedy_example in greedy_examples:
                    fd.write(json.dumps(greedy_example) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, help='path to input data file')
    parser.add_argument('--similarity_fn', type=str, default='weighted', choices=['weighted', 'original'], help='function used for similarity evaluation')
    parser.add_argument('--stable_alignment', action='store_true', help='function used for aligning')
    parser.add_argument('--greedy_alignment', action='store_true', help='function used for aligning')
    parser.add_argument('--merging_min_sents', type=int, default=4, help='')
    parser.add_argument('--merging_max_sents', type=int, default=12, help='')
    parser.add_argument('--alignment_capacity', type=int, default=10, help='')
    parser.add_argument('--save_figs', action='store_true', help='function used for aligning')
    args = parser.parse_args()

    if not (args.stable_alignment or args.greedy_alignment):
        raise RuntimeError("At least one alignment option must be chosen: `stable_alignment`, `greedy_alignment`.")

    if args.save_figs:
        args.output_dir = os.path.join(os.path.dirname(args.data_path), "saved_figs")
        os.makedirs(args.output_dir, exist_ok=True)
    else:
        args.output_dir = None


    main(args)
