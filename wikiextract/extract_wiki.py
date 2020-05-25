#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gzip
import json
import os
from tqdm import tqdm
import random
from collections import defaultdict, OrderedDict
import regex as re
import string
import unicodedata
import html
import string


puncts = [',', '.', '"', ':', ')', '(', '-', '!', '?', '|', ';', "'", '$', '&', '/', '[', ']', '>', '%', '=', '#', '*', '+', '\\', '•',  '~', '@', '£', 
 '·', '_', '{', '}', '©', '^', '®', '`',  '<', '→', '°', '€', '™', '›',  '♥', '←', '×', '§', '″', '′', 'Â', '█', '½', 'à', '…', 
 '“', '★', '”', '–', '●', 'â', '►', '−', '¢', '²', '¬', '░', '¶', '↑', '±', '¿', '▾', '═', '¦', '║', '―', '¥', '▓', '—', '‹', '─', 
 '▒', '：', '¼', '⊕', '▼', '▪', '†', '■', '’', '▀', '¨', '▄', '♫', '☆', 'é', '¯', '♦', '¤', '▲', 'è', '¸', '¾', 'Ã', '⋅', '‘', '∞', 
 '∙', '）', '↓', '、', '│', '（', '»', '，', '♪', '╩', '╚', '³', '・', '╦', '╣', '╔', '╗', '▬', '❤', 'ï', 'Ø', '¹', '≤', '‡', '√', ]

#writing specially to extract external references titles
def extract_external_ref_name(source_text, skip_chars=["'", ']', '[']):
    # regex_string = "\\n\*\s+\[http[s]?://\S+\s+"
    regex_string = "\[http[s]?://\S+\s+"
    regex = re.compile(regex_string)
    re_iterator = regex.finditer(source_text)
    ref_titles = []
    for match in re_iterator:
        ref_title = []
        index = match.end()
        while index < len(source_text):
            if source_text[index]=="\n":
                break
            if source_text[index]=='<' and index+1 < len(source_text) and source_text[index+1]=='/':
                break
            if source_text[index] in skip_chars:
                index+=1
                continue
            ref_title.append(source_text[index])
            index+=1
        temp = ''.join(ref_title)
        if 'http' in temp:
            regex = re.compile('http[s]?://\S+')
            temp = re.sub(regex, '', temp)
        try:
            unescaped_str = html.unescape(temp)
            ref_titles.append(unescaped_str.strip())
        except Exception:
            #if operation is not successfull use escaped string
            ref_titles.append(temp.strip())
    return ref_titles

def remove_start_ref_tags(text):
    text = text.replace('</ref>', '')
    ref_start_regex = re.compile("<ref(\s*(\S+=[^>\s/]+))*>")
    return re.sub(ref_start_regex, '', text)    

def get_cite_info(cite_text, skip_char=['[', ']', "'"]):
    cite_titles = []
    if cite_text is None:
        return cite_titles
    cite_info = cite_text.split('|')
    for data in cite_info:
        info = data.split('=')
        if len(info)!=2:
            continue
        key, value = info[0].strip(), info[1].strip()
        final_value = []
        for index in range(len(value)):
            if value[index] in skip_char:
                continue
            final_value.append(value[index])
        value = ''.join(final_value)
        if 'http' in value:
            regex = re.compile('http[s]?://\S+')
            value = re.sub(regex, '', value)
        if len(key)==0 or key=='' or value=='' or len(value)==0:
            continue
        cite_titles.extend([val.strip() for val in value.split('\n')])
    return cite_titles

#extacting the <ref> tags and its closing tags
def extract_internal_ref_name(source_text, skip_chars=["'", ']', '[']):
    regex_string = "<ref(\s*(\S+=[^>\s/]+))*>(?>[^<>]+|(?R))*</ref>"
    regex = re.compile(regex_string)
    re_iterator = regex.finditer(source_text)
    ref_titles = []
    #match self close ref tags
    sclose_regex_string = "<ref(\s*(\S+=[^>\s/]+))*/>"
    sclose_regex = re.compile(sclose_regex_string)
    for match in sclose_regex.finditer(source_text):
        ref_titles.extend(get_cite_info(match.group(2)))
    for match in re_iterator:
        ref_title = []
        matched_str = str(source_text[match.start():match.end()]).strip()
        #remove closing ref tags
        matched_str = remove_start_ref_tags(matched_str)
        #iteratively remove ref tags, simple regex operation fails
        
        #clean the citations
        cite_regex = re.compile("\{\{\s*cit")
        if cite_regex.search(matched_str.lower()) is not None:
            ref_titles.extend(get_cite_info(matched_str))
            continue
        for index in range(len(matched_str)):
            if matched_str[index] in skip_chars:
                index+=1
                continue
            ref_title.append(matched_str[index])
            index+=1
        temp = ''.join(ref_title)
        if 'http' in temp:
            regex = re.compile('http[s]?://\S+')
            temp = re.sub(regex, '', temp)
        try:
            unescaped_str = html.unescape(temp)
            ref_titles.extend([val.strip() for val in unescaped_str.split('\n')])
        except Exception:
            #if operation is not successfull use escaped string
            ref_titles.extend([val.strip() for val in temp.split('\n')])
    return ref_titles

