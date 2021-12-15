#%% 

import requests
import json
from bs4 import BeautifulSoup
import re
import os
import traceback
from datetime import date

SUB_FOLDER = 'utils/'
DIST_FOLDER = 'page/'

#%%
def find_quote_target(title, self_name, char_dict, lang) -> tuple[str, int]:
    about = {'en': 'About ', 'zh': '关于'}
    for char in char_dict.values():
        name = char['name_'+lang]
        if name != self_name:
            if about[lang] in title and name in title:
                return name, char['id']
            if 'alias_'+lang in char:
                if about[lang] in title and char['alias_'+lang] in title:
                    return name, char['id']
    return None, None

def merge_lines(lines_zh: list[dict], lines_en: list[dict]) -> list[dict]:
    lines = []
    if len(lines_zh) != len(lines_en):
        raise ValueError(f"{len(lines_zh)} ZH and {len(lines_en)} EN lines don't match")
    for i in range(len(lines_zh)):
        if lines_zh[i]['target_id'] == lines_en[i]['target_id']:
            lines.append({**lines_zh[i], **lines_en[i]})
        else:
            # reordering not implemented
            print(lines_zh[i]['title_zh'], lines_en[i]['title_en'])
            raise ValueError("Quote targets don't match")
    return lines

def get_char_api() -> dict[str, dict[str, str]]:
    # api from https://ys.mihoyo.com/main/character/mondstadt
    # channelId 150 mondstadt, 151 liyue, 324 inazuma; 152 seems to be all chars, stumbled across
    # alternatively from english / other language website https://genshin.mihoyo.com/en/character/mondstadt
    # 487, 488, 1108 [489 all]
    URL_zh = "https://ys.mihoyo.com/content/ysCn/getContentList?pageSize=100&pageNum=1&channelId=152"
    URL_en = "https://genshin.mihoyo.com/content/yuanshen/getContentList?pageSize=100&pageNum=1&channelId=489" 
    # without &order=asc newest first

    S = requests.Session()

    res = S.get(url=URL_zh, timeout=20)
    data = res.json()
    res2 = S.get(url=URL_en, timeout=20)
    data2 = res2.json()
    char_count = data['data']['total']
    char_list_zh = data['data']['list']
    char_list_en = data2['data']['list']
    if len(char_list_zh) != len(char_list_en):
        raise ValueError(f"{len(char_list_zh)} ZH and {len(char_list_en)} EN char data entries don't match")
    char_dict = {}
    for i, entry in enumerate(char_list_zh):
        name = entry['title']
        d = {
            'id': char_count - i, # last one = 1
            'name_zh': name,
            'name_en': char_list_en[i]['title'],
        }
        for subentry in entry['ext']:
            if subentry['arrtName'] == '角色-ICON':
                img_url = subentry['value'][0]['url']
                d['img_url'] = img_url
                break
        char_dict[name] = d
    return char_dict

def get_quotes_hhw(char, char_dict, lang='zh') -> list[dict]:
    """
        get lines from *char* to other chars
    """
    name = char['name_'+lang]
    if 'url_name' in char:
        url_name = char['url_name']
    else:
        url_name = char['name_en'].split(' ')[-1] # for japanese names use given name only

    if lang == 'en':
        lang_param = 'EN'
    else:
        lang_param = 'CHS'

    URL = "https://genshin.honeyhunterworld.com/db/char/%s/?lang=%s" % (url_name, lang_param)

    lines = []

    S = requests.Session()
    res = S.get(url=URL)
    soup = BeautifulSoup(res.content, 'html.parser')

    # check name
    # display_name = soup.find('div', class_='custom_title').get_text()
    # if (display_name != name):
    #     raise ValueError('Name mismatch: expect %s, got %s' % (name, display_name))
    display_name = soup.select_one('#scroll_card_item').next_sibling.select_one('tr:first-child').get_text()
    if (display_name != name):
        raise ValueError('Name mismatch: expect %s, got %s' % (name, display_name))

    quote_start = soup.find('span', id='scroll_quotes')

    ele = quote_start.next_sibling
    while ele is not None and ele.name != 'span':
        table = ele.find('table')
        if table is not None:
            tr1, tr2 = table.contents[:2]
            k = tr1.get_text()

            target_name, target_id = find_quote_target(k, name, char_dict, lang)
            
            if target_name is not None:
                while k.endswith('…') or k.endswith('·') or k.endswith(' '):
                    k = k[:-1]
                tr2_str = str(tr2).replace('<br/><color>', '\n') # fischl
                tr2 = BeautifulSoup(tr2_str, 'html.parser')
                v = tr2.get_text()
                
                if lang == 'en':
                    if k[:5] == 'About': # should always be true
                        k = name + ' about' + k[5:] # change "About" to lower case
                else:
                    k = name + k
                lines.append({
                    # 'from_'+lang : name,
                    'target_id': target_id,
                    'target_'+lang : target_name,
                    'title_'+lang : k,
                    'content_'+lang : v,
                })
        ele = ele.next_sibling

    return lines

