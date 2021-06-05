import json
import os
from os.path import basename, dirname, join
import uuid
import argparse
from tqdm import tqdm

splitter = "#$$$#$$$#"

def main(args):

    src = "chapter_summary_aligned_{}_split.jsonl.gathered.stable.bi_encoder_paraphrase".format(args.file)
    dest = "chapter_summary_aligned_{}_split.jsonl.gathered.stable.bi_encoder_paraphrase.aggregated".format(args.file)

    f_dest = open(dest, "w")

    summary_dir = {}
    scores_dir = {}

    fp = open(src, "r")

    count = 0

    for line in tqdm(fp.readlines()):
        x = json.loads(line.strip())
        count += 1

        title = x['title']
        print ("title: ", title)

        key = x['bi-encoder-paraphrase alignment'] + splitter + title
        if key not in summary_dir:
            summary_dir[key] = []
            scores_dir[key] = []

        summary_dir[key].append(x['summary sentence'])
        scores_dir[key].append(x['bi-encoder-paraphrase score'])

    print ("count: ", count)
    print (len(summary_dir))

    for x, y in summary_dir.items():

        new_dict = {}
        new_dict['text'], new_dict['title'] = x.split(splitter)
        new_dict['scores'] = scores_dir[x]
        new_dict['summary'] = y

        json.dump(new_dict, f_dest)
        f_dest.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, required=True, choices=["train", "test", "val"])
    args = parser.parse_args()

    main(args)



