import numpy as np, sys
from scipy.ndimage import zoom, gaussian_filter
from PIL import Image

OUT = sys.argv[1]
W, H = 1600, 1100
RNG = np.random.default_rng(7)

def noise(shape, cells, rng=RNG, order=3):
    gy, gx = max(2, int(cells[0])), max(2, int(cells[1]))
    g = rng.standard_normal((gy + 3, gx + 3))
    z = zoom(g, ((shape[0] + 40) / (gy + 3), (shape[1] + 40) / (gx + 3)), order=order)
    return z[20:20 + shape[0], 20:20 + shape[1]]

def fbm(shape, cells, oct=5, rng=RNG):
    s = np.zeros(shape); a = 1; t = 0
    for o in range(oct):
        s += a * noise(shape, (cells[0] * 2 ** o, cells[1] * 2 ** o), rng); t += a; a *= .5
    return s / t

def hx(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float) / 255

def shade(alb, h, strength=6.0, amb=.42, kd=.75, ks=0.0, shin=40, light=(-.55, -.65, .55)):
    gy, gx = np.gradient(h)
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array(light, float); L /= np.linalg.norm(L)
    dif = np.clip((n * L).sum(2), 0, 1)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    sp = np.clip((n * Hh).sum(2), 0, 1) ** shin
    rgb = alb * (amb + kd * dif)[..., None] + ks * sp[..., None]
    return rgb

def save(rgb, name):
    rgb = rgb + RNG.standard_normal(rgb.shape) * .006
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(f'{OUT}/{name}.jpg', quality=88, optimize=True, progressive=True)
    print(name)

Y, X = np.mgrid[0:H, 0:W].astype(float)

def edge_profile(d, r):  # d: distance to tile edge in px, r: rounding radius
    return np.clip(d / r, 0, 1) ** .5

# ---------------- travertine ----------------
def travertine():
    band = fbm((H, W), (40, 1.5), 5)
    base = fbm((H, W), (3, 4), 4)
    t = .5 + band * .55 + base * .25
    alb = hx('#E2D3B8')[None, None] * (1 - t[..., None] * .18) + hx('#B89D78')[None, None] * (t[..., None] * .18)
    alb = alb * (1 + fbm((H, W), (200, 30), 2)[..., None] * .05)
    p = noise((H, W), (H / 9, W / 40), order=1)
    pm = gaussian_filter((p > np.quantile(p, .965)).astype(float), (.9, 2.2))
    holes = np.clip(pm * 2.2, 0, 1) * np.clip(.5 + band * 3, 0, 1)
    h = base * 1.2 + band * .8 - holes * 3
    alb = alb * (1 - holes[..., None] * .45) + hx('#8A7356')[None, None] * holes[..., None] * .3
    rgb = shade(alb, gaussian_filter(h, 1.2), strength=2, amb=.72, kd=.36)
    # soft leaf shadow

    save(rgb, 'travertine')

# ---------------- microcement / concrete ----------------
def concrete():
    m = fbm((H, W), (4, 5), 6)
    alb = hx('#BDBAB4')[None, None] * (1 + m[..., None] * .12)
    alb *= (1 + noise((H, W), (H / 2, W / 2), order=1)[..., None] * .035)
    h = m * 1.5
    rng = np.random.default_rng(3)
    holes = np.zeros((H, W))
    for _ in range(520):
        cx, cy = rng.integers(0, W), rng.integers(0, H)
        r = rng.choice([1.2, 1.8, 2.5, 3.5, 5, 7], p=[.3, .25, .2, .13, .08, .04])
        x0, x1, y0, y1 = max(0, int(cx - r - 2)), min(W, int(cx + r + 3)), max(0, int(cy - r - 2)), min(H, int(cy + r + 3))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dd = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.15) ** 2)
        holes[y0:y1, x0:x1] = np.maximum(holes[y0:y1, x0:x1], np.clip(r - dd + .8, 0, 1))
    h = h - holes * 4
    alb = alb * (1 - holes[..., None] * .55)
    save(shade(alb, gaussian_filter(h, .8), strength=4, amb=.62, kd=.45), 'concrete')

