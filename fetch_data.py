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
import sys

char_names = json.load(open('char_names.json','r'))

#%%
def get_quote_target(self_name, key, lang):
    about = {'en': 'About ', 'zh': '关于'}
    for char in char_names:
        name = char['name_'+lang]
        if name != self_name:
            if (about[lang] + name) in key:
                return name
            try:
                alt_name = char['alt_name_'+lang]
                if (about[lang] + alt_name) in key:
                    return name
            except KeyError:
                pass

# not used anymore
def parse_char_lines(name):
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
    try:
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
    except:
        print(name, sys.exc_info()[0])
    # print(entries)
    return entries

def parse_char_list():
    char_list = []
    names_zh = [char['name_zh'] for char in char_names]

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
            try:
                srcset = a.img['srcset']
                img_url = srcset.split('1.5x, ')[-1].replace(' 2x','')
            except:
                print(name, 'cannot find img url')
                img_url = ''

            char = {
                'name_zh': name,
                # 'url': URL_BASE + a['href'],
                # 'lines_url': URL_BASE + '/ys/%s语音' % name,
                'img': img_url
            }
            char_list.append(char)

            if img_url != '':
                img_path = "./images/%s.png" % char['name_zh']
                if not os.path.exists(img_path):
                    r = requests.get(char['img'])
                    with open(img_path, "wb") as f:
                        f.write(r.content)
                    print('Downloaded %s' % img_path)

    return char_list

def parse_quotes_hhw(char, lang='zh'):
    """
        get lines from *char* to other chars
    """
    name = char['name_'+lang]

    url_name = char['name_en'].replace(' ', '') # hu tao
    if url_name == 'Yanfei':
        url_name = 'feiyan'

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

            target = get_quote_target(name, k, lang)
            
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

    # except:
    #     print(name, sys.exc_info()[0], sys.exc_info()[1])
    
    return lines
#%%
if __name__ == '__main__':

    char_list = parse_char_list()
    
    for char in char_names:
        lines_zh = parse_quotes_hhw(char, 'zh')
        lines_en = parse_quotes_hhw(char, 'en')
        info = (char['name_zh'], len(lines_zh), len(lines_en))
        print(*info)
        assert(info[1] == info[2])

        char['lines'] = [{**lines_zh[i], **lines_en[i]} for i in range(len(lines_zh))]

    with open("char_data.json", "w", encoding='utf8') as f:
        json.dump(char_list, f, ensure_ascii=False, indent=4)

    print('----Complete----')
# %%
