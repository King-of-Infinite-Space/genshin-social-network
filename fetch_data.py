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

#%%

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
        try:
            srcset = a.img['srcset']
            img_url = srcset.split('1.5x, ')[-1].replace(' 2x','')
        except:
            print(name, 'cannot find img url')
            img_url = ''

        char = {
            'name': name,
            'url': URL_BASE + a['href'],
            'lines_url': URL_BASE + '/ys/%s语音' % name,
            'img': img_url
        }
        char_list.append(char)

        if img_url != '':
            img_path = "./images/%s.png" % char['name']
            r = requests.get(char['img'])
            if not os.path.exists(img_path):
                with open(img_path, "wb") as f:
                    f.write(r.content)

    return char_list

#%%
if __name__ == '__main__':

    char_list = parse_char_list()

    for char in char_list:
        char['lines'] = parse_char_lines(char['name'])
        print(char['name'], len(char['lines']))

    with open("char_data.json", "w", encoding='utf8') as f:
        json.dump(char_list, f, ensure_ascii=False, indent=4)

    print('Complete')