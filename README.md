# BOOKSUM: A Collection of Datasets for Long-form Narrative Summarization
Authors: [Wojciech Kryściński](https://twitter.com/iam_wkr), [Nazneen Rajani](https://twitter.com/nazneenrajani), [Divyansh Agarwal](https://twitter.com/jigsaw2212), [Caiming Xiong](https://twitter.com/caimingxiong), [Dragomir Radev](http://www.cs.yale.edu/homes/radev/)

## Introduction
The majority of available text summarization datasets include short-form source documents that lack long-range causal and temporal dependencies, and often contain strong layout and stylistic biases. 
While relevant, such datasets will offer limited challenges for future generations of text summarization systems.
We address these issues by introducing BookSum, a collection of datasets for long-form narrative summarization.
Our dataset covers source documents from the literature domain, such as novels, plays and stories, and includes highly abstractive, human written summaries on three levels of granularity of increasing difficulty: paragraph-, chapter-, and book-level.
The domain and structure of our dataset poses a unique set of challenges for summarization systems, which include: processing very long documents, non-trivial causal and temporal dependencies, and rich discourse structures.
To facilitate future work, we trained and evaluated multiple extractive and abstractive summarization models as baselines for our dataset.

Paper link: https://arxiv.org/abs/2105.08209

<p align="center"><img src="misc/book_sumv4.png"></p>
 
## Table of Contents

1. [Updates](#updates)
2. [Citation](#citation)
3. [Legal Note](#legal-note)
4. [License](#license)
5. [Usage](#usage)
6. [Get Involved](#get-involved)

## Updates
#### 4/15/2021
Initial commit


## Citation
```
@article{kryscinski2021booksum,
      title={BookSum: A Collection of Datasets for Long-form Narrative Summarization}, 
      author={Wojciech Kry{\'s}ci{\'n}ski and Nazneen Rajani and Divyansh Agarwal and Caiming Xiong and Dragomir Radev},
      year={2021},
      eprint={2105.08209},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```

## Legal Note
By downloading or using the resources, including any code or scripts, shared in this code
repository, you hereby agree to the following terms, and your use of the resources is conditioned
on and subject to these terms.
1. You may only use the scripts shared in this code repository for research purposes. You
may not use or allow others to use the scripts for any other purposes and other uses are
expressly prohibited.
2. You will comply with all terms and conditions, and are responsible for obtaining all
rights, related to the services you access and the data you collect.
3. We do not make any representations or warranties whatsoever regarding the sources from
which data is collected. Furthermore, we are not liable for any damage, loss or expense of
any kind arising from or relating to your use of the resources shared in this code
repository or the data collected, regardless of whether such liability is based in tort,
contract or otherwise.

## License
The code is released under the **BSD-3 License** (see `LICENSE.txt` for details).


## Usage

#### 1. Chapterized Project Guteberg Data
The chapterized book text from Gutenberg, for the books we use in our work, has been made available through a public GCP bucket. It can be fetched using:
```
gsutil cp gs://sfr-books-dataset-chapters-research/all_chapterized_books.zip .
```

or downloaded directly [here](https://storage.cloud.google.com/sfr-books-dataset-chapters-research/all_chapterized_books.zip).

#### 2. Data Collection
Data collection scripts for the summary text are organized by the different sources that we use summaries from.
Note: At the time of collecting the data, all links in literature_links.tsv were working for the respective sources. 

For each data source, run `get_works.py` to first fetch the links for each book, and then run `get_summaries.py` to get the summaries from the collected links.

```
cd scripts/data_collection/cliffnotes/
python get_works.py
python get_summaries.py
```

#### 3. Data Cleaning

Data Cleaning is performed through the following steps:

First script for some basic cleaning operations, like removing parentheses, links etc from the summary text
```
cd scripts/data_cleaning_scripts/
python basic_clean.py
```

We use intermediate alignments in  summary_chapter_matched_all_sources.jsonl to identify which summaries are separable, and separates them, creating new summaries (eg. Chapters 1-3 summary separated into 3 different files - Chapter 1 summary, Chapter 2 summary, Chapter 3 summary)
```
python split_aggregate_chaps_all_sources.py
```

Lastly, our final cleaning script using various regexes to separate out analysis/commentary text, removes prefixes, suffixes etc.
```
python clean_summaries.py
```

#### Data Alignments
Generating paragraph alignments from the chapter-level-summary-alignments, is performed individually for the train/test/val splits:

Gather the data from the summaries and book chapters into a single jsonl. The script needs to be run separately for each split as the matched file
```
cd paragraph-level-summary-alignments
python gather_data.py --matched_file /path/to/chapter_summary_aligned_{train/test/val}_split.jsonl --split_paragraphs
```

Generate alignments of the paragraphs with sentences from the summary using the bi-encoder **paraphrase-distilroberta-base-v1**
```
python align_data_bi_encoder_paraphrase.py --data_path /path/to/chapter_summary_aligned_{train/test/val}_split.jsonl.gathered --stable_alignment
```

Aggregate the generated alignments for cases where multiple sentences from a chapter summary are matched to the same paragraph from the book chapter
```
python aggregate_paragraph_alignments_bi_encoder_paraphrase.py --file train/test/val
```

## Troubleshooting
1. The web archive links we collect the summaries from can often be unreliable, taking a long time to load. One way to fix this is to use higher sleep timeouts when one of the links throws an exception, which has been implemented in some of the scripts.
2. Some links that constantly throw errors are aggregated in a file called - 'section_errors.txt'. This is useful to inspect which links are actually unavailable and re-running the data collection scripts for those specific links.
3. Some paths in the provided files might throw errors depending on where the chapterized books have been downloaded. It is recommended to download them in booksum root directory for the scripts to work without requiring any modifications to the paths.


## Get Involved
Please create a GitHub issue if you have any questions, suggestions, requests or bug-reports. 
We welcome PRs!

