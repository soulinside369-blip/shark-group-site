import numpy as np, sys
from scipy.ndimage import zoom, gaussian_filter
from PIL import Image

W, H = 2000, 1400
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

def noise(shape, cells, rng, order=3):
    gy, gx = max(2, int(cells[0])), max(2, int(cells[1]))
    g = rng.standard_normal((gy + 3, gx + 3))
    z = zoom(g, ((shape[0] + 40) / (gy + 3), (shape[1] + 40) / (gx + 3)), order=order)
    return z[20:20 + shape[0], 20:20 + shape[1]]

def fbm(shape, cells, rng, oct=5, aniso=(1, 1)):
    s = np.zeros(shape); a = 1; tot = 0
    for o in range(oct):
        c = (cells[0] * 2 ** o * aniso[0], cells[1] * 2 ** o * aniso[1])
        s += a * noise(shape, c, rng); tot += a; a *= 0.5
    return s / tot

def ramp(t, stops):
    t = np.clip(t, 0, 1)
    xs = [s[0] for s in stops]; cs = np.array([s[1] for s in stops], float) / 255
    out = np.zeros(t.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(t, xs, cs[:, ch])
    return out

def hexc(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def wood(name, seed, palette, ring_freq, tilt, depth, warp, pores, pore_amt,
         fiber_amt, ring_sharp, figure=0.0, knots=(), cracks=(), gray=0.0, sheen=0.06):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:H, 0:W].astype(float)
    X = x / W; Y = (y - H * 0.5) / H
    wv = fbm((H, W), (2, 1.5), rng, 4) * warp + fbm((H, W), (10, 3), rng, 3) * warp * 0.25
    d = depth + tilt * (X - 0.2) + fbm((H, W), (1.5, 2), rng, 2) * 0.03
    R = np.sqrt((Y + wv) ** 2 + d ** 2)
    rings = R * ring_freq + fbm((H, W), (40, 3), rng, 3) * 0.12
    for kx, ky, kr in knots:
        dx = (x - kx * W) / (kr * W); dy = (y - ky * H) / (kr * W * 0.45)
        kd = np.sqrt(dx ** 2 + dy ** 2)
        rings = rings + np.exp(-kd ** 2 * 0.2) * 5.0 / (kd + 0.5)
    f = rings - np.floor(rings)
    # thin latewood line + porous earlywood band
    var = 0.55 + 0.45 * np.clip(fbm((H, W), (6, 2), rng, 3) * 2.2 + 0.5, 0, 1)
    lw = np.exp(-((f - 0.9) / ring_sharp) ** 2) * var
    broad = np.clip((f - 0.45) / 0.45, 0, 1) ** 2 * 0.22
    ew = np.exp(-((f - 0.04) / 0.05) ** 2) * 0.10
    tone = 0.30 + 0.30 * lw + broad + ew
    # lengthwise tonal stripes of veneer
    tone += fbm((H, W), (14, 1.2), rng, 4) * 0.09
    tone += fbm((H, W), (3, 3), rng, 3) * 0.05
    # fibres
    fib = noise((H, W), (H / 3, W / 160), rng, order=3)
    tone += fib * fiber_amt
    if figure:
        tone += np.sin(x / W * 70 + fbm((H, W), (3, 5), rng, 3) * 10) * figure * (0.5 + fbm((H, W), (2, 2), rng, 2))
    if pore_amt:
        pn = noise((H, W), (H / 3.2, W / 45), rng, order=1)
        thr = np.quantile(pn, 0.955)
        pm = np.clip((pn - thr) * 4, 0, 1)
        zone = 0.35 + 0.65 * np.exp(-((f - 0.08) / 0.12) ** 2)
        tone += pm * pore_amt * zone
    for cx, cy, cl in cracks:
        n = 600; t = np.linspace(0, 1, n)
        px = (cx + t * cl) * W; py = cy * H + np.cumsum(rng.standard_normal(n)) * 0.8
        m = np.zeros((H, W))
        wdt = (np.sin(t * np.pi) * 3).astype(int)
        for a, b2, ww in zip(px.astype(int), py.astype(int), wdt):
            if 0 <= a < W and 4 <= b2 < H - 4:
                m[b2 - ww:b2 + ww + 1, a] = 1
        tone += np.clip(gaussian_filter(m, 0.8) * 2, 0, 1) * 0.7
    tone = np.clip(tone, 0, 1)
    rgb = ramp(tone, palette)
    if gray:
        g = rgb.mean(-1, keepdims=True); rgb = rgb * (1 - gray) + g * gray
    # soft light sheen
    rgb += sheen * 0.3 * np.exp(-((X - 0.65) ** 2) / 0.08)[..., None] * np.exp(-((Y + 0.1) ** 2) / 0.2)[..., None]
    # fine noise for photo realism
    rgb += rng.standard_normal(rgb.shape) * 0.008
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    img.save(f'{OUT}/{name}.jpg', quality=88, optimize=True, progressive=True)
    print(name)

P = lambda *hs: [(i / (len(hs) - 1), hexc(h)) for i, h in enumerate(hs)]

jobs = {
 'oak':        dict(seed=11, palette=P('#E9CDA2', '#D7B383', '#BE9564', '#946C42', '#5E4325'), ring_freq=70, tilt=0.12, depth=0.015, warp=0.03, pores=1, pore_amt=0.30, fiber_amt=0.06, ring_sharp=0.05),
 'oak_rustic': dict(seed=23, palette=P('#E0C49C', '#CBA77C', '#AE875C', '#7F5E3C', '#4A3420'), ring_freq=75, tilt=0.16, depth=0.01, warp=0.04, pores=1, pore_amt=0.32, fiber_amt=0.07, ring_sharp=0.06, knots=[(0.34, 0.6, 0.02), (0.8, 0.28, 0.014)], cracks=[(0.06, 0.4, 0.2), (0.56, 0.74, 0.16)]),
 'walnut':     dict(seed=5, palette=P('#A47C58', '#86623F', '#67472D', '#4A311F', '#2C1C11'), ring_freq=45, tilt=0.14, depth=0.02, warp=0.04, pores=1, pore_amt=0.14, fiber_amt=0.07, ring_sharp=0.11),
 'ash':        dict(seed=31, palette=P('#F3E8D2', '#E8D6B6', '#D6BF98', '#B99C72', '#8C7150'), ring_freq=50, tilt=0.13, depth=0.015, warp=0.03, pores=1, pore_amt=0.26, fiber_amt=0.05, ring_sharp=0.06),
 'oak_white':  dict(seed=47, palette=P('#EFE9DE', '#E0D7C8', '#CDC0AC', '#AC9B84', '#807261'), ring_freq=70, tilt=0.12, depth=0.02, warp=0.03, pores=1, pore_amt=0.30, fiber_amt=0.05, ring_sharp=0.05, gray=0.25),
 'oak_smoked': dict(seed=59, palette=P('#8F6D4E', '#76563A', '#5C412A', '#422D1D', '#281A10'), ring_freq=68, tilt=0.12, depth=0.015, warp=0.035, pores=1, pore_amt=0.20, fiber_amt=0.07, ring_sharp=0.06),
 'elm':        dict(seed=71, palette=P('#CF9F6E', '#B58253', '#93643A', '#6D4628', '#452A16'), ring_freq=55, tilt=0.18, depth=0.01, warp=0.06, pores=1, pore_amt=0.24, fiber_amt=0.07, ring_sharp=0.07),
}
for k in (sys.argv[2:] or jobs):
    wood(k, **jobs[k])
