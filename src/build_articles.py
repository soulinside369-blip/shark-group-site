# -*- coding: utf-8 -*-
"""Страницы статей sharkgroup.pro/stati/ из src/articles.py.

    python build_articles.py   ->  stati/index.html, stati/<slug>.html, m/<фото>.webp, sitemap.xml

Подписи к фото берутся из каталога в template.html (те же, что на сайте), чтобы картинка
всегда соответствовала тексту. Фото, которого нет в каталоге, получает подпись из CAP ниже.
"""
import os, re, json, html, hashlib, io
from PIL import Image
from articles import ARTICLES

SRC = os.path.dirname(os.path.abspath(__file__)) + '/'
ROOT = os.path.dirname(SRC.rstrip('/')) + '/'
OUT = ROOT + 'stati/'
SITE = 'https://sharkgroup.pro'
DATE = '2026-11-13'
YM_ID = 114234559
CATN = {'ven': 'Шпон и отделка', 'st': 'Лестницы', 'door': 'Двери', 'fur': 'Мебель', 'soft': 'Мягкая мебель', 'restore': 'Реставрация'}

tpl = open(SRC + 'template.html', encoding='utf-8').read()
CAP = {}
for ph, cap in re.findall(r"\['\{\{P:(\w+)\}\}','([^']*)'\]", tpl):
    CAP.setdefault(ph, cap)
CAP.update({'n_desk_ws2': 'Резная нога стола, деталь', 'n_peb2': 'Стол с галькой, деталь'})


def webp(name, big=False):
    """m/<name>.webp — тот же формат, что у сайта; возвращает URL с ?h= для обновления кэша."""
    src = SRC + f'img/{name}.jpg'
    im = Image.open(src).convert('RGB'); im.thumbnail((1600, 1600) if big else (1280, 1280))
    b = io.BytesIO(); im.save(b, 'WEBP', quality=80, method=6); data = b.getvalue()
    path = ROOT + f'm/{name}.webp'
    if not os.path.exists(path) or open(path, 'rb').read() != data:
        if not os.path.exists(path): open(path, 'wb').write(data)
    data = open(path, 'rb').read()
    return f'/m/{name}.webp?h=' + hashlib.md5(data).hexdigest()[:8], Image.open(path).size


CSS = '''
:root{--night:#0E1726;--night-2:#16223A;--pit:#070B12;--brass:#C9A46A;--brass-hi:#E2C48F;--ivory:#F2EBDD;--mute:#B8B0A0;--soft:#D9D2C3;--line:rgba(242,235,221,.18);color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--night);color:var(--ivory);font:17px/1.7 'Manrope',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:var(--brass)}a:hover{color:var(--brass-hi)}
img{max-width:100%;display:block}
.top{border-bottom:1px solid var(--line);background:var(--pit)}
.top .in{max-width:1100px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;gap:14px}
.logo{display:flex;align-items:center;gap:10px;white-space:nowrap;text-decoration:none;color:var(--ivory);font-family:'Cormorant Garamond',Georgia,serif;font-weight:600;font-size:20px;letter-spacing:.12em}
.pill{display:inline-flex;align-items:center;min-height:44px;padding:0 18px;border-radius:999px;border:1px solid var(--brass);color:var(--brass);text-decoration:none;font-weight:600;font-size:14px;white-space:nowrap}
main{max-width:760px;margin:0 auto;padding:28px 16px 72px}
.crumbs{font-size:13px;color:var(--mute)}.crumbs a{color:var(--mute)}
h1,h2,h3{font-family:'Cormorant Garamond',Georgia,serif;font-weight:600;line-height:1.08;margin:0}
h1{font-size:clamp(34px,6vw,54px);margin-top:14px}
h2{font-size:clamp(26px,4vw,34px);margin:40px 0 12px}
.lead{font-size:19px;color:var(--soft);margin-top:18px}
p,li{color:var(--soft)}ul{padding-left:20px}li{margin:6px 0}
.cover{margin:26px -16px 0;aspect-ratio:16/10;overflow:hidden;background:var(--pit)}
.cover img{width:100%;height:100%;object-fit:cover}
@media (min-width:800px){.cover{margin-inline:0;border-radius:18px;border:1px solid rgba(201,164,106,.3)}}
figure{margin:0}figcaption{font-size:13px;color:var(--mute);padding-top:8px}
.gal{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}
.gal img{width:100%;aspect-ratio:4/5;object-fit:cover;border-radius:12px;background:var(--pit)}
.cta{margin-top:44px;padding:24px;border:1px solid rgba(201,164,106,.35);border-radius:18px;background:var(--night-2)}
.cta h2{margin:0 0 8px}.cta p{margin:0 0 18px}
.cta .row{display:flex;flex-wrap:wrap;gap:12px}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:50px;padding:0 24px;border-radius:999px;font-weight:600;text-decoration:none}
.btn-brass{background:var(--brass);color:var(--night)}.btn-brass:hover{background:var(--brass-hi);color:var(--night)}
.btn-ghost{border:1px solid rgba(242,235,221,.35);color:var(--ivory)}
.list{display:grid;gap:18px;margin-top:28px}
.card{display:grid;grid-template-columns:140px minmax(0,1fr);gap:16px;text-decoration:none;color:var(--ivory);padding:14px;border:1px solid var(--line);border-radius:16px;transition:border-color .2s,background-color .2s}
.card:hover{border-color:rgba(201,164,106,.5);background:rgba(201,164,106,.06)}
.card img{width:140px;height:110px;object-fit:cover;border-radius:10px}
.card b{font-family:'Cormorant Garamond',Georgia,serif;font-size:22px;line-height:1.15;display:block}
.card small{display:block;margin-top:6px;font-size:14px;color:var(--mute)}
@media (max-width:520px){.logo{font-size:16px;letter-spacing:.08em}.logo svg{width:28px;height:28px}.card{grid-template-columns:96px minmax(0,1fr)}.card img{width:96px;height:96px}.card b{font-size:19px}.top .pill{padding:0 14px}}
.more{margin-top:44px;border-top:1px solid var(--line);padding-top:20px}
.more ul{list-style:none;padding:0}
footer{border-top:1px solid var(--line);font-size:13px;color:var(--mute)}
footer .in{max-width:1100px;margin:0 auto;padding:22px 16px;display:flex;flex-wrap:wrap;gap:10px 22px}
footer a{color:var(--mute)}
'''