# ---------------- kit-kat glazed bronze ----------------
def kitkat():
    cw, ch, g = 58, 520, 5
    col = (X // cw).astype(int); row = ((Y + 60) // ch).astype(int)
    u = (X % cw) / cw; v = ((Y + 60) % ch) / ch
    tid = col * 7 + row * 131
    rng = np.random.default_rng(11)
    seeds = rng.random(5000)
    s = seeds[tid % 5000]
    grout = ((X % cw) < g) | (((Y + 60) % ch) < g)
    # glaze: dark rust to amber with vertical runs
    run = fbm((H, W), (2, 26), 3)
    tt = np.clip(.42 + (s - .5) * .9 + run * .55 + (v - .5) * .25, 0, 1)
    c1, c2, c3 = hx('#3E1C0C'), hx('#7A3A16'), hx('#C27A3C')
    alb = np.where(tt[..., None] < .5, c1 + (c2 - c1) * (tt[..., None] / .5), c2 + (c3 - c2) * ((tt[..., None] - .5) / .5))
    # pale edge glaze pooling
    edge = np.minimum(u, 1 - u) * cw
    alb = alb + (np.exp(-edge / 6)[..., None] * hx('#E8C9A0') * .25)
    h = np.sin(np.clip(u, 0, 1) * np.pi) ** .5 * 5 + run * .4
    h = np.where(grout, -2, h)
    alb = np.where(grout[..., None], hx('#3A2F28'), alb)
    rgb = shade(alb, gaussian_filter(h, 1.2), strength=1.4, amb=.55, kd=.6, ks=.35, shin=90, light=(-.35, -.3, .88))
    save(rgb, 'kitkat_bronze')

# ---------------- black brick herringbone ----------------
def herringbone(color='#2E2F33', grout_c='#18181A', unit=68, name='brick_black'):
    x = X / unit + 3; y = Y / unit
    k = np.floor(y); t = x - k + 4; m = np.floor(t / 8); xp = x - 8 * m; r = t - 8 * m
    isH = r >= 4
    j = np.floor(xp) + 1
    bid = np.where(isH, k * 1000 + m * 7 + .5, j * 1000 + m * 7)
    along = np.where(isH, xp - k, y - j)
    across = np.where(isH, y - k, xp - (j - 1))
    # distance to edge in px
    dx = np.minimum(across, 1 - across) * unit; dl = np.minimum(along, 4 - along) * unit
    d = np.minimum(dx, dl)
    gw = 3
    grout = d < gw
    rough = fbm((H, W), (H / 30, W / 30), 4) * 1.0 + fbm((H, W), (H / 90, W / 90), 2) * .3
    rng = np.random.default_rng(5)
    sv = rng.random(20000)
    s = sv[(np.abs(bid) * 13 % 20000).astype(int)]
    h = edge_profile(d - gw, 8) * 5 + rough * 4.5 * np.clip((d - gw) / 6, 0, 1)
    h = np.where(grout, -1.5, h)
    alb = hx(color)[None, None] * (1 + (s[..., None] - .5) * .18) * (1 + rough[..., None] * .12)
    alb = np.where(grout[..., None], hx(grout_c), alb)
    save(shade(alb, gaussian_filter(h, .9), strength=2.6, amb=.45, kd=.95, ks=.06, shin=12), name)

# ---------------- tumbled stone (mixed sizes) ----------------
def tumbled():
    rng = np.random.default_rng(9)
    ids = np.zeros((H, W), int); dist = np.zeros((H, W)); y = 0; n = 0
    heights = [150, 220, 150, 290, 220, 150, 220]
    while y < H:
        hgt = heights[n % len(heights)] + rng.integers(-10, 10); x = -rng.integers(0, 120)
        while x < W:
            w = rng.choice([150, 220, 290, 360]); n += 1
            x0, x1, y0, y1 = max(0, x), min(W, x + w), y, min(H, y + hgt)
            if x1 > x0:
                yy, xx = np.mgrid[y0:y1, x0:x1]
                ids[y0:y1, x0:x1] = n
                dist[y0:y1, x0:x1] = np.minimum(np.minimum(xx - x, x + w - 1 - xx), np.minimum(yy - y, y + hgt - 1 - yy))
            x += w
        y += hgt
    s = rng.random(n + 2)[ids]
    g = 2.5
    grout = dist < g
    patch = fbm((H, W), (6, 8), 5)
    rust = np.clip(.55 + patch * 1.6, 0, 1) * (s > .7) * .85
    dark = hx('#1F2022') * (1 + (s[..., None] - .5) * .25)
    alb = dark * (1 - rust[..., None]) + hx('#6A5440')[None, None] * rust[..., None]
    alb *= (1 + fbm((H, W), (H / 30, W / 30), 3)[..., None] * .18)
    veins = np.exp(-np.abs(fbm((H, W), (10, 14), 4)) * 90) * (s[..., None] > .8)[..., 0]
    alb = alb + veins[..., None] * .25
    pits = fbm((H, W), (H / 18, W / 18), 3)
    h = edge_profile(dist - g, 18) * 6 + pits * 1.1
    h = np.where(grout, -2, h)
    alb = np.where(grout[..., None], hx('#141414'), alb)
    save(shade(alb, gaussian_filter(h, 1.1), strength=2.2, amb=.5, kd=.85, ks=.05, shin=10), 'stone_tumbled')

# ---------------- zellige olive ----------------
def zellige():
    sz, g = 132, 4
    cx = (X // sz).astype(int); cy = (Y // sz).astype(int)
    u = X % sz; v = Y % sz
    d = np.minimum(np.minimum(u, sz - 1 - u), np.minimum(v, sz - 1 - v))
    grout = d < g
    rng = np.random.default_rng(21)
    sv = rng.random((40, 40))
    s = sv[cy % 40, cx % 40]
    pal = [hx('#2F4A3B'), hx('#3E5A48'), hx('#4A6852'), hx('#27402F'), hx('#587760')]
    idx = (s * len(pal)).astype(int).clip(0, len(pal) - 1)
    alb = np.stack(pal)[idx]
    cloud = fbm((H, W), (14, 20), 4)
    alb = alb * (1 + cloud[..., None] * .22)
    alb = alb + np.exp(-(d - g) / 5)[..., None] * hx('#C9D6C0') * .18
    h = edge_profile(d - g, 14) * 4 + fbm((H, W), (H / 110, W / 110), 2) * 3
    h = np.where(grout, -2, h)
    alb = np.where(grout[..., None], hx('#D8D1C3'), alb)
    save(shade(alb, gaussian_filter(h, 1.3), strength=1.6, amb=.55, kd=.6, ks=.45, shin=120, light=(-.4, -.45, .8)), 'zellige_olive')

for f in (sys.argv[2:] or ['travertine', 'concrete', 'kitkat', 'herringbone', 'tumbled', 'zellige']):
    globals()[f]()
