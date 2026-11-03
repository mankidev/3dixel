import math
import numpy as np

FACES = ("front", "back", "right", "left", "top", "bottom")


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def face_size(f, t, face, density=1):
    d = np.subtract(t, f) * density
    w, h = {
        "front": (d[0], d[1]), "back": (d[0], d[1]),
        "right": (d[2], d[1]), "left": (d[2], d[1]),
        "top": (d[0], d[2]), "bottom": (d[0], d[2]),
    }[face]
    return max(1, round(h)), max(1, round(w))


def to_rgb(idx, pal):
    return np.array(pal)[np.clip(idx, 0, len(pal) - 1)]


def rgba(img, a=1.0):
    return np.concatenate([img, np.full(img.shape[:2] + (1,), a)], -1)


def side_bands(h, w, top, bottom):
    rows = np.linspace(top, bottom, h).round().astype(int) if h > 1 else np.array([top])
    return np.repeat(rows[:, None], w, 1)


def shaded_idx(f, t, base):
    out = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        if face == "top":
            idx = np.full((h, w), base)
        elif face == "bottom":
            idx = np.full((h, w), base - 2)
        else:
            idx = side_bands(h, w, base, base - 2)
        out[face] = idx
    return out


def fur(idx, seed, along_rows=True, amount=0.26):
    rng = np.random.default_rng(seed)
    h, w = idx.shape
    out = idx.copy()
    r = rng.random((h, w))
    out[r < amount * 0.45] += 1
    out[r > 1 - amount * 0.55] -= 1
    for _ in range(max(1, h * w // 14)):
        y, x = rng.integers(0, h), rng.integers(0, w)
        d = 1 if rng.random() < 0.5 else -1
        if along_rows:
            out[y, x:x + 2] = idx[y, x:x + 2] + d
        else:
            out[y:y + 2, x] = idx[y:y + 2, x] + d
    return out


def furred(f, t, base, pal, seed):
    idx = shaded_idx(f, t, base)
    return {face: to_rgb(fur(v, seed + i, face in ("front", "back", "top", "bottom")), pal) for i, (face, v) in enumerate(idx.items())}


def part(f, t, tex, tr=()):
    return {"from": f, "to": t, "tex": tex, "tr": list(tr)}


def mirror(p):
    (x0, y0, z0), (x1, y1, z1) = p["from"], p["to"]
    src = p["tex"]
    flip = lambda img: None if img is None else img[:, ::-1]
    tex = {"left": flip(src.get("right")), "right": flip(src.get("left"))}
    for k in ("front", "back", "top", "bottom"):
        tex[k] = flip(src.get(k))
    tr = [((-px, py, pz), (rx, -ry, -rz)) for (px, py, pz), (rx, ry, rz) in p["tr"]]
    out = dict(p)
    out.update({"from": (-x1, y0, z0), "to": (-x0, y1, z1), "tex": tex, "tr": tr})
    return out


def hair_plane(f, t, tr, pal, tones, seed, up=3, down=2, density=0.7):
    rng = np.random.default_rng(seed)
    L = round(t[0] - f[0])
    core = round(t[1] - f[1])
    h = up + core + down
    img = np.zeros((h, L, 4))
    for x in range(L):
        for side, reach in ((-1, up), (1, down)):
            if reach == 0 or rng.random() > density:
                continue
            n = int(rng.integers(1, reach + 1))
            for k in range(n):
                y = up - 1 - k if side < 0 else up + core + k
                xx = min(L - 1, x + k // 2)
                tone = tones[min(len(tones) - 1, k * len(tones) // max(reach, 1))]
                img[y, xx, :3] = pal[tone]
                img[y, xx, 3] = 1
    zc = (f[2] + t[2]) / 2
    tex = {k: None for k in FACES}
    tex["front"] = img
    return {"from": (f[0], f[1] - down, zc), "to": (t[0], t[1] + up, zc), "tex": tex, "tr": list(tr), "double": True}


def fk_tip_y(hip_y, segs, delta, solve):
    y = hip_y
    cum = 0.0
    for k, s in enumerate(segs):
        a = s[3] + (delta if k == solve else 0)
        cum += a
        y += s[0] * math.sin(math.radians(cum))
    return y


def solve_leg(hip_y, segs, ground, solve):
    lo, hi = -60.0, 60.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if fk_tip_y(hip_y, segs, mid, solve) > ground:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def chain(side, hip, splay, segs, texfn, hairfn=None, ground=0.5, solve=1):
    delta = solve_leg(hip[1], segs, ground, solve)
    x, y, z = hip
    links = []
    for k, (L, hgt, wid, ang) in enumerate(segs):
        a = ang + (delta if k == solve else 0)
        links = [((x, y, z), (0, 0, a))] + links
        f = (x, y - hgt / 2, z - wid / 2)
        t = (x + L, y + hgt / 2, z + wid / 2)
        tr = links + [(hip, (0, splay, 0))]
        side.append(part(f, t, texfn(k, f, t), tr))
        if hairfn is not None:
            hp = hairfn(k, f, t, tr)
            if isinstance(hp, list):
                side.extend(hp)
            elif hp is not None:
                side.append(hp)
        x += L


def strands(idx, seed, direction="up", clump=3, lo=4, hi=7, tip=0.2):
    rng = np.random.default_rng(seed)
    rot = {"up": 0, "left": 1, "down": 2, "right": 3}[direction]
    work = np.rot90(idx, rot).copy()
    h, w = work.shape
    out = work.copy()
    x = 0
    while x < w:
        cw = int(rng.integers(1, clump + 1))
        y = h - 1 + int(rng.integers(0, 3))
        while y >= 0:
            n = int(rng.integers(lo, hi + 1))
            top = y - n + 1
            for xx in range(x, min(w, x + cw)):
                for k in range(n):
                    yy = y - k
                    if not (0 <= yy < h):
                        continue
                    frac = k / max(n - 1, 1)
                    d = -1 if frac < 0.3 else (0 if k < n - 2 else 1)
                    if k == n - 1 and rng.random() < tip:
                        d = 2
                    out[yy, xx] = work[yy, xx] + d
            y = top - 1
        x += cw
    return np.rot90(out, -rot)


def fringe_plane(f, t, axis, tr, pal, tones, seed, pad=2, density=0.55, down_scale=0.5, at=None):
    rng = np.random.default_rng(seed)
    if axis == "z":
        w = round(t[0] - f[0]) + 2 * pad
    else:
        w = round(t[2] - f[2]) + 2 * pad
    h = round(t[1] - f[1]) + 2 * pad
    img = np.zeros((h, w, 4))

    def put(y, x, k, n):
        if 0 <= y < h and 0 <= x < w:
            tone = tones[min(len(tones) - 1, k * len(tones) // max(n, 1))]
            img[y, x, :3] = pal[tone]
            img[y, x, 3] = 1

    for x in range(pad, w - pad):
        if rng.random() < density:
            n = int(rng.integers(1, pad + 1))
            lean = int(rng.integers(-1, 2))
            for k in range(n):
                put(pad - 1 - k, x + (lean if k == n - 1 else 0), k, n)
        if rng.random() < density * down_scale:
            put(h - pad, x, 0, 1)
    for y in range(pad, h - pad):
        for side in (-1, 1):
            if rng.random() < density:
                n = int(rng.integers(1, pad + 1))
                for k in range(n):
                    x = pad - 1 - k if side < 0 else w - pad + k
                    put(y + (1 if k == n - 1 and rng.random() < 0.5 else 0), x, k, n)
    tex = {k: None for k in FACES}
    cx, cy, cz = [(a + b) / 2 for a, b in zip(f, t)]
    if axis == "z":
        cz = cz if at is None else at
        tex["front"] = img
        pf, pt = (f[0] - pad, f[1] - pad, cz), (t[0] + pad, t[1] + pad, cz)
    else:
        cx = cx if at is None else at
        tex["right"] = img
        pf, pt = (cx, f[1] - pad, f[2] - pad), (cx, t[1] + pad, t[2] + pad)
    return {"from": pf, "to": pt, "tex": tex, "tr": list(tr), "double": True}


def hair_card(base, w, L, rots, tr, pal, tones, seed, gap=0.2):
    rng = np.random.default_rng(seed)
    img = np.zeros((L, w, 4))
    for x in range(w):
        if rng.random() < gap:
            continue
        n = int(rng.integers(max(1, L // 2), L + 1))
        bend = int(rng.integers(-1, 2)) if n > 2 else 0
        for k in range(n):
            y = L - 1 - k
            xx = x + (bend if k >= n * 2 // 3 else 0)
            if 0 <= xx < w:
                tone = tones[min(len(tones) - 1, k * len(tones) // n)]
                img[y, xx, :3] = pal[tone]
                img[y, xx, 3] = 1
    bx, by, bz = base
    tex = {k: None for k in FACES}
    tex["front"] = img
    local = [(base, r) for r in rots]
    return {"from": (bx - w / 2, by, bz), "to": (bx + w / 2, by + L, bz), "tex": tex, "tr": local + list(tr), "double": True}


def flow(idx, seed, direction="up"):
    rng = np.random.default_rng(seed)
    rot = {"up": 0, "left": 1, "down": 2, "right": 3}[direction]
    work = np.rot90(idx, rot).copy()
    h, w = work.shape
    out = work.copy()
    for x in range(w):
        y = h - 1 - int(rng.integers(0, 3))
        while y >= 0:
            n = int(rng.integers(3, 7))
            for k in range(n):
                if 0 <= y - k < h and k < n - 1:
                    out[y - k, x] = work[y - k, x] - (1 if k < 2 else 0)
            y -= n + int(rng.integers(0, 2))
    return np.rot90(out, -rot)


def noise_field(h, w, seed, cy, cx=None):
    cx = cy if cx is None else cx
    rng = np.random.default_rng(seed)
    g = rng.random((int(h / cy) + 3, int(w / cx) + 3))
    ys = np.arange(h) / cy
    xs = np.arange(w) / cx
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def stretch(f):
    lo, hi = np.percentile(f, [3, 97])
    if hi - lo < 1e-9:
        return np.full_like(f, 0.5)
    return np.clip((f - lo) / (hi - lo), 0, 1)


def quant(f, lo, hi):
    return np.round(lo + f * (hi - lo)).astype(int)


def strand_noise(h, w, seed):
    return stretch(noise_field(h, w, seed, 1, 5) * 0.7 + noise_field(h, w, seed + 1, 1, 3) * 0.3)


TURNS = {"right": 0, "up": 1, "left": 2, "down": 3}


def oriented(fn, h, w, direction, *args):
    k = TURNS[direction]
    bh, bw = (w, h) if k % 2 else (h, w)
    return tuple(np.rot90(a, k) for a in fn(bh, bw, *args))


def _weave(h, w, seed, lo, hi):
    f = stretch(noise_field(h, w, seed, 10, 14) * 0.6 + strand_noise(h, w, seed + 5) * 0.4)
    return quant(f, lo, hi), np.ones((h, w), bool)


def weave_fur(h, w, seed, lo=1, hi=6, direction="right"):
    return oriented(_weave, h, w, direction, seed, lo, hi)


def _locks(h, w, seed, hi):
    rng = np.random.default_rng(seed)
    idx = np.zeros((h, w), int)
    s = strand_noise(h, w, seed + 5)
    shade = stretch(noise_field(h, w, seed, 14, 20))
    lw, ll, step = 6, 18, 12
    spots = []
    for r, y in enumerate(range(-3, h, lw - 1)):
        for x in range(-ll, w + step, step):
            spots.append((x + (r % 2) * (step // 2) + int(rng.integers(-2, 3)), y))
    spots.sort(key=lambda p: -p[0])
    for lx, ly in spots:
        L = ll + int(rng.integers(-2, 3))
        lift = shade[min(max(ly + 2, 0), h - 1), min(max(lx + L // 2, 0), w - 1)]
        for k in range(lw):
            y = ly + k
            if not 0 <= y < h:
                continue
            edge = abs(k - (lw - 1) / 2)
            end = lx + L - int(round(edge * edge * 0.8))
            for x in range(max(lx, 0), min(end, w)):
                u = (x - lx) / max(end - lx, 1)
                v = 0.12 + 0.55 * u + 0.2 * s[y, x] + 0.25 * lift - (0.3 if k == lw - 1 else 0) - (0.15 if x - lx < 2 else 0)
                idx[y, x] = quant(np.clip(v, 0, 1), 0, hi)
    return idx, np.ones((h, w), bool)


def lock_fur(h, w, seed, hi=6, direction="right"):
    return oriented(_locks, h, w, direction, seed, hi)


def _tips(h, w, seed, hi, ragged):
    s = strand_noise(h, w, seed + 5)
    xs = np.arange(w)[None, :] / w
    f = np.clip(xs * 1.05 + (s - 0.5) * 0.35, 0, 1)
    idx = quant(f, 0, hi)
    edge = noise_field(h, 1, seed + 9, 2, 1)[:, 0]
    alpha = np.zeros((h, w), bool)
    for y in range(h):
        alpha[y, :w - 1 - int(edge[y] * ragged)] = True
    return idx, alpha


def tip_fur(h, w, seed, hi=7, ragged=7, direction="right"):
    return oriented(_tips, h, w, direction, seed, hi, ragged)


def paint(idx, alpha, pal):
    img = to_rgb(idx, pal)
    if alpha.all():
        return img
    return np.concatenate([img, alpha[..., None].astype(float)], -1)


def light_map(h, w, seed, lx=0.75, ly=0.65):
    ys, xs = np.mgrid[0:h, 0:w]
    g = 1 - (xs / max(w - 1, 1) * lx + ys / max(h - 1, 1) * ly) / (lx + ly)
    return np.clip(0.8 * g + 0.2 * noise_field(h, w, seed + 50, 10), 0, 1)


def light_tone(L, detail, n=8):
    amp = 0.35 + 0.65 * L
    return np.clip(np.round(0.6 + L * (n - 2.8) + detail * amp), 0, n - 1).astype(int)


def _voronoi(h, w, pts, sy=1.0, lean=0.0):
    ys, xs = np.mgrid[0:h, 0:w] + 0.5
    dy = (ys[..., None] - pts[:, 0]) / sy
    dx = xs[..., None] - pts[:, 1]
    d = np.sqrt(dy ** 2 + dx ** 2) - lean * dy
    order = np.argsort(d, -1)
    i1 = order[..., 0]
    d1 = np.take_along_axis(d, order[..., :1], -1)[..., 0]
    d2 = np.take_along_axis(d, order[..., 1:2], -1)[..., 0]
    return ys, xs, i1, d2 - d1


def _domed(h, w, seed, step, jitter, L):
    rng = np.random.default_rng(seed)
    pts = []
    for r, y in enumerate(np.arange(-step, h + step, step * 0.87)):
        off = (r % 2) * step / 2
        for x in np.arange(-step + off, w + step, step):
            pts.append((y + rng.uniform(-jitter, jitter), x + rng.uniform(-jitter, jitter)))
    pts = np.array(pts)
    ys, xs, i1, edge = _voronoi(h, w, pts)
    dy = (ys - pts[i1, 0]) / (step / 2)
    dx = (xs - pts[i1, 1]) / (step / 2)
    dome = -(dx * 0.7 + dy * 0.7)
    detail = np.clip(dome, -1, 1) * 1.1
    detail = np.where((dome > 0.45) & (edge > 1.6), detail + 0.6 + 1.2 * L, detail)
    detail = np.where(edge < 1.0, -2.2, detail)
    return np.where((edge >= 1.0) & (edge < 1.6), detail - 0.6, detail)


def _keeled(h, w, seed, step, sy, jitter, L):
    rng = np.random.default_rng(seed)
    pts = []
    for r, y in enumerate(np.arange(-8, h + 8, step * sy * 0.8)):
        off = (r % 2) * step / 2
        for x in np.arange(-step + off, w + step, step):
            pts.append((y + rng.uniform(-jitter, jitter), x + rng.uniform(-jitter, jitter)))
    pts = np.array(pts)
    ys, xs, i1, edge = _voronoi(h, w, pts, sy, 0.25)
    ly = (ys - pts[i1, 0]) / (step * sy / 2)
    lx = (xs - pts[i1, 1]) / (step / 2)
    detail = 0.5 - ly * 0.9 - lx * 0.3
    detail = np.where(np.abs(lx) < 0.25, detail + 0.5 + 0.8 * L, detail)
    detail = np.where(edge < 0.8, -2.3, detail)
    detail = np.where((edge >= 0.8) & (edge < 1.4) & (ly > 0), detail - 0.8, detail)
    return np.clip(detail, -2.3, 2)


def _scutes(h, w, seed):
    rng = np.random.default_rng(seed)
    detail = np.zeros((h, w))
    y = 0
    while y < h:
        ph = int(rng.integers(5, 7))
        for dy in range(ph):
            if y + dy >= h:
                break
            detail[y + dy] = -2.4 if dy == ph - 1 else 1.2 - dy * (2.0 / (ph - 2))
        y += ph
    return detail


SCALE_TURNS = {"down": 0, "right": 1, "up": 2, "left": 3}


def _turned(fn, h, w, direction, L, *args):
    k = SCALE_TURNS[direction]
    if k == 0:
        return fn(h, w, *args, L)
    bh, bw = (w, h) if k % 2 else (h, w)
    return np.rot90(fn(bh, bw, *args, np.rot90(L, -k)), k)


def domed_scales(h, w, seed, n=8, step=5.5, jitter=1.4, light=None):
    L = light_map(h, w, seed) if light is None else light
    return light_tone(L, _domed(h, w, seed, step, jitter, L), n), np.ones((h, w), bool)


def keeled_scales(h, w, seed, n=8, step=4.5, stretch_y=1.7, jitter=1.0, direction="down", light=None):
    L = light_map(h, w, seed) if light is None else light
    return light_tone(L, _turned(_keeled, h, w, direction, L, seed, step, stretch_y, jitter), n), np.ones((h, w), bool)


def belly_scutes(h, w, seed, n=8, direction="down", light=None):
    if light is None:
        light = light_map(h, w, seed, lx=0.2, ly=0.7)
        across = (w if SCALE_TURNS[direction] % 2 == 0 else h)
        u = (np.arange(across) - (across - 1) / 2) / max((across - 1) / 2, 1)
        cyl = 0.45 + 0.55 * np.cos(u * 1.35)
        light = light * (cyl[None, :] if SCALE_TURNS[direction] % 2 == 0 else cyl[:, None])
    detail = _turned(lambda bh, bw, s, L: _scutes(bh, bw, s), h, w, direction, light, seed)
    return light_tone(light, detail, n), np.ones((h, w), bool)


def mixels(parts, density=1):
    issues = []
    for i, p in enumerate(parts):
        d = np.subtract(p["to"], p["from"]) * density
        for v in d:
            if p.get("double") and abs(v) < 1e-9:
                continue
            if abs(v - round(v)) > 1e-6 or round(v) < 1:
                issues.append((i, "size", tuple(float(x) for x in np.subtract(p["to"], p["from"]))))
                break
        for face, img in p["tex"].items():
            if img is None:
                continue
            want = face_size(p["from"], p["to"], face, density)
            if tuple(img.shape[:2]) != tuple(want):
                issues.append((i, face, tuple(img.shape[:2]), tuple(want)))
    return issues


def encrusted_shell(h, w, seed, n=10, band=5, crust=0.35, light=None):
    rng = np.random.default_rng(seed)
    L = 0.4 + 0.55 * light_map(h, w, seed, lx=0.6, ly=0.8) if light is None else light
    ys, xs = np.mgrid[0:h, 0:w]
    s = (xs * 0.6 + ys + (noise_field(h, w, seed + 3, 6) - 0.5) * 3).astype(int)
    k = s % band
    d = np.where(k == 0, 1.6, np.where(k == 1, 0.7, np.where(k == band - 1, -2.0, -0.3)))
    d = d + (stretch(noise_field(h, w, seed + 4, 3)) - 0.5) * 0.4
    taken = np.zeros((h, w), bool)
    for _ in range(int(h * w / 14)):
        if h < 4 or w < 4:
            break
        y, x = int(rng.integers(0, h - 3)), int(rng.integers(0, w - 3))
        if taken[max(y - 1, 0):y + 4, max(x - 1, 0):x + 4].any():
            continue
        if rng.random() < 0.6:
            d[y, x:x + 2] = 2.6
            d[y + 1, x] = 1.4
            d[y + 1, x + 1] = 0.6
            d[y + 1, x + 2] = -1.0
            d[y + 2, x + 1:x + 3] = -2.2
        else:
            d[y:y + 2, x:x + 2] = -3.0
            d[y + 2, x:x + 2] = 0.9
        taken[y:y + 3, x:x + 3] = True
    if crust > 0:
        top = (noise_field(h, w, seed + 6, 5) > 0.6) & (ys < h * crust)
        d[top] = 2.2 + (noise_field(h, w, seed + 7, 2)[top] - 0.5)
        d[top & ~np.roll(top, 1, 0)] = -1.8
    return light_tone(L, d, n), np.ones((h, w), bool)
