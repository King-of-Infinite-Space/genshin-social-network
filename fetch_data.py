"""
Reference:
    MediaWiki Action API Code Samples https://www.mediawiki.org/wiki/API:Parsing_wikitext
"""

import requests
import json
import pandas as pd
from bs4 import BeautifulSoup

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
    wikitext = data['parse']['wikitext']['*']
    lines = wikitext.replace('\n','').replace('\t','').split('}}{{')
    lines[-1] = lines[-1].replace('}}','')
    entries = {}

    for line in lines:
        if line.startswith("角色/语音"):
            l = line.split('|')
            k = l[1].split('=')[-1]
            while k.endswith('…') or k.endswith('·') or k.endswith(' '):
                k = k[:-1]
            v = l[-1].split('=')[-1].replace('<br>','')
            entries[k] = v
            
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
        srcset = a.img['srcset']
        char = {
            'name': a['title'],
            'url': URL_BASE + a['href'],
            'lines_url': URL_BASE + '/ys/%s语音' % a['title'],
            'img': srcset.split('1.5x, ')[-1].replace(' 2x','')
        }
        char_list.append(char)

        r = requests.get(char['img'])
        with open("./images/%s.png" % char['name'], "wb") as f:
            f.write(r.content)

    return char_list


if __name__ == '__main__':

    char_list = parse_char_list()

    for char in char_list:
        char['lines'] = parse_char_lines(char['name'])
        print(char['name'], len(char['lines']))

    with open("char_data.json", "w", encoding='utf8') as f:
        json.dump(char_list, f, ensure_ascii=False, indent=4)