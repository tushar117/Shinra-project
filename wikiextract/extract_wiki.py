import gzip
import json
import os
from tqdm import tqdm
import random
from collections import defaultdict
import regex as re


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

def clean_text(text, re_expressions):
    new_wiki_text=text
    for re_name, re_string in re_expressions.items():
        regex = re.compile(re_string, re.IGNORECASE)
        new_wiki_text = re.sub(regex, '', new_wiki_text)
    return new_wiki_text


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
        if extracted_data_count == 10:
            break
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
                        if field == 'text' and config.get('use_regex'):
                            temp_data[field] = clean_text(data['text'], config.get('exclude_regex'))
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

def init():
    base_dir = os.path.dirname(os.path.realpath(__file__))
    print("working in directory : ", base_dir)
    global_config = {
        'fields': ['text', 'category'], #fields in addition to titles and page_ids 
        'dumpfile': '/home/tushar/research/projects/shinra/hi/hiwiki-20190121-cirrussearch-content.json.gz',
        'dataset_file': os.path.join(base_dir, 'dataset.json'),
        'ene_definition_file': os.path.join(base_dir, 'ENE_Definition_v8.0.0.json'),
        'ene_lang_file': os.path.join(base_dir, 'hi_ENEW_LIST.json'),
        'use_regex': True,
        # need to explore more
        'exclude_regex': {
            "html_tags": "<\w+[\s|\w]*>(?>[^<>]+|(?R))*</\w+>", #recursive expression don't change
            "url": "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "www": "www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "english_words": "[a-zA-Z]+",
            #"wiki_links": "\[\[(?>[^\[\]]+|(?R))*\]\]",
            #"curly_braces": "{{(?>[^{}]+|(?R))*}}",
            #"styles" : "\[\|.*?\|\]",
            #"tables" : '{\|.*?\|}',
            #"braces" : '{.*?}'
        },
    }
    extract_data(global_config)

if __name__ == "__main__":
    init()