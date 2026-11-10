# -*- coding: utf-8 -*-
"""Подготовка фото работ в едином стиле Shark Group.

    python photos.py "<папка выгрузки Telegram>"     ->  img/pN.jpg  (N = номер фото в выгрузке)

Что делает с каждым кадром, который используется в template.html:
  1. убирает лишнее обрезкой (обувь у порога, люди, отражение фотографа, инструмент, мусор, чёрные поля,
     водяные знаки телефона) — таблица CROP: доли кадра (слева, сверху, справа, снизу);
  2. приводит к одному характеру: выравнивает экспозицию и баланс белого, слегка приглушает насыщенность,
     тени уводит в «ночь» (#0E1726), света — в тёплую латунь, добавляет мягкую виньетку и резкость.
Кадры, где лишнее не убрать обрезкой, на сайт не берём (см. DROP) — дорисовывать настоящие фото нельзя.
Пачку 130–144 владелец запретил использовать.
"""
import sys, glob, re, os
import numpy as np
from PIL import Image, ImageOps, ImageFilter

E = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/img'

# (left, top, right, bottom) в долях исходного кадра
CROP = {
    1: (0, 0, 1, .52),        # зал Fish Bone: гости и официант внизу кадра -> оставляем потолок и люстру
    15: (0, 0, .82, 1),       # человек в глубине справа
    17: (0, .16, 1, 1),       # рука и посторонние предметы сверху
    19: (0, .14, .92, 1),
    22: (.16, 0, 1, 1),       # отражение фотографа в зеркале
    27: (.12, 0, 1, .90),     # строительный мусор
    28: (0, 0, 1, .78),
    29: (0, 0, 1, .82),
    31: (0, 0, 1, .83),
    34: (0, 0, 1, .90),       # водяной знак телефона
    36: (.10, 0, 1, .82),     # обувь и вещи на полу
    46: (0, 0, 1, .73),       # обувь у порога (просьба заказчика)
    48: (0, 0, 1, .83),
    49: (.22, 0, 1, 1),       # обувь слева
    54: (.10, 0, 1, 1),       # бутылка и коробка на столешнице
    58: (0, 0, 1, .93),
    66: (0, 0, .90, 1),       # машина справа
    87: (0, 0, 1, .93),       # обувь внизу кадра
    89: (.06, 0, 1, 1),       # рука слева
    109: (.07, 0, 1, .92),    # баллон пены
    123: (0, 0, .90, .84),    # упаковка на полу
    73: (0, .04, 1, 1),       # остаток чёрного поля
}
TRIM_BLACK = {26, 73, 77}     # скриншоты с чёрными полями
# не берём: красная куртка на перилах (32, 33), мусор под лестницей (35), стиральная машина (44),
# дубли (50, 106, 111), пылесос (57), «до» с инструментом (113), люди в кадре (3, 10, 70, 78)
DROP = {3, 10, 32, 33, 35, 44, 50, 57, 70, 78, 106, 111, 113} | set(range(130, 145))


def trim_black(im):
    a = np.asarray(im.convert('L')) > 24
    ys = np.where(a.mean(1) > .5)[0]; xs = np.where(a.mean(0) > .5)[0]
    return im.crop((xs[0], ys[0], xs[-1] + 1, ys[-1] + 1))


def grade(im):
    """единая цветокоррекция: мягко и без искажения цвета материала"""
    a = np.asarray(im, np.float32) / 255
    # экспозиция: растягиваем уровни по 0,5 / 99,5 перцентилю, наполовину
    lum = a @ np.array([.299, .587, .114], np.float32)
    lo, hi = np.percentile(lum, .5), np.percentile(lum, 99.5)
    a = a * .5 + np.clip((a - lo) / max(hi - lo, .2), 0, 1) * .5
    # баланс белого: на четверть к нейтральному (убирает жёлтый свет ламп, дерево остаётся тёплым)
    m = a.reshape(-1, 3).mean(0); g = m.mean()
    a = a * (1 + (g / np.maximum(m, 1e-3) - 1) * .25)
    a = np.clip(a, 0, 1)
    # лёгкая S-кривая и приглушённая насыщенность
    a = a + (a - a * a * (3 - 2 * a)) * -.28
    lum = (a @ np.array([.299, .587, .114], np.float32))[..., None]
    a = lum + (a - lum) * .93
    # сплит-тон: тени — в ночь, света — в латунь
    night = np.array([14, 23, 38], np.float32) / 255; brass = np.array([226, 196, 143], np.float32) / 255
    sh = np.clip(1 - lum * 2.2, 0, 1) ** 1.5; hl = np.clip(lum * 1.6 - .7, 0, 1) ** 1.5
    a = a * (1 - sh * .10) + night * sh * .10
    a = a * (1 - hl * .05) + brass * hl * .05
    # виньетка
    h, w = a.shape[:2]; y, x = np.mgrid[0:h, 0:w]
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    a = a * (1 - np.clip(r - .75, 0, 1)[..., None] ** 2 * .22)
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(radius=1.6, percent=45, threshold=2))


used = sorted({int(x) for x in re.findall(r'\{\{P:p(\d+)\}\}', open(HERE + '/template.html', encoding='utf-8').read())})
src = {int(re.search(r'photo_(\d+)@', f).group(1)): f for f in glob.glob(E + '/photos/*.jpg') if '_thumb' not in f}
bad = [n for n in used if n in DROP]
assert not bad, 'в template.html есть запрещённые/исключённые фото: %s' % bad
for f in glob.glob(OUT + '/p*.jpg'):
    if int(re.search(r'p(\d+)\.jpg', f).group(1)) not in used: os.remove(f)
for n in used:
    im = ImageOps.exif_transpose(Image.open(src[n])).convert('RGB')
    if n in TRIM_BLACK: im = trim_black(im)
    if n in CROP:
        l, t, r, b = CROP[n]; w, h = im.size; im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    im = grade(im)
    im.thumbnail((1600, 1600)); im.save(f'{OUT}/p{n}.jpg', quality=90)
print(len(used), 'фото обработано')
