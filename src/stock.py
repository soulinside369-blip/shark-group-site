# -*- coding: utf-8 -*-
"""Атмосферные кадры для трейлера (слова «Дерево. Металл. Камень.») — лицензионные фото с Unsplash.

    python stock.py        ->  img/s_wood.jpg, img/s_metal.jpg, img/s_stone.jpg

ВАЖНО: это НЕ работы и НЕ цех Shark Group — только настроение под слова о материалах.
Работы в трейлере и на сайте остаются настоящими. Когда заказчик снимет свой цех — заменить.
Лицензия Unsplash: бесплатное коммерческое использование, указание автора не обязательно.
Источники:
  wood  — Clem Onojeghuo,  https://unsplash.com/photos/hdW4rZPHe2g  (стружка на верстаке)
  metal — Ben Spray,       https://unsplash.com/photos/P_Obxo3hrVQ  (сварка в тёмном цеху, лица не видно)
  stone — Peter Muniz,     https://unsplash.com/photos/lhIOmjqf728  (душевая, облицованная травертином)
"""
import io, os, urllib.request
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = {
    # имя: (id фото, обрезка в долях кадра l,t,r,b, яркость)
    'wood':  ('photo-1470342495351-a5f90c5011cd', (0, .06, 1, .94), .80),
    'metal': ('photo-1745448797900-35d08e85e9db', (.24, .04, .82, .66), 1.25),
    'stone': ('photo-1763485956229-a5e1396f7d3a', (.36, 0, 1, 1), .92),
}


def grade(im, gain):
    """тот же характер, что у фото работ: тени в «ночь», света в латунь, виньетка"""
    a = np.asarray(im, np.float32) / 255 * gain
    lum = (a @ np.array([.299, .587, .114], np.float32))[..., None]
    a = lum + (a - lum) * .9
    night = np.array([14, 23, 38], np.float32) / 255; brass = np.array([226, 196, 143], np.float32) / 255
    sh = np.clip(1 - lum * 2.2, 0, 1) ** 1.5; hl = np.clip(lum * 1.6 - .7, 0, 1) ** 1.5
    a = a * (1 - sh * .14) + night * sh * .14
    a = a * (1 - hl * .06) + brass * hl * .06
    h, w = a.shape[:2]; y, x = np.mgrid[0:h, 0:w]
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    a = a * (1 - np.clip(r - .6, 0, 1)[..., None] ** 2 * .45)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


import sys
for name, (pid, (l, t, r, b), gain) in SRC.items():
    if len(sys.argv) > 1 and name not in sys.argv[1:]: continue
    raw = urllib.request.urlopen(f'https://images.unsplash.com/{pid}?w=3600&q=88&fm=jpg', timeout=60).read()
    im = Image.open(io.BytesIO(raw)).convert('RGB'); w, h = im.size
    im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    # к кадру 16:9
    w, h = im.size; th = int(w * 9 / 16)
    if th < h: im = im.crop((0, (h - th) // 2, w, (h - th) // 2 + th))
    im.thumbnail((2400, 2400))
    grade(im, gain).save(f'{HERE}/img/s_{name}.jpg', quality=90)
    print(name, im.size)