def extract_english_concepts(text):
    concept_regex = re.compile('\(([A-Za-z-_]+|\s*)+\)')
    concept_list = []
    for concept in concept_regex.finditer(text):
        temp_con = str(text[concept.start()+1:concept.end()-1]).strip()
        if len(temp_con)!=0 or temp_con!='':
            concept_list.append(temp_con)
    #finally removing these concepts
    concept_regex = re.compile('\(([A-Za-z-_]+|\s*)+\)')
    new_wiki_text = re.sub(concept_regex, '', text)
    return concept_list, new_wiki_text

def _is_punctuation(char):
  """Checks whether `chars` is a punctuation character."""
  cp = ord(char)
  # We treat all non-letter/number ASCII as punctuation.
  # Characters such as "^", "$", and "`" are not in the Unicode
  # Punctuation class but we treat them as punctuation anyways, for
  # consistency.
  if ((cp >= 33 and cp <= 47) or (cp >= 58 and cp <= 64) or
      (cp >= 91 and cp <= 96) or (cp >= 123 and cp <= 126)):
    return True
  cat = unicodedata.category(char)
  if cat.startswith("P"):
    return True
  return False

def run_split_on_punc(text):
    """Splits punctuation on a piece of text except numbers."""
    try:
        text = str(text).strip()
        x = float(text)
        return [text]
    except ValueError:
        pass
    #proceed with normal execution step 
    chars = list(text)
    i = 0
    start_new_word = True
    output = []
    while i < len(chars):
      char = chars[i]
      if _is_punctuation(char):
        output.append([char])
        start_new_word = True
      else:
        if start_new_word:
          output.append([])
        start_new_word = False
        output[-1].append(char)
      i += 1

    return ["".join(x) for x in output]

def get_top_category(ene_id, ene_map):
    target = ene_id
    while(ene_map[target]['parent'] is not None):
        target = ene_map[target]['parent']
    return target

def wikidump(filepath, offset=1, step=1):
    with gzip.open(os.path.abspath(filepath), mode='rt', encoding='utf-8') as dump_file:
        line_count=0
        for line in dump_file:
            line_count+=1
            if offset > line_count or (line_count - offset)%step != 0:
                continue
            try:
                yield json.loads(line.rstrip(',\n'))
            except json.decoder.JSONDecodeError:
                continue

def remove_refs(text, target_strs):
    new_text = text
    for replace_str in target_strs:
        new_text = new_text.replace(replace_str, '')
    return new_text

def clean_text(text, re_expressions):
    new_wiki_text=text
    for re_name, re_string in re_expressions.items():
        regex = re.compile(re_string, re.IGNORECASE)
        new_wiki_text = re.sub(regex, '', new_wiki_text)
    simple_tokens = []
    for token in str(new_wiki_text).split():
        # simple_tokens.append(token)
        simple_tokens.extend(peices.strip() for peices in run_split_on_punc(token) if len(peices.strip())!=0)
    return ' '.join(token for token in simple_tokens if token not in puncts)

def get_ene_hierarchy(config):
    raw_dicts = {}
    with open(config.get('ene_definition_file'), 'r', encoding='utf-8') as ene_file:
        for line in ene_file.readlines():
            line = str(line).strip()
            #workaround for escape characters
            if "\'" in line:
                line = line.replace("\'", "\\'")
            data = json.loads(line)
            ene_id = data.get('ENE_id')
            ene_name = data['name']['en']
            parent_catgory = data['parent_category']
            child_category = data['children_category']
            raw_dicts[ene_id] = {
                'name': ene_name,
                'parent': parent_catgory,
                'child': child_category,
            }
    return raw_dicts

def get_language_data(config):
    ene_categories = defaultdict(lambda: [])
    print('loading language dependent data from file : %s' % (config.get('ene_lang_file')))
    with open(config.get('ene_lang_file'), 'r', encoding='utf-8') as t_file:
        for line in tqdm(t_file.readlines()):
            line = str(line).strip()
            data = json.loads(line)
            page_id = int(str(data.get('pageid')).strip())
            for ene_desc in data['ENEs']:
                ene_id = ene_desc['ENE_id']
                ene_categories[page_id].append(ene_id)
    return ene_categories

