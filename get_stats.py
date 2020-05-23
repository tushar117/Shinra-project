from tqdm import tqdm
import json
from collections import defaultdict


categories = {}

raw_dicts = {}

n_levels_categories = []


def get_top_category(ene_id, ene_map):
    target = ene_id
    while(ene_map[target]['parent'] is not None):
        target = ene_map[target]['parent']
    return target

#the first level must be defined
def get_n_level_category(n_level, category_map, raw_data):
    n_level_catgories = set()
    for ene_id in category_map.get(n_level-1):
        for child_id in raw_data[ene_id]['child']:
            n_level_catgories.add(child_id)
    return n_level_catgories

def initialize_category_map(n_level, n_level_categories, category_map):
    category_map[n_level] = {}
    for category_id in n_level_categories:
        category_map[n_level][category_id] = 0

def update_category_count(ene_id, category_map, raw_dict):
    all_levels = len(category_map)
    entity_level = -1
    #find the category levels
    for level in reversed(range(all_levels)):
        if ene_id in category_map[level]:
            entity_level = level
            break
    if entity_level == -1:
        print(ene_id)
        return
    search_level, target = entity_level, ene_id
    while search_level>=0:
        category_map[search_level][target]+=1
        search_level-=1
        target = raw_dict[target]['parent'] 


n_levels_categories.append(set())

with open('ENE_Definition_v8.0.0.json', 'r', encoding='utf-8') as ene_file:
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
        if parent_catgory is None:
            n_levels_categories[0].add(ene_id)

category_map = {}
initialize_category_map(0, n_levels_categories[0], category_map)
print('--'*30)
level_count = 1
while True:
    if len(n_levels_categories[level_count-1]) == 0:
        del category_map[level_count-1]
        n_levels_categories.pop()
        break
    n_levels_categories.append(set())
    n_levels_categories[level_count] = get_n_level_category(level_count, category_map, raw_dicts)
    initialize_category_map(level_count, n_levels_categories[level_count], category_map)

    level_count+=1

print("total count of categories", len(raw_dicts))
for level in category_map:
    print("count of level-%s categories : %d"%(level, len(category_map[level])))
print('--'*30)
doc_counter = 0
actual_category = set()
labels_info = defaultdict(lambda: 0)
with open('hi_ENEW_LIST.json', 'r', encoding='utf-8') as t_file:
    for line in tqdm(t_file.readlines()):
        doc_counter+=1
        line = str(line).strip()
        data = json.loads(line)
        labels_info[len(data['ENEs'])]+=1
        for ene_desc in data['ENEs']:
            ene_id = ene_desc['ENE_id']
            actual_category.add(ene_id)
            update_category_count(str(ene_id).strip(), category_map, raw_dicts)
print("classification of documents on based on label count:")
for label_count, value in sorted(labels_info.items(), key=lambda item: item[0]):
    if label_count == 1:
        print('single-class labelled documents : %d' % value)
        print('multi-class labelled documents : %d' % (doc_counter - value))
    else:
        print('\t%d - class document count : %d' % (label_count, value))
print('%d documents distribution in different categories [%d]'%(doc_counter, len(actual_category)))
print('=='*30)
for top_category, count in sorted(category_map[0].items(), key=lambda item: item[1], reverse=True):
    print("%s (%s) - %d" % (raw_dicts[top_category]['name'], top_category ,category_map[0][top_category]))
    temp = {}
    for child in raw_dicts[top_category]['child']:
        temp[raw_dicts[child]['name']] = { 
            'id': child,
            'count': category_map[1][child],
            }
    for next_category, next_count in sorted(temp.items(), key=lambda item: item[1]['count'], reverse=True):
        # if next_count['count']>0:
        print("\t %s (%s) - %d" % (next_category, next_count['id'], next_count['count'])) 
    print('--'*30)
