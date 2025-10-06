import regex as re
import unicodedata
from collections import defaultdict
from nltk.util import ngrams
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
from  pprint import pprint
from collections import Counter
import matplotlib.pyplot as plt
import genanki
from deep_translator import GoogleTranslator
import stanza
import os
import deepl
import hashlib, html
from typing import Dict, List, Tuple
import time, unicodedata as ud
from dotenv import load_dotenv
load_dotenv()

nlp = stanza.Pipeline("sv", processors="tokenize,pos,lemma")
nltk.download("stopwords")
stopwords = stopwords.words("swedish")

# 1) Known ambiguous terms → add a hint (and optional forced gloss)
SWEDISH_DELETE_WORDS = [
    # greetings / interjections
    "hej","hejsan","hallå","tjena","tjenare","tjenixen","tja","goddag","godmorgon","godkväll","mors",
    "aha","oj","åh","hmm","mm","mmm","eh","öh","öhm","äh","asså","ba",
    # yes / no / acknowledgements
    "ja","japp","jo","visst","absolut","okej","ok","okey","nej","icke",
    # fillers / discourse markers
    "liksom","typ","alltså","ju","väl","likaså","likväl","så","då","bara","redan","också","dessutom","kanske","nog",
    # pronouns / determiners
    "jag","du","han","hon","den","det","vi","ni","de","mig","dig","honom","henne","oss","er","dem","man",
    "min","mitt","mina","din","ditt","dina","sin","sitt","sina","vår","vårt","våra","er","ert","era",
    "denna","detta","dessa","någon","något","några","ingen","inget","inga","vilken","vilket","vilka","som",
    # common verbs/aux/modals
    "är","var","vara","blir","blev","bli","ha","har","hade","gör","gjorde","göra",
    "kan","kunde","ska","skall","skulle","vill","ville","måste","bör","brukar","får","fick",
    # adverbs / particles
    "inte","aldrig","alltid","ofta","ibland","sällan","här","där","hit","dit","hem","borta","nu","sen","snart","igen","än",
    "mycket","lite","mer","mest","mindre","minst","kvar","både","antingen","heller","också",
    # prepositions
    "i","på","till","från","för","med","utan","över","under","mellan","genom","mot","bland","hos",
    "före","efter","kring","runt","enligt","trots","vid","omkring","om","åt","av","per","cirka","ca",
    # conjunctions / subjunctions
    "och","men","eller","samt","utan","att","för att","eftersom","därför","medan","när","innan","efter att","om",
    "fast","så att","såväl","både","dock","ty","varför",

    'ska', 'nej', 'hej','bra', 'ja','vill','lite', 'jaha', 'wow'
]

names = ['eddie', 'martin', 'william', 'lisa','eddies', 'patrik', 'bianca', "katja"]
to_delete = stopwords + SWEDISH_DELETE_WORDS + names


# SRT timestamp line: 00:00:12,345 --> 00:00:14,567
_SRT_TIME_RE = re.compile(
    r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}$'
)

_SENT_END_RE = re.compile(
    r"""
    (?<!\b(?:dr|prof|mr|mrs|ms|nr|itp|np|tj|kap|art|al)\.)   # variable-width lookbehind OK here
    (?<=\.|!|\?|…)
    ["')\]]*
    \s+
    """,
    re.IGNORECASE | re.VERBOSE
)

def read_file(file_name: str):
    with open(file_name, 'r', encoding = 'UTF-8') as f:
        file = f.read()
    return file

def clean_line(line, for_word):
    line = line.replace('-','')
    line = line.replace('...','')
    line = line.strip()

    if line.endswith(','):
        line = line [:-1]
        
    if for_word:
        line = re.sub(r'\p{P}+', ' ', line)
        line = line.lower()

    line = line.replace('  ', ' ')
    line = line.strip()
    return line


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]

def clean_data(file: str, for_word: bool = False) -> list[str]:
    # 1) Strip SRT artifacts, collapse to a single text
    lines = []
    for raw in file.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.isdigit():               # SRT index lines
            continue
        if _SRT_TIME_RE.match(line):     # SRT time range lines
            continue
        lines.append(line)
    text = " ".join(lines)

    # 2) Split by sentences (not lines)
    sentences = _split_sentences(text)

    # 3) Clean and filter
    filtered = []
    for s in sentences:
        s = clean_line(s, for_word)      # your cleaner
        s = " ".join(s.split())
        if len(s) > 1:
            filtered.append(s)
    return filtered

def convert_to_words(lines:list) -> list:
    full_list = []
    for line in lines:
        for word in line.split(' '):
            if word.isdigit():
                continue
            if isinstance(word, str):
                full_list.append(word)
    
    return full_list

def generate_ngram(words_tokenized, n, min_count):
    generated_ngrams = ngrams(words_tokenized, n)
    counter_grams = Counter(list(generated_ngrams))
    counter_dict = dict(counter_grams)
    return {k: v for k,v in counter_dict.items() if v >= min_count}

def generate_multiple_ngrams(words_tokenized, min_counts):
    grams = {}
    gram_counts = {}
    for i in range(3,10):
        if generate_ngram(words_tokenized, i, min_counts):
            grams[i] = generate_ngram(words_tokenized, i, min_counts)
            gram_counts[i] = len(grams[i])
        else:
            break
    return grams, gram_counts