def extract_data(config):
    dump_file_path = config.get('dumpfile')
    ene_hierarchy = get_ene_hierarchy(config)
    ene_pages = get_language_data(config)

    page_info_start=True
    ill_formed_data = 0
    temp_data = {}
    is_valid = False
    
    dataset_file = config.get('dataset_file')
    if os.path.isfile(dataset_file):
        try:
            os.remove(dataset_file)
        except Exception as e:
            print('unable to delete : %s. error : %s' % (dataset_file, str(e)))
            with open(dataset_file,'w'): pass
    dataset_file = open(dataset_file, 'a+', encoding='utf-8')

    # global_data = []
    counter=0
    extracted_data_count=0
    for data in tqdm(wikidump(dump_file_path)):
        if page_info_start:
            counter+=1
            temp_data = {}
            page_data = data.get('index', None)
            ill_formed_data+=1
            if page_data is not None and page_data.get('_id', -1) != -1:
                is_valid=True
                temp_data['page_id'] = page_data.get('_id')
                ill_formed_data-=1
                page_info_start = False
        else:
            title = data.get('title', None)
            ill_formed_data+=1
            if title is not None and not page_info_start:
                temp_data['title'] = title
                page_info_start = True
                ill_formed_data-=1
                is_valid=False
                curr_page_id = int(str(temp_data.get('page_id')).strip())
                if curr_page_id in ene_pages:
                    zero_level_classes = set()
                    #ensuring mutiple-labels classes are included
                    for ene_id in ene_pages[curr_page_id]:
                        zero_level_classes.add(get_top_category(ene_id, ene_hierarchy))
                    temp_data['classes'] = list(zero_level_classes)
                    #loading additional fields as configures
                    for field in config.get('fields'):
                        if field == 'text':
                            text = str(data['text'])
                            #will able to remove external and internal references almost completely
                            if config.get('exclude_refs'):
                                ext_refs_names = extract_external_ref_name(str(data['source_text']))
                                int_ref_names = extract_internal_ref_name(str(data['source_text']))
                                text = remove_refs(text, int_ref_names)
                                text = remove_refs(text, ext_refs_names)
                            if config.get('extract_concepts'):
                                temp_data['concepts'], text = extract_english_concepts(text)
                            if config.get('use_regex'):
                                text = clean_text(text, config.get('exclude_regex'))
                            temp_data[field] = text
                        else:
                            temp_data[field] = data.get(field, None)
                    #writing to file 
                    json.dump(temp_data, dataset_file, ensure_ascii=False)
                    dataset_file.write('\n')
                    # global_data.append(temp_data)
                    extracted_data_count+=1
    #finally close the file
    dataset_file.close()
    print("count : %d, invalid counter : %d, valid counter : %d" % (counter, ill_formed_data, counter-ill_formed_data))
    print("global data extracted : %d/%d"%(extracted_data_count, len(ene_pages)))

def update_lang_literals(config):
    hindi_numbers = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९']
    hindi_literals = ["अ", "आ", "इ", "ई", 'उ', "ऊ", "ऋ", "ऌ",  "ए", "ओ", "औ", "अं", "अः", "अँ", "क", "ख", "ग", "घ", "ङ", "च", "छ", "ज"]
    regex_str = "\([%s]{1,2}\)"
    regex_str2 = "\[[%s]{1,2}\]"
    config.update({
        'en_list': "\([0-9]{1,2}\)",
        'en_list_2': "\[[0-9]{1,2}\]",
        'hi_list': regex_str%(''.join(hindi_numbers)),
        'hi_list_2': regex_str2%(''.join(hindi_numbers)),
        'hi_lterals': regex_str%(''.join(hindi_literals)),
        'hi_lterals_2': regex_str2%(''.join(hindi_literals))
    })

def init():
    base_dir = os.path.dirname(os.path.realpath(__file__))
    print("working in directory : ", base_dir)
    global_config = {
        'fields': ['text', 'category'], #fields in addition to titles and page_ids 
        'dumpfile': os.path.join(base_dir, 'hiwiki-20190121-cirrussearch-content.json.gz'),
        'dataset_file': os.path.join(base_dir, 'dataset.json'),
        'ene_definition_file': os.path.join(base_dir, 'ENE_Definition_v8.0.0.json'),
        'ene_lang_file': os.path.join(base_dir, 'hi_ENEW_LIST.json'),
        'use_regex': True,
        # need to explore more
        'exclude_regex': OrderedDict(
            [("html_tags", "<\w+((\s+\w+(\s*=\s*(?:\"?.*?\"?|'.*?'|[\^'\">\s]+))?)+\s*|\s*)>(?>[^<>]+|(?R))*</\w+>"), #recursive expression don't change
            ("url", "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"),
            ("www", "www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"),
            ("json_escape", "\""),
            ("emphassis", "'"),
            ("english_words", "[a-zA-Z]+"),
            ("wiki_links", "\[\[(?>[^\[\]]+|(?R))*\]\]"),
            ("curly_braces", "{{.*?}}"),
            ("styles", "\[\|.*?\|\]"),
            ("tables", '{\|.*?\|}')]),
        'exclude_refs': True,
        'extract_concepts': True
    }
    update_lang_literals(global_config['exclude_regex'])
    extract_data(global_config)

if __name__ == "__main__":
    init()
