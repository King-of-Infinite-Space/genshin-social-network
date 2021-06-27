#%% 
"""
Reference:
    MediaWiki Action API Code Samples https://www.mediawiki.org/wiki/API:Parsing_wikitext
"""

import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import re
import os
import traceback

char_names = json.load(open('char_names.json','r'))
names_zh = [char['name_zh'] for char in char_names]

#%%
def find_quote_target(self_name, key, lang):
    about = {'en': 'About ', 'zh': '关于'}
    for char in char_names:
        name = char['name_'+lang]
        if name != self_name:
            if (about[lang] + name) in key:
                return name
            if 'alias_'+lang in char:
                if (about[lang] + char['alias_'+lang]) in key:
                    return name

# not used anymore
def get_quotes_bwiki(name):
    S = requests.Session()

    URL = "https://wiki.biligame.com/ys/api.php"

    PARAMS = {
        'action': "parse",
        'page': name+'语音',
        'prop': 'wikitext',
        'format': "json"
    }

    res = S.get(url=URL, params=PARAMS)
    data = res.json()

    entries = {}

    wikitext = data['parse']['wikitext']['*']
    lines = wikitext.replace('\n','').replace('\t','').split('}}{{')
    lines[-1] = lines[-1].replace('}}','')
    for line in lines:
        if line.startswith("角色/语音"):
            l = line.split('|')
            k = l[1].split('=')[-1] #关于xx
            while k.endswith('…') or k.endswith('·') or k.endswith(' '):
                k = k[:-1]
            k = re.sub(r'[0-9]|\.', '', k)
            v = l[-1].replace('<br>','\n')
            v = re.sub('<[^<]+?>', '', v)
            v = v.split('=')[-1]
            v = v.replace("'''",'')
            entries[k] = v
    # print(entries)
    return entries

def get_images_bwiki():
    image_urls = {}

    S = requests.Session()
    URL = "https://wiki.biligame.com/ys/api.php"
    URL_BASE = "https://wiki.biligame.com"
    PARAMS = {
        'action': "parse",
        'page': "角色筛选",
        'format': "json"
    }

    res = S.get(url=URL, params=PARAMS)
    html_doc = res.json()['parse']['text']['*']
    # table = pd.read_html(data, attrs={'id':"CardSelectTr"})
    soup = BeautifulSoup(html_doc,features="lxml")
    table = soup.find(id='CardSelectTr')
    for tr in table.find_all('tr')[1:]: #ignore thead
        a = tr.td.a # from first td
        name = a['title']
        if name in names_zh:
            srcset = a.img['srcset']
            img_url = srcset.split('1.5x, ')[-1].replace(' 2x','')
            image_urls[name] = img_url

            img_path = "./images/%s.png" % name
            if not os.path.exists(img_path):
                r = requests.get(img_url)
                with open(img_path, "wb") as f:
                    f.write(r.content)
                print('Downloaded %s' % img_path)
    return image_urls

def get_quotes_hhw(char, lang='zh'):
    """
        get lines from *char* to other chars
    """
    name = char['name_'+lang]
    if 'url_name' in char:
        url_name = char['url_name']
    else:
        url_name = char['name_en'].replace(' ', '') # eg. hutao  # case insensitive

    if lang == 'en':
        lang_param = 'EN'
    else:
        lang_param = 'CHS'

    URL = "https://genshin.honeyhunterworld.com/db/char/%s/?lang=%s" % (url_name, lang_param)

    lines = []

    S = requests.Session()
    res = S.get(url=URL)
    soup = BeautifulSoup(res.content, features="lxml")

    # check name
    display_name = soup.find('div', class_='custom_title').get_text()
    if (display_name != name):
        raise ValueError('Name mismatch: expect %s, got %s' % (name, display_name))

    quote_start = soup.find('span', id='scroll_quotes')

    ele = quote_start.next_sibling
    while ele.name != 'span':
        table = ele.find('table')
        if table is not None:
            tr1, tr2 = table.contents[:2]
            k = tr1.get_text()

            target = find_quote_target(name, k, lang)
            
            if target is not None:
                while k.endswith('…') or k.endswith('·') or k.endswith(' '):
                    k = k[:-1]
                tr2_str = str(tr2).replace('<br/><color>', '\n') # fischl
                tr2 = BeautifulSoup(tr2_str, features="lxml")
                v = tr2.get_text()
                
                if lang == 'en':
                    if k[:5] == 'About': # should always be true
                        k = name + ' about' + k[5:] # change "About" to lower case
                else:
                    k = name + k
                lines.append({
                    # 'from_'+lang : name,
                    'target_'+lang : target,
                    'title_'+lang : k,
                    'content_'+lang : v,
                })
        ele = ele.next_sibling

    return lines

def find_item_index(lst, key, value):
    for i, item in enumerate(lst):
        if item[key] == value:
            return i

def sort_char_data(char_data, names):
    for i, name in enumerate(names):
        j = find_item_index(char_data, 'name_zh', name)
        if i != j:
            char_data[i], char_data[j] = char_data[j], char_data[i]
    char_data.reverse()
    return char_data

#%%
if __name__ == '__main__':
    char_pending = json.load(open('char_pending.json','r'))
    char_error = []

    if len(char_pending) == 0: # start anew
        char_pending = names_zh.copy()
        char_data = []
    else: # resume
        char_data = json.load(open('char_data.json','r'))

    count_total = len(names_zh)
    count_pending = len(char_pending)

    char_images = get_images_bwiki()
    print('-- Images acquired')
    print('---- Updating %d / %d   ----' % (count_pending, count_total))
    for char in char_names:
        if char['name_zh'] in char_pending:
            try:
                char = char.copy()
                char['img'] = char_images[char['name_zh']]
                lines_zh = get_quotes_hhw(char, 'zh')
                lines_en = get_quotes_hhw(char, 'en')
                if len(lines_zh) != len(lines_en):
                    raise ValueError("ZH and EN lines don't match")
                char['lines'] = [{**lines_zh[i], **lines_en[i]} for i in range(len(lines_zh))]
                char_data.append(char)
                print('---' , char['name_zh'], len(lines_zh))
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                print(char['name_zh'], traceback.format_exc())
                char_error.append(char['name_zh'])

    if len(names_zh) != len(char_data) + len(char_error):
        raise ValueError("Number of entries don't match")
    
    if len(char_error) == 0:
        char_data = sort_char_data(char_data, names_zh)

    with open("char_data.json", "w", encoding='utf8') as f:
        json.dump(char_data, f, ensure_ascii=False, indent=4)

    with open("char_pending.json", "w", encoding='utf8') as f:
        json.dump(char_error, f, ensure_ascii=False, indent=4)
    
    print('---- Updated %d / %d / %d  ----' % (count_pending - len(char_error), count_pending, count_total))
    if len(char_error):
        print('---- Error with following chars ----')
        print(*char_error)
    else:
        print('---- Complete! ----')
# %%