LOGO = '<svg width="34" height="34" viewBox="0 0 120 120" fill="none" aria-hidden="true"><circle cx="60" cy="60" r="56" stroke="#C9A46A" stroke-width="4"/><path d="M14 70 C 24 76, 40 79, 60 79 C 80 79, 96 76, 106 70" stroke="#C9A46A" stroke-width="2.4"/><path d="M38 68 C 50 56, 58 38, 74 22 C 70 38, 70 52, 76 68 Z" fill="#C9A46A"/></svg>'

YM = ('<script>(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();'
      'k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})'
      "(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');"
      f"if(/(^|\\.)sharkgroup\\.pro$/.test(location.hostname))ym({YM_ID},'init',{{clickmap:true,trackLinks:true,accurateTrackBounce:true}});"
      "document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[data-goal]');"
      f"if(a&&window.ym)try{{ym({YM_ID},'reachGoal',a.dataset.goal)}}catch(x){{}}}});</script>")


def page(title, desc, canon, body, jsonld, og_img):
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Shark Group">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{canon}"><meta property="og:image" content="{og_img}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600&family=Manrope:wght@400;600&display=swap">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
{YM}
</head>
<body>
<header class="top"><div class="in"><a class="logo" href="/">{LOGO}<span>SHARK GROUP</span></a><a class="pill" href="/#quiz" data-goal="article_cta">Рассчитать проект</a></div></header>
{body}
<footer><div class="in"><a href="/">sharkgroup.pro</a><a href="tel:+79649446637">+7 964 944-66-37</a><a href="/stati/">Статьи</a><a href="https://dzen.ru/sharkgroup" target="_blank" rel="noopener" data-goal="dzen_click">Наш канал в Дзене</a><a href="/privacy.html">Политика конфиденциальности</a><span>ИП Шаркова Элина Валерьевна · ИНН 232010079424 · ОГРНИП 319237500229952</span></div></footer>
</body>
</html>
'''


os.makedirs(OUT, exist_ok=True)
cards, urls = [], []
for a in ARTICLES:
    canon = f'{SITE}/stati/{a["slug"]}.html'
    cov, _ = webp(a['cover'], big=True)
    gal = []
    for ph in a['photos']:
        if ph == a['cover']: continue
        u, _ = webp(ph)
        cap = CAP.get(ph, '')
        gal.append(f'<figure><img src="{u}" alt="{html.escape(cap)}" loading="lazy" decoding="async"><figcaption>{html.escape(cap)}</figcaption></figure>')
    body_html = ''.join(f'<h2>{h}</h2>{t}' for h, t in a['body'])
    others = ''.join(f'<li><a href="/stati/{o["slug"]}.html">{html.escape(o["title"].split(":")[0])}</a></li>' for o in ARTICLES if o is not a)
    cat = a['cat']
    body = f'''<main>