def get_cleaned_sentences(cleaned_file):
    sentence_clean = {}
    for line in cleaned_file:
        sentence_clean[clean_line(line, for_word = True)] = line

    return sentence_clean

def match_grams_with_sentences(grams, sentence_clean):
    di = {}
    # sentence_clean: {clean -> original}
    for n, content in grams.items():
        for gram, _ in content.items():
            key = ' '.join(gram)
            pat = re.compile(rf"\b{re.escape(key)}\b", flags=re.IGNORECASE)
            di[gram] = [cent_raw for sent, cent_raw in sentence_clean.items() if pat.search(sent)]
    return di

def get_lemma(word):
    doc = nlp(word)
    out = []
    for sent in doc.sentences:
        for w in sent.words:
            if w.upos == "NOUN":
                feats = w.feats or ""          # e.g. "Definite=Ind|Gender=Neut|Number=Sing"
                art = "en" if "Gender=Com" in feats else ("ett" if "Gender=Neut" in feats else None)
                return [art, w.upos , w.lemma]
            else:
                return [None, w.upos, w.lemma]
            
def lemmatize_words(words):
    final_words = defaultdict(dict)
    for w in words:
        art, pos, lem = get_lemma(w)
        info = final_words.setdefault(lem, {"Artikel": art, "POS": pos, "Forms": set()})
        info["Forms"].add(w)
    return final_words

def get_lemma_count(words, lemmatized):
    surface_to_row = {}
    for lem, info in lemmatized.items():
        for form in info["Forms"]:
            surface_to_row[form] = (info["Artikel"], info["POS"], lem)

    counts = defaultdict(Counter)
    for w in words:
        row = surface_to_row.get(w)
        if not row: 
            continue
        _, upos, lemma = row
        counts[upos][lemma] += 1
    return {pos: dict(cnt) for pos, cnt in counts.items()}



def get_sentence_example(lematized, sentences):
    res = defaultdict(list)
    for word, lemma_data in lematized.items():
        for word_form in lemma_data['Forms']:
            res[word].append(word_form) 

    for lemma, words in res.items():
        lemma_map = {}  
        for word in set(words):
            pattern = re.compile(rf"\b{re.escape(word)}\b", flags=re.IGNORECASE)
            hits = [target for sent, target in sentences.items() if pattern.search(sent)]
            if hits:
                lemma_map[word] = hits
        if lemma_map:
            lematized[lemma]['examples'] = lemma_map
    return lematized


def normalize_text(lines: list[str]) -> str:
    cleaned_file_words = clean_data(lines, for_word= True)
    cleaned_words = convert_to_words(cleaned_file_words)
    # Retained punctuation
    cleaned_file = clean_data(lines, for_word= False)
    sentence_clean = get_cleaned_sentences(cleaned_file)
    return sentence_clean, cleaned_words

def get_grams(sentence_clean, cleaned_file_words) -> dict[str,list]:
    grams, _ = generate_multiple_ngrams(cleaned_file_words, 3)
    matched_dict = match_grams_with_sentences(grams, sentence_clean)
    return matched_dict


def compute_file_hash(file_content: str) -> str:
    """Compute SHA-256 hash of file content for caching"""
    return hashlib.sha256(file_content.encode('utf-8')).hexdigest()

def get_cached_data(file_hash:str) -> dict:
    """ Return data from cachce"""
    return False

def run_stage1_data_generation(file_content:str):
    sentence_clean, cleaned_file_words = normalize_text(file_content)
    
    file_hash = compute_file_hash("".join(list(sentence_clean.keys())))

    cached_data = get_cached_data(file_hash)

    if cached_data:
        print("I WILL USE CACHED DATA FROM SUPABASE AND OMMIT PROCESSING")
        return
    print("RUNNING ANALYSIS")
    
    grams = get_grams(sentence_clean, cleaned_file_words)
    words_clean = [w for w in cleaned_file_words if (w not in to_delete)]
    lematized = lemmatize_words(words_clean)
    lemma_count = get_lemma_count(words_clean, lematized)
    final_with_sentences = get_sentence_example(lematized, sentence_clean)

    stage1_data = {
        'episode_data_processed':final_with_sentences,
        'lemma_count': lemma_count,
        'grams': grams,
        'file_hash': file_hash
    }
    
    return stage1_data


if __name__ == '__main__':
    from pprint import pformat  
    import pickle
    results = run_stage1_data_generation(read_file('ep1.srt'))
    # binary snapshot (full fidelity)
    with open('data.pkl', 'wb') as f:
        pickle.dump(results, f)

    # human-readable peek (no JSON needed)
    with open('data_preview.txt', 'w', encoding='utf-8') as f:
        f.write(pformat(results, width=120, compact=True))

    print("Saved data.pkl and data_preview.txt")
    
    #quotas = {"VERB": 0.35, "NOUN": 0.40, "ADJ": 0.15, "ADV": 0.10}
    #study_list, picked_by_pos = select_top_quota(lemma_count, target_total=260, quotas=quotas)
    #cov = coverage(lemma_count)
    #get_coverage_info(lemma_count)
    #print(f"Estimated token coverage: {cov:.1%}")