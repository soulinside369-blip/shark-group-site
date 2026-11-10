import re,base64,io,os
from PIL import Image

# Repo layout: this script + template.html + img/ wood/ tile/ live in src/.
# Output (index.html + m/*.webp and shark-group.html) is written to the repo ROOT (one level up),
# so GitHub Pages serves them from the root.
SRC=os.path.dirname(os.path.abspath(__file__))+'/'
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'

t=open(SRC+'template.html',encoding='utf-8').read()
os.makedirs(ROOT+'m',exist_ok=True)
cache={}
def webp(kind,name):
    if kind=='P':
        src=SRC+f'img/{name}.jpg'; mw=2200 if name=='p124' else 1800; q=86
    elif kind=='T':
        src=SRC+f'wood/{name}.jpg'; mw=2000; q=90
    else:
        src=SRC+f'tile/{name}.jpg'; mw=1800; q=88
    im=Image.open(src).convert('RGB'); im.thumbnail((mw,mw)); b=io.BytesIO(); im.save(b,'WEBP',quality=q,method=6); return b.getvalue()
def get(k,n):
    if (k,n) not in cache: cache[(k,n)]=webp(k,n)
    return cache[(k,n)]

# split template into head (up to and incl </style>) and body (rest)
i=t.index('</style>')+len('</style>')
head_frag=t[:i]; body_frag=t[i:]

HEAD='''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
'''
def wrap(head_resolved, body_resolved):
    return HEAD+head_resolved+'\n</head>\n<body>\n'+body_resolved+'\n</body>\n</html>\n'

# split build: external webp files at repo root (m/)
def split_sub(m):
    open(ROOT+f'm/{m.group(2)}.webp','wb').write(get(m.group(1),m.group(2)))
    return f'm/{m.group(2)}.webp'
hs=re.sub(r'\{\{([PTX]):(\w+)\}\}',split_sub,head_frag)
bs=re.sub(r'\{\{([PTX]):(\w+)\}\}',split_sub,body_frag)
open(ROOT+'index.html','w',encoding='utf-8').write(wrap(hs,bs))

# single-file version (everything embedded) at repo root
def emb(m): return 'data:image/webp;base64,'+base64.b64encode(get(m.group(1),m.group(2))).decode()
h1=re.sub(r'\{\{([PTX]):(\w+)\}\}',emb,head_frag)
b1=re.sub(r'\{\{([PTX]):(\w+)\}\}',emb,body_frag)
open(ROOT+'shark-group.html','w',encoding='utf-8').write(wrap(h1,b1))
tot=sum(len(v) for v in cache.values())
print(len(cache),'imgs',round(tot/1e6,2),'MB; single',round(len(one:=open(ROOT+"shark-group.html").read())/1e6,2),'MB')