<nav class="crumbs" aria-label="Навигация"><a href="/">Главная</a> · <a href="/stati/">Статьи</a></nav>
<article>
<h1>{html.escape(a["title"])}</h1>
<p class="lead">{a["lead"]}</p>
<figure class="cover"><img src="{cov}" alt="{html.escape(CAP.get(a["cover"], a["title"]))}" fetchpriority="high"></figure>
<figcaption>{html.escape(CAP.get(a["cover"], ""))}</figcaption>
{body_html}
{'<h2>Фото наших работ</h2><div class="gal">' + ''.join(gal) + '</div>' if gal else ''}
</article>
<section class="cta">
<h2>Посчитаем ваш проект</h2>
<p>Пришлите фото помещения или проект — ответим в рабочее время, смету покажем до начала работ.</p>
<div class="row"><a class="btn btn-brass" href="/#quiz" data-goal="article_cta">Рассчитать по фото</a><a class="btn btn-ghost" href="/?cat={cat}#cat" data-goal="article_catalog">{CATN.get(cat, "Каталог")}: цены</a></div>
</section>
<nav class="more" aria-label="Другие статьи"><h2 style="margin-top:0">Ещё статьи</h2><ul>{others}</ul><p>Новые работы и статьи — в нашем канале: <a href="https://dzen.ru/sharkgroup" target="_blank" rel="noopener" data-goal="dzen_click">Shark Group в Дзене</a>.</p></nav>
</main>'''
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Article', 'headline': a['title'], 'description': a['desc'], 'image': SITE + cov.split('?')[0],
         'datePublished': DATE, 'dateModified': DATE, 'inLanguage': 'ru', 'mainEntityOfPage': canon, 'keywords': a['keys'],
         'author': {'@type': 'Organization', 'name': 'Shark Group', 'url': SITE + '/'},
         'publisher': {'@type': 'Organization', 'name': 'Shark Group', 'url': SITE + '/'}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Главная', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Статьи', 'item': SITE + '/stati/'},
            {'@type': 'ListItem', 'position': 3, 'name': a['title'], 'item': canon}]}]}
    open(OUT + a['slug'] + '.html', 'w', encoding='utf-8').write(page(a['title'] + ' — Shark Group', a['desc'], canon, body, ld, SITE + cov.split('?')[0]))
    thumb, _ = webp(a['cover'], big=True)
    cards.append(f'<a class="card" href="/stati/{a["slug"]}.html"><img src="{thumb}" alt="" loading="lazy"><span><b>{html.escape(a["title"])}</b><small>{html.escape(a["desc"])}</small></span></a>')
    urls.append(canon)

idx = f'''<main>
<nav class="crumbs" aria-label="Навигация"><a href="/">Главная</a></nav>
<h1>Статьи Shark Group</h1>
<p class="lead">Как мы делаем панели из шпона, лестницы, двери и мебель из массива, реставрируем старинную мебель — с фото наших работ, ценами «от» и сроками.</p>
<div class="list">{''.join(cards)}</div>
</main>'''
ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': 'Статьи Shark Group', 'url': SITE + '/stati/'}
open(OUT + 'index.html', 'w', encoding='utf-8').write(page('Статьи о панелях из шпона, лестницах, дверях и мебели — Shark Group',
     'Статьи Shark Group: стеновые панели из шпона, лестницы на второй этаж, двери из массива, реставрация мебели, мягкая мебель на заказ в Сочи.',
     SITE + '/stati/', idx, ld, SITE + '/m/p24.webp'))

sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f'  <url><loc>{SITE}/</loc><lastmod>{DATE}</lastmod><priority>1.0</priority></url>',
      f'  <url><loc>{SITE}/stati/</loc><lastmod>{DATE}</lastmod><priority>0.7</priority></url>']
sm += [f'  <url><loc>{u}</loc><lastmod>{DATE}</lastmod><priority>0.6</priority></url>' for u in urls]
sm += [f'  <url><loc>{SITE}/privacy.html</loc><lastmod>{DATE}</lastmod><priority>0.2</priority></url>', '</urlset>', '']
open(ROOT + 'sitemap.xml', 'w', encoding='utf-8').write('\n'.join(sm))
print(len(urls), 'статей ->', OUT)