def update_local_list(char_dict, ver):
    entries = []
    with open(SUB_FOLDER+'char_list.json', 'r') as f:
        lines = f.readlines()
    char_list_local = json.loads(''.join(lines))
    names_local = {char['name_zh'] for char in char_list_local}
    for k in char_dict:
        if k not in names_local:
            d = char_dict[k].copy()
            del d['img_url']
            d['ver'] = ver
            entry = '    ' + json.dumps(d, ensure_ascii=False) + ',\n'
            entries.append(entry)
    if len(entries) > 0:
        print('Writing local list')
        if char_list_local[0]['ver'][:3] != ver[:3]:
            entries.append('\n')
        lines = [lines[0]] + entries + lines[1:]
        with open(SUB_FOLDER+'char_list.json', 'w') as f:
            f.writelines(lines)
    else:
        print('Local list up to date')

def modify_char_dict(char_dict):
    with open(SUB_FOLDER+'char_list.json', 'r') as f:
        char_list_local = json.load(f)
    for d in char_list_local:
        name = d['name_zh']
        if name in char_dict:
            char_dict[name].update(d)

def main():
    # 2021-11-24 Wed v2.3.1
    # 1 subversion per 6 weeks, usually two banners
    dd = (date.today() - date(2021, 11, 24)).days
    v_main = 2
    v_sub = 3 + dd // 42
    while v_sub > 7:  # assuming 2.7 -> 3.0 according to speculation
        v_sub -= 8
        v_main += 1
    v_banner = 2 if abs(dd % 42 - 21) <= 7 else 1
    # first 21 days is 1st banner
    ver = f'{v_main}.{v_sub}.{v_banner}'

    print('Updating for v'+ver)
    with open(SUB_FOLDER+'char_data.json') as f:
        char_data_old = json.load(f)
    with open(SUB_FOLDER+'char_retry.json') as f:
        char_retry = json.load(f)
    count_old = len(char_data_old)
    count_total = count_old
    char_error = []
    commit_msg = ''

    if len(char_retry) == 0:  # start anew
        print('Fetching mhy api')
        # get current char list
        char_dict = get_char_api()  # used for generate char_data
        char_names = list(char_dict.keys())
        char_pending = char_names
        count_total = len(char_dict)
        print(f"\tLast3 {' '.join(char_names[:3])}")

        if count_total <= count_old:
            print(f'\t{count_total} released / {count_old} saved')
            print('Already up to date')
            return commit_msg

        char_names_new = char_names[:count_total-count_old]
        print(f"\tNew char {' '.join(char_names_new)}")
        update_local_list(char_dict, ver) # write new names to char_list.json
   
    else:  # resume from last checkpoint
        char_pending = char_retry
        print(f"Retrying {' '.join(char_retry)}")
        char_dict = {x['name_zh']: x for x in char_data_old}
    
    print('Updating char dict with local list')
    modify_char_dict(char_dict) # add local info (eg. alias) to char_dict
    print(f'Fetching quotes')
    count_pending = len(char_pending)
    print(f'\t{count_pending} pending / {count_total} released')
    i = 1
    for char in char_dict.values():
        if char['name_zh'] in char_pending:
            try:
                lines_zh = get_quotes_hhw(char, char_dict, 'zh')
                lines_en = get_quotes_hhw(char, char_dict, 'en')
                char['lines'] = merge_lines(lines_zh, lines_en)
                print(f"\t{i} / {count_pending}  {char['name_zh']} ({len(lines_zh)})")
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                print(f"\t{i} / {count_pending}  {char['name_zh']} {traceback.format_exc()}")
                char_error.append(char['name_zh'])
            i += 1

    print(f'Updated {count_pending} chars, {len(char_error)} errors')
    # write data files
    char_data = list(char_dict.values())
    char_data.sort(key=lambda x: x['id'])

    with open(SUB_FOLDER+"char_data.json", "w", encoding='utf8') as f:
        json.dump(char_data, f, ensure_ascii=False, indent=4)

    with open(DIST_FOLDER+"char_data_min.json", "w", encoding='utf8') as f:
        json.dump(char_data, f, ensure_ascii=False, separators=(',', ':'))

    with open(SUB_FOLDER+"char_retry.json", "w", encoding='utf8') as f:
        json.dump(char_error, f, ensure_ascii=False, indent=4)

    if len(char_error) == 0:
        commit_msg = f"v{ver} {' '.join([char['name_zh'] for char in char_data if char['ver']==ver])}"
    else:
        commit_msg = f"v{ver} update incomplete"
    print('Done —— '+commit_msg)
    return commit_msg

#%%
if __name__ == '__main__':
    commit_msg = main()
    with open('msg.log', 'w') as f:
        f.write(commit_msg)
    try:
        k1, v1 = os.getenv('PAYLOAD1').split('=')
        payload = {k1: v1, 'text': commit_msg}
        r = requests.get(os.getenv('MSG_URL'), params=payload)
    except:
        print(traceback.format_exc())
        