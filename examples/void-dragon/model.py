import math
import os
import sys
import numpy as np

sys.path.insert(0, os.environ.get("CORE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core")))
import render
from kit import FACES, hexc, face_size, to_rgb, part, mirror, light_tone, noise_field, _voronoi


def pal(*c):
    return [hexc(x) for x in c]


VOID = pal("#040308", "#07060d", "#0b0913", "#100d1a", "#151122", "#1b162b", "#221b35", "#2a2140", "#33284c", "#3e3159")
HORN = pal("#0a0812", "#140f20", "#201831", "#2d2244", "#3c2e58", "#4d3b6d", "#604a82", "#765c98", "#8e71b0")
MEM = pal("#0e0518", "#170827", "#220c38", "#2e114b", "#3b175f", "#4a1e75", "#5b268c", "#6e30a3", "#833dba")
GLOW = pal("#3a0d6b", "#5a18a0", "#7d27d1", "#a03ff0", "#bf6cff", "#d9a3ff", "#f0d8ff")
FLESH = pal("#12061a", "#1d0a2a", "#2b103d", "#3b1752", "#4d2068")
NV = len(VOID)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def euler(R):
    b = math.asin(max(-1.0, min(1.0, R[0, 2])))
    if abs(R[0, 2]) > 0.99999:
        c = 0.0
        a = math.atan2(R[2, 1], R[1, 1])
    else:
        c = math.atan2(-R[0, 1], R[0, 0])
        a = math.atan2(-R[1, 2], R[2, 2])
    return (math.degrees(a), math.degrees(b), math.degrees(c))


def frame(V, hint):
    V = unit(V)
    h = np.asarray(hint, float)
    W = h - np.dot(h, V) * V
    if np.linalg.norm(W) < 1e-6:
        W = np.array([0.0, 0.0, 1.0]) - V[2] * V
    W = unit(W)
    U = np.cross(V, W)
    return U, V, W


def placed(O, U, V, W, size, tex, center=True):
    sx, sy, sz = size
    O = np.asarray(O, float)
    if center:
        f = (O[0] - sx / 2, O[1], O[2] - sz / 2)
        t = (O[0] + sx / 2, O[1] + sy, O[2] + sz / 2)
    else:
        f = tuple(O)
        t = (O[0] + sx, O[1] + sy, O[2] + sz)
    R = np.column_stack([U, V, W])
    return part(f, t, tex, [(tuple(O), euler(R))])


def face_light(face, h, w, seed, top=0.95, low=0.3):
    r = np.arange(h)[:, None] / max(h - 1, 1)
    c = np.arange(w)[None, :] / max(w - 1, 1)
    if face == "top":
        L = np.full((h, w), top) - 0.1 * r
    elif face == "bottom":
        L = np.full((h, w), low * 0.7)
    else:
        L = np.broadcast_to(top - (top - low) * r, (h, w)).copy()
        L = L + (0.06 * (1 - c) if face in ("front", "left") else -0.06 * c)
        if face == "back":
            L = L - 0.08
    L = L + 0.14 * (noise_field(h, w, seed, 6) - 0.5)
    return np.clip(L, 0, 1)


def plates_detail(h, w, seed, step=6.0, jitter=1.6):
    if h < 3 or w < 3:
        return np.zeros((h, w))
    rng = np.random.default_rng(seed)
    pts = []
    for r, y in enumerate(np.arange(-step, h + step, step * 0.85)):
        off = (r % 2) * step / 2
        for x in np.arange(-step + off, w + step, step):
            pts.append((y + rng.uniform(-jitter, jitter), x + rng.uniform(-jitter, jitter)))
    pts = np.array(pts)
    ys, xs, i1, edge = _voronoi(h, w, pts)
    dy = (ys - pts[i1, 0]) / (step / 2)
    dx = (xs - pts[i1, 1]) / (step / 2)
    lean = -(dx * 0.6 + dy * 0.8)
    d = np.clip(lean, -1, 1) * 0.6
    rim = (edge >= 1.0) & (edge < 2.0)
    d = np.where(rim & (lean > 0.1), d + 1.3, d)
    d = np.where(rim & (lean < -0.3), d - 0.7, d)
    return np.where(edge < 1.0, -2.2, d)


def skin_tex(f, t, seed, base=0.0, step=6.0, pal_=VOID):
    tex = {}
    n = len(pal_)
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        L = face_light(face, h, w, seed + i)
        idx = light_tone(np.clip(L * 0.85 + base, 0, 1), plates_detail(h, w, seed + i * 7, step), n)
        tex[face] = to_rgb(idx, pal_)
    return tex


def joint_tex(f, t, seed):
    tex = {}
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        L = face_light(face, h, w, seed + i) * 0.6
        rows = np.zeros((h, w))
        rows[1::2] = -1.4
        rows[::2] = 0.4
        tex[face] = to_rgb(light_tone(L, rows, NV) - 1, VOID)
    return tex


def beam(p0, p1, sx, sz, hint, seed, extra=1, tex=None, base=0.0, step=6.0):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    U, V, W = frame(p1 - p0, hint)
    L = max(1, int(math.ceil(np.linalg.norm(p1 - p0) - 1e-4)) + extra)
    O = p0 - V * extra / 2
    f = (O[0] - sx / 2, O[1], O[2] - sz / 2)
    t = (O[0] + sx / 2, O[1] + L, O[2] + sz / 2)
    tx = tex(f, t, seed) if tex else skin_tex(f, t, seed, base, step)
    return placed(O, U, V, W, (sx, L, sz), tx)


def horn_tex(f, t, seed, glow_tip=2):
    tex = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        if face in ("top", "bottom"):
            tex[face] = to_rgb(np.full((h, w), 2 if face == "top" else 1), HORN)
            continue
        r = np.arange(h)[:, None]
        along = 1 - r / max(h - 1, 1)
        idx = np.round(1.5 + along * 4.5).astype(int) + np.zeros((h, w), int)
        idx[:, -1:] -= 1
        if w > 1 and face in ("front", "left"):
            idx[:, :1] += 1
        idx[h - 2: h - 1] -= 2
        rgb = to_rgb(idx, HORN)
        a = np.ones((h, w))
        if glow_tip and face in ("front", "back", "left", "right"):
            k = min(glow_tip, h)
            gi = np.clip(np.arange(k)[::-1] + 3, 0, len(GLOW) - 1)
            rgb[:k] = np.array([GLOW[g] for g in gi])[:, None, :]
            a[:k] = 2.0
        tex[face] = np.concatenate([rgb, a[..., None]], -1)
    return tex


def sprite_card(O, U, V, cells, w, h, double=True):
    img = np.zeros((h, w, 4))
    for (x, y), (rgb, a) in cells.items():
        if 0 <= x < w and 0 <= y < h:
            img[h - 1 - y, x, :3] = rgb
            img[h - 1 - y, x, 3] = a
    W = np.cross(U, V)
    p = placed(O, unit(U), unit(V), unit(W), (w, h, 0), {"front": img}, center=False)
    p["double"] = double
    return p


def spike_cells(w, h, lean=0.0, glow=2, pal_=HORN, root=3):
    cells = {}
    for y in range(h):
        u = y / max(h - 1, 1)
        half = (w / 2) * (1 - u) + 0.5 * u
        cx = (w - 1) / 2 + lean * y
        for x in range(w):
            if abs(x - cx) <= half - 0.01 or (half < 0.75 and int(round(cx)) == x):
                side = 1 if x <= cx else -1
                tone = int(np.clip(round(root + u * 3 + side * 0.6), 0, len(pal_) - 1))
                if y >= h - glow:
                    cells[(x, y)] = (GLOW[min(len(GLOW) - 1, 3 + (y - (h - glow)))], 2.0)
                else:
                    cells[(x, y)] = (pal_[tone], 1.0)
    return cells


def crossed_spike(base, direction, w, h, seed=0, glow=2):
    d = unit(direction)
    U1, V1, W1 = frame(d, (0, 0, 1) if abs(d[2]) < 0.9 else (0, 1, 0))
    out = []
    for U in (U1, W1):
        O = np.asarray(base, float) - U * w / 2
        out.append(sprite_card(O, U, d, spike_cells(w, h, 0, glow), w, h))
    return out


def claw(base, direction, seed, length=4):
    return crossed_spike(base, direction, 2, length, seed, glow=1)


MEMREF = {}


def membrane(Wp, A, B, seed, sag=0.25, spacing=15.0, rows_glow=True, double=True, ref=None, edge=True):
    Wp, A, B = (np.asarray(v, float) for v in (Wp, A, B))
    U = unit(A - Wp)
    bb = B - Wp
    V = unit(bb - np.dot(bb, U) * U)
    ax = np.linalg.norm(A - Wp)
    bx, by = np.dot(bb, U), np.dot(bb, V)
    x0 = math.floor(min(0.0, bx)) - 1
    w = int(math.ceil(max(ax, bx) - x0)) + 1
    h = int(math.ceil(by)) + 1
    O = Wp + U * x0 - V
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:h, 0:w] + 0.5
    px, py = xs + x0, ys - 1
    a2 = np.array([ax, 0.0])
    b2 = np.array([bx, by])
    e = b2 - a2
    el = np.linalg.norm(e)
    s_ab = np.clip(((px - a2[0]) * e[0] + (py - a2[1]) * e[1]) / el ** 2, 0, 1)
    dist = (e[0] * (py - a2[1]) - e[1] * (px - a2[0])) / el
    s1 = ax * py
    s3 = by * px - bx * py
    sp_ = spacing
    nseg = int(math.ceil(ax / sp_))
    k = np.floor(px / sp_)
    u = px / sp_ - k
    rd = np.random.default_rng(seed + 7)
    depth = rd.uniform(0.18, 0.3, 64)[np.clip(k.astype(int), 0, 63)] * sp_
    teeth = np.zeros(400)
    q = 0
    rt = np.random.default_rng(seed + 11)
    while q < len(teeth):
        tw = int(rt.integers(2, 4))
        dep = rt.uniform(0.0, 0.9 if double else 1.8)
        for j in range(tw):
            if q + j < len(teeth):
                teeth[q + j] = dep * (1 - abs(j - (tw - 1) / 2) / ((tw + 1) / 2))
        q += tw
    jag = teeth[np.clip((s_ab * el).astype(int), 0, len(teeth) - 1)]
    tt = np.clip(px / max(ax, 1), 0, 1)
    half = np.where(s_ab < 0.5, s_ab * 2, s_ab * 2 - 1)
    if double:
        inward = sag * el * 0.5 * np.sin(np.pi * half) ** 0.85 + jag
    else:
        inward = sag * el * np.sin(np.pi * s_ab) + depth * np.sin(np.pi * u) ** 0.9 * np.clip((tt - 0.3) * 3, 0, 1) + jag
    mid = (a2 + b2) / 2
    ml = np.linalg.norm(mid)
    mu = mid / max(ml, 1e-6)
    along_m = px * mu[0] + py * mu[1]
    off_m = np.abs(px * mu[1] - py * mu[0])
    mid_strut = (off_m < 0.75) & (along_m > ml * 0.35) & (along_m < ml + 1) & (sag > 0)
    inside = (s1 >= -1.2 * ax) & (s3 >= -1.2 * np.hypot(bx, by)) & (dist >= inward)
    colmax = np.where(inside, py, -1).max(0, keepdims=True)
    tv = np.clip(py / np.maximum(colmax, 1), 0, 1)
    dstrut = np.minimum(u, 1 - u) * sp_
    is_strut = (dstrut < 0.6) & (k >= 1) & (k < nseg + 0.5) & (tt > 0.05) & (tv > 0.12)
    nf = 0.5 + 0.25 * np.sin(px * 0.37 + seed) * np.sin(py * 0.29 + seed * 0.7) + 0.25 * np.sin(py * 0.53 + px * 0.11 + seed * 2)
    L = 0.78 - 0.3 * tv ** 1.6 + 0.16 * (nf - 0.5)
    band = inside & (dist < inward + 1.5)
    if edge:
        L = np.where(band, L - 0.1, L)
    idx = np.clip(np.round(L * 8), 0, len(MEM) - 1).astype(int)
    is_strut = np.zeros_like(is_strut)
    rgb = to_rgb(np.clip(idx, 0, len(MEM) - 1), MEM)
    alpha = inside * 2.0
    if rows_glow:
        lvl = np.zeros((h, w))
        for kk in range(nseg + 1):
            rng = np.random.default_rng(seed * 100 + kk)
            for f_i in range(2 if rng.random() < 0.6 else 1):
                uc = rng.uniform(0.38, 0.62) if f_i == 0 else rng.choice([0.25, 0.75])
                t0, t1 = rng.uniform(0.12, 0.25), rng.uniform(0.68, 0.88)
                wmax = rng.uniform(2.0, 3.0) * (1 if f_i == 0 else 0.7)
                ph = rng.uniform(0, 6.28)
                tb = rng.uniform(0.35, 0.5)
                bdir = rng.choice([-1, 1])
                sel = k == kk
                tn = np.clip((tv - t0) / (t1 - t0), 0, 1)
                prof = np.where((tv > t0) & (tv < t1), np.sin(np.pi * np.clip(tn * 0.8 + 0.2, 0, 1)) ** 0.6 * (1 - 0.55 * tn), 0)
                ucen = uc + 0.07 * np.sin(tv * 9 + ph)
                d = np.abs(u - ucen) * sp_
                wd = wmax * prof
                lv = np.where(d < wd * 0.4, 3, np.where(d < wd, 2, np.where(d < wd + 1.0, 1, 0)))
                tbn = np.clip((tv - tb) / (t1 - tb), 0, 1)
                bprof = np.where((tv > tb) & (tv < t1 - 0.04), np.sin(np.pi * np.clip(tbn * 0.8 + 0.2, 0, 1)) ** 0.7 * 0.75 * (1 - 0.5 * tbn), 0)
                bc = ucen + bdir * 0.24 * tbn
                bd = np.abs(u - bc) * sp_
                bw = wmax * 0.6 * bprof
                lv = np.maximum(lv, np.where(bd < bw * 0.4, 3, np.where(bd < bw, 2, np.where(bd < bw + 1.0, 1, 0))))
                lvl = np.where(sel, np.maximum(lvl, lv), lvl)
        lvl = np.where(inside & ~is_strut & (py > 1.0), lvl, 0)
        cols = {1: to_rgb(np.full((h, w), 1), GLOW) * 0.55 + rgb * 0.45, 2: to_rgb(np.full((h, w), 3), GLOW), 3: to_rgb(np.full((h, w), 5), GLOW)}
        for lv_, c_ in cols.items():
            rgb = np.where((lvl == lv_)[..., None], c_, rgb)
    if ref is not None:
        if seed not in MEMREF:
            MEMREF[seed] = membrane(*ref, seed, sag, spacing, rows_glow, double, edge=False)
        rp = MEMREF[seed]
        rimg = rp["tex"]["front"][::-1]
        dx = int(round(x0 - rp["x0"]))
        rr, cc = np.mgrid[0:h, 0:w]
        cr = cc + dx
        ok = (rr < rimg.shape[0]) & (cr >= 0) & (cr < rimg.shape[1])
        src = rimg[np.clip(rr, 0, rimg.shape[0] - 1), np.clip(cr, 0, rimg.shape[1] - 1), :3]
        rgb = np.where(ok[..., None], src, rgb)
        if edge:
            rgb = np.where((band & ~(rimg[np.clip(rr, 0, rimg.shape[0] - 1), np.clip(cr, 0, rimg.shape[1] - 1), 3] > 1.5) | band)[..., None] & (rgb.max(-1, keepdims=True) < 0.75), rgb * 0.85, rgb)
    img = np.concatenate([rgb, alpha[..., None]], -1)[::-1]
    Wn = np.cross(U, V)
    p = placed(O, U, V, Wn, (w, h, 0), {"front": img}, center=False)
    p["double"] = True
    p["x0"] = x0
    return p


def terrace_detail(h, w, seed, lines=2):
    d = np.zeros((h, w))
    if h < 3 or w < 3:
        return d
    rng = np.random.default_rng(seed)
    region = np.zeros((h, w), int)
    starts = sorted(rng.uniform(0.25, 0.85, lines) * h)
    for k, y0 in enumerate(starts):
        y = y0
        slope = rng.uniform(-0.5, 0.5)
        x = 0
        ys = np.zeros(w)
        while x < w:
            run = int(rng.integers(2, 5))
            for j in range(run):
                if x + j < w:
                    ys[x + j] = y
            x += run
            y += np.sign(slope + rng.normal(0, 0.35)) * (1 if rng.random() < 0.7 else 0)
            y = np.clip(y, 1, h - 2)
        rows = np.arange(h)[:, None]
        yi = np.round(ys).astype(int)[None, :]
        region += (rows > yi).astype(int)
        line = rows == yi
        d = np.where(line, -2.2, d)
        up = rows == yi - 1
        d = np.where(up & (d > -2), d + 0.8, d)
    d = np.where(d > -2, d - 0.75 * region + 0.5, d)
    return d


def terrace_tex(f, t, seed, base=0.15, pal_=VOID, glow=None):
    tex = {}
    n = len(pal_)
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        L = face_light(face, h, w, seed + i, top=1.0, low=0.4)
        lines = 1 if min(h, w) < 6 else 2
        det = terrace_detail(h, w, seed * 3 + i, lines)
        if h > w * 2:
            det = terrace_detail(w, h, seed * 3 + i, lines).T
        tex[face] = to_rgb(light_tone(np.clip(L * 0.8 + base, 0, 1), det, n), pal_)
    return tex


def stripe_tex(f, t, seed, base=0.1, faces=("top",), dash=3):
    tex = terrace_tex(f, t, seed, base + 0.1)
    for face in faces:
        img = tex[face]
        h, w = img.shape[:2]
        a = np.ones((h, w))
        col = w // 2 if face in ("top", "bottom") else 0
        rows = range(1, h - 1)
        for r in rows:
            if r % (dash + 1) != dash:
                img[r, col] = GLOW[4 if r % (dash + 1) else 3]
                a[r, col] = 2.0
        tex[face] = np.concatenate([img, a[..., None]], -1)
    return tex


def eye_part(f, t):
    etex = {k: to_rgb(np.full(face_size(f, t, k), 0), VOID) for k in FACES}
    eh, ew = face_size(f, t, "right")
    W_, P_, K_ = (1.0, 0.96, 1.0), GLOW[5], VOID[0]
    pattern = [[K_, K_, W_, W_, P_, K_],
               [P_, W_, W_, W_, K_, K_],
               [K_, K_, K_, K_, K_, K_]]
    eimg = np.zeros((eh, ew, 4))
    for r in range(eh):
        for c in range(ew):
            col = pattern[r][c]
            eimg[r, c, :3] = col
            eimg[r, c, 3] = 1.0 if col is K_ else 2.0
    etex["right"] = eimg
    return part(f, t, etex)


BK = 1.35
BPIV = np.array([0.0, 44.0, 0.0])


def B(v):
    return BPIV + BK * (np.asarray(v, float) - BPIV)


def bsz(v):
    return max(1, int(round(v * BK)))


def bbeam(p0, p1, sx, sz, hint, seed, **kw):
    return beam(B(p0), B(p1), bsz(sx), bsz(sz), hint, seed, **kw)


def head_parts():
    H = B(np.array([0.0, 80.0, 20.5])) - np.array([0.0, 8.0, 2.5])
    tr = [(tuple(H + np.array([0, 8.0, 4.0])), (10, 0, 0))]
    jaw_piv = H + np.array([0, 3.5, 2.0])
    jaw_tr = [(tuple(jaw_piv), (15, 0, 0))] + tr
    P = lambda x, y, z: H + np.array([x, y, z], float)
    side, center, jaw = [], [], []

    def bm(p0, p1, sx, sz, seed, hint=(0, 1, 0), tex=None, base=0.0, extra=1):
        if tex is None:
            tex = lambda f, t, s: terrace_tex(f, t, s, 0.18 + base)
        return beam(p0, p1, sx, sz, hint, seed, extra=extra, tex=tex, base=base, step=4.5)

    striped = lambda f, t, s: stripe_tex(f, t, s, 0.12, ("front",), 2)
    f, t = tuple(P(-4.5, 3, 0)), tuple(P(4.5, 12, 9))
    center.append(part(f, t, terrace_tex(f, t, 501, 0.15)))
    center.append(bm(P(0, 12.0, 2), P(0, 4.5, 26), 5, 4, 502, base=0.12))
    side.append(bm(P(2.6, 11.0, 1), P(1.4, 5.0, 23), 3, 3, 503, base=0.08))
    side.append(bm(P(3.4, 6.0, 0), P(2.4, 4.5, 18), 4, 6, 504))
    side.append(bm(P(4.6, 8.2, 6), P(3.6, 6.4, 19), 2, 2, 505, base=0.15))
    side.append(bm(P(4.0, 12.6, 6), P(4.4, 11.4, 16), 2, 2, 506))
    side.append(bm(P(2.2, 12.5, 9), P(2.6, 16.5, -7), 3, 3, 507, hint=(0, 0, 1), tex=lambda f, t, s: glow_bar_tex(f, t, s, 0.6, 0.85)))
    side.append(bm(P(4.4, 11.0, 6), P(6.2, 12.5, -6), 3, 3, 508, hint=(0, 0, 1)))
    side.append(bm(P(5.0, 9.0, 4), P(5.6, 10.0, -11), 2, 2, 509, hint=(0, 0, 1), tex=lambda f, t, s: glow_bar_tex(f, t, s, 0.2, 0.65)))
    center.append(bm(P(0, 13.5, 7), P(0, 18.5, -8), 3, 3, 510, hint=(0, 0, 1), base=0.1))
    side.append(eye_part(tuple(P(4.0, 8.5, 9)), tuple(P(5.0, 11.5, 15))))
    for i, (z, hgt, x, th) in enumerate([(11.5, 15, 2.2, 3), (16.0, 13, 0.0, 3), (19.5, 11, 1.8, 2), (24.0, 4, 0.0, 2)]):
        top_y = 12.0 + (4.5 - 12.0) * (z - 2) / 24 + 1.0
        base = P(x, top_y, z)
        tip = base + np.array([0.9 * np.sign(x), hgt, -hgt * 0.5])
        hp = beam(base, tip, th, th, (0, 0, 1), 520 + i, tex=lambda f, t, s: horn_tex_striped(f, t, s), extra=0)
        (side if x else center).append(hp)
    jaw.append(bm(P(0, 1.5, 1), P(0, 1.5, 14), 8, 4, 530, hint=(0, 1, 0), base=-0.1))
    jaw.append(bm(P(0, 2.0, 13), P(0, 2.5, 25), 6, 3, 531, hint=(0, 1, 0), base=-0.05))
    up_a, up_b = P(0, 12.0, 2), P(0, 4.5, 26)
    Uu, Vu, Wu = frame(up_b - up_a, (0, 1, 0))
    n_up = 18
    cells = {}
    for k in range(n_up):
        if k % 2 == 0:
            hgt = 3 if k in (n_up - 2, n_up - 6, 4) else 2
            for y in range(hgt):
                cells[(k, 3 - y)] = ((1.0, 0.95, 1.0) if y < hgt - 1 else GLOW[5], 2.0)
    for sg in (1, -1):
        O = up_a + Vu * 7.5 - Wu * 5.5 + np.array([sg * 2.0, 0, 0])
        center.append(sprite_card(O, Vu, Wu, cells, n_up, 4))
    fc = {}
    for x, hgt in ((0, 4), (2, 2), (4, 4)):
        for y in range(hgt):
            fc[(x, 4 - y)] = ((1.0, 0.95, 1.0) if y < hgt - 1 else GLOW[5], 2.0)
    O = up_b + Vu * 0.1 - Wu * 6.5 - np.array([2.5, 0, 0])
    center.append(sprite_card(O, (1, 0, 0), Wu, fc, 5, 5))
    f, t = tuple(P(-2, 2.5, 6)), tuple(P(2, 4.5, 22))
    center.append(part(f, t, {k: to_rgb(np.full(face_size(f, t, k), 1), FLESH) for k in FACES}))
    lo_a, lo_b = P(0, 2.0, 13), P(0, 2.5, 25)
    Ul, Vl, Wl = frame(lo_b - lo_a, (0, 1, 0))
    lc = {}
    for k in range(12):
        if k % 2 == 1:
            hgt = 2 if k in (9, 5, 1) else 1
            for y in range(hgt):
                lc[(k, 1 + y)] = ((1.0, 0.95, 1.0) if y == hgt - 1 else GLOW[5], 2.0)
    for sg in (1, -1):
        O = lo_a + Wl * 0.5 + np.array([sg * 1.8, 0, 0])
        jaw.append(sprite_card(O, Vl, Wl, lc, 12, 3))
    lf = {}
    for x, hgt in ((0, 3), (2, 2), (4, 3)):
        for y in range(hgt):
            lf[(x, 1 + y)] = ((1.0, 0.95, 1.0) if y == hgt - 1 else GLOW[5], 2.0)
    O = lo_b + Vl * 0.1 + Wl * 0.5 - np.array([2.5, 0, 0])
    jaw.append(sprite_card(O, (1, 0, 0), Wl, lf, 5, 4))
    f, t = tuple(P(-2.5, 3.0, 4)), tuple(P(2.5, 4.0, 14))
    jaw.append(part(f, t, {k: to_rgb(np.full(face_size(f, t, k), 3), FLESH) for k in FACES}))
    out = []
    for p in center:
        p["tr"] = p["tr"] + tr
        out.append(p)
    for p in side:
        p["tr"] = p["tr"] + tr
        out += [p, mirror(p)]
    for p in jaw:
        p["tr"] = p["tr"] + jaw_tr
        p["jaw"] = tuple(jaw_piv)
        out.append(p)
    global NECK_END
    NECK_END = H + np.array([0, 8.0, 2.5])
    return out


def glow_bar_tex(f, t, seed, a0, a1):
    tex = terrace_tex(f, t, seed, 0.2)
    for face in ("front", "back", "left", "right", "top", "bottom"):
        img = tex[face]
        h, w = img.shape[:2]
        if h < 4:
            continue
        r0, r1 = int(h * (1 - a1)), int(h * (1 - a0))
        al = np.ones((h, w))
        cols = [w // 2] if w < 3 else [w // 2 - 1, w // 2]
        for r in range(r0, r1):
            gap = (r - r0) in (2,)
            for c in cols:
                if not gap:
                    edge = r in (r0, r1 - 1)
                    img[r, c] = GLOW[3 if edge else 5]
                    al[r, c] = 2.0
        for c in cols:
            for r in (r0 - 1, r1):
                if 0 <= r < h:
                    img[r, c] = GLOW[0] * 0.6 + img[r, c] * 0.4
                    al[r, c] = 2.0
        tex[face] = np.concatenate([img, al[..., None]], -1)
    return tex


def horn_tex_striped(f, t, seed):
    tex = terrace_tex(f, t, seed, 0.2, HORN)
    for face in ("front", "back", "left", "right"):
        img = tex[face]
        h, w = img.shape[:2]
        al = np.ones((h, w))
        c = w // 2
        for r in (1, 2, 4, 5):
            if r < h:
                img[r, c] = GLOW[5 if r in (1, 2) else 4]
                al[r, c] = 2.0
        for r in range(0, min(h, 7)):
            if al[r, c] < 2 and r != 3:
                img[r, c] = GLOW[1] * 0.5 + img[r, c] * 0.5
                al[r, c] = 2.0
        tex[face] = np.concatenate([img, al[..., None]], -1)
    tex["top"] = to_rgb(np.full(face_size(f, t, "top"), 6), HORN)
    return tex


def Ry(a):
    return render.rot_matrix(0, a, 0)


def Rz(a):
    return render.rot_matrix(0, 0, a)


def wing_side(wp=None):
    global REST_PANES
    rp = None
    if wp:
        if "REST_PANES" not in globals():
            wing_side(None)
        rp = REST_PANES
    wp = wp or {}
    sh_z, sh_y = wp.get("sh_z", 0.0), wp.get("sh_y", 0.0)
    fold, wr_z = wp.get("fold", 0.0), wp.get("wr_z", 0.0)
    S = B([10.0, 66.0, -3.0])
    E0 = S + np.array([8.0, 9.0, -5.0])
    W0 = S + np.array([17.0, 15.0, -7.0])
    Rsh = Ry(sh_y) @ Rz(sh_z)
    E = S + Rsh @ (E0 - S)
    Rel = Rsh @ Ry(16 * fold)
    Wr = E + Rel @ (W0 - E0)
    spread = 1 - 0.28 * fold
    rays = []
    for i, (deg, length, bend) in enumerate(((36, 112, 3.0), (4, 100, 2.0), (-31, 88, 1.0))):
        a = math.radians(4 + (deg - 4) * spread)
        d = np.array([math.cos(a), math.sin(a), -0.22])
        Rh = Rel @ Rz(wr_z * (1 + 0.3 * i)) @ Ry(22 * fold * (0.7 + 0.25 * i))
        tip = Wr + Rh @ (d * length)
        mid = Wr + Rh @ (d * length * 0.48 + np.array([0, bend, 0]))
        rays.append((mid, tip))
    hip = B([9.0, 46.0, -6.0])
    out = [beam(S, E, 8, 8, (0, 1, 0), 601, base=0.05), beam(E, Wr, 6, 6, (0, 1, 0), 602, base=0.05)]
    for i, (mid, tip) in enumerate(rays):
        th = 4 if i == 0 else 3
        out.append(beam(Wr, mid, th, th, (0, 0, 1), 610 + i, base=0.1, step=4))
        out.append(beam(mid, tip, th - 1, th - 1, (0, 0, 1), 620 + i, base=0.1, step=4))
        out += claw(tip - unit(tip - mid) * 0.5, unit(tip - mid), 630 + i, 5)
    out.append(beam(Wr + Rel @ np.array([-2.0, -2.0, 0]), Wr + Rel @ np.array([2.0, 3.0, 0]), 6, 6, (0, 0, 1), 640, base=0.15))
    out += crossed_spike(Wr + Rel @ np.array([0, 3.5, 0.5]), Rel @ np.array([0.15, 1, 0.2]), 4, 7, 641)
    tips = [t for _, t in rays]
    panes = [(Wr, tips[0], tips[1], 0.42), (Wr, tips[1], tips[2], 0.42), (Wr, tips[2], hip, 0.2), (Wr, hip, S + np.array([0, -2.0, 0]), 0.0)]
    if rp is None:
        REST_PANES = [(a_, b_, c_) for a_, b_, c_, _ in panes]
    for i, (a_, b_, c_, cv) in enumerate(panes):
        out.append(membrane(a_, b_, c_, 650 + i, sag=cv, double=i < 2, ref=rp[i] if rp else None))
    return out


def arm_side():
    global ARM_SH
    A0 = np.array([10.0, 64.0, 5.0])
    ARM_SH = B(A0)
    A1 = np.array([13.0, 55.0, 5.0])
    A2 = np.array([8.0, 61.0, 12.0])
    out = [bbeam(A0, A1, 6, 6, (0, 0, 1), 701), bbeam(A1, A2, 5, 5, (0, 0, 1), 702)]
    palm0 = A2 + np.array([0, 1.0, -0.5])
    palm1 = A2 + np.array([0, -1.0, 2.5])
    out.append(bbeam(palm0, palm1, 7, 3, (0, 1, 0), 703, base=0.1, step=4))
    for i, dx in enumerate((-2.5, 0.0, 2.5)):
        b = palm1 + np.array([dx, 0.5, -0.5])
        tip = b + np.array([dx * 0.2, -5.0, -0.5])
        out.append(bbeam(b, tip, 2, 2, (0, 0, 1), 710 + i, base=0.15, step=3))
        out += claw(B(tip), (0, -1, -0.3), 720 + i, 3)
    return out


def leg_side():
    global LEG_HIP
    H0 = np.array([9.0, 47.0, -1.0])
    LEG_HIP = B(H0)
    H1 = np.array([12.0, 36.0, 7.0])
    H2 = np.array([11.0, 23.0, 2.0])
    H3 = np.array([10.5, 15.0, 4.0])
    out = [bbeam(H0, H1, 10, 10, (0, 1, 0), 801), bbeam(H1, H2, 7, 7, (0, 0, 1), 802), bbeam(H2, H3, 5, 6, (0, 0, 1), 803)]
    for i, dx in enumerate((-2.0, 0.0, 2.0)):
        b = H3 + np.array([dx, 0.5, 1.0])
        tip = b + np.array([dx * 0.2, -5.5, 0.6])
        out.append(bbeam(b, tip, 2, 2, (0, 0, 1), 810 + i, base=0.15, step=3))
        out += claw(B(tip), (0, -1, 0.1), 820 + i, 4)
    return out


def tail():
    global TAIL_RINGS, TAIL_JOINTS
    TAIL_RINGS, TAIL_JOINTS = [], []
    out = []
    p = np.array([0.0, 45.0, -6.0])
    n = 12
    for k in range(n):
        u = k / (n - 1)
        th = int(round(13 - 8 * u))
        ang = math.radians(12 - 22 * u * u)
        d = np.array([0.0, -math.cos(ang), -math.sin(ang)])
        q = p + d * 4
        TAIL_JOINTS.append(B(p))
        n0 = len(out)
        out.append(bbeam(p, q, th, th, (0, 0, -1), 900 + k, extra=0, base=-0.05, step=5))
        jq = q + d * 1.5
        out.append(bbeam(q - d * 0.5, jq, max(1, th - 2), max(1, th - 2), (0, 0, -1), 950 + k, extra=0, tex=joint_tex))
        TAIL_RINGS.append(out[n0:])
        p = jq
    out.append(tail_fin(B(p + np.array([0, 1.0, 0]))))
    TAIL_RINGS[-1].append(out[-1])
    return out


def tail_fin(c):
    w, h = 27, 19
    cells = {}
    for y in range(h):
        for x in range(w):
            dx = abs(x - (w - 1) / 2)
            if y <= 12:
                half = 1.5 + y * 0.95
            else:
                half = 12.9 - (y - 12) * 1.8
            notch = y <= 3 and dx < 3 - y and dx > 0.6
            if dx <= half and not notch and y >= 0:
                edge = dx > half - 1.2
                if edge and y > 2:
                    cells[(x, y)] = (GLOW[3 + (y > 9)], 2.0)
                else:
                    cells[(x, y)] = (MEM[int(np.clip(3 + (y > 6) + (dx < 1.5) * 2, 0, len(MEM) - 1))], 2.0)
    O = np.asarray(c, float) + np.array([-w / 2, 0, 3.0])
    return sprite_card(O, (1, 0, 0), (0, 0, -1), cells, w, h)


def spine_spikes():
    out = []
    pts = [((0, 70, 3), 4, 4), ((0, 64, -0.5), 4, 5), ((0, 58, -3.5), 4, 4), ((0, 52, -6), 3, 4), ((0, 76, 11), 3, 3), ((0, 80, 15.5), 3, 3)]
    for (base, w, h) in pts:
        w, h = bsz(w), bsz(h)
        O = B(base) - np.array([0, w / 2, 0])
        out.append(sprite_card(O, (0, 1, 0), unit((0, 0.5, -1)), spike_cells(w, h, 0, 1, VOID, 5), w, h))
    return out


def body():
    out = [bbeam((0, 44, -3), (0, 56, 0.5), 17, 15, (0, 0, 1), 301),
           bbeam((0, 55, 0.5), (0, 69, 5), 22, 17, (0, 0, 1), 302, base=0.05)]
    out.append(bbeam((0, 68, 5), (0, 73, 10), 12, 12, (0, 0, 1), 303))
    out.append(bbeam((0, 73, 10), (0, 77, 15), 11, 11, (0, 0, 1), 304))
    out.append(bbeam((0, 77, 15), (0, 80, 20.5), 10, 10, (0, 0, 1), 305))
    return out


def shift(parts, dy):
    out = []
    for p in parts:
        q = dict(p)
        (x0, y0, z0), (x1, y1, z1) = p["from"], p["to"]
        q["from"], q["to"] = (x0, y0 + dy, z0), (x1, y1 + dy, z1)
        q["tr"] = [((a, b + dy, c), r) for (a, b, c), r in p["tr"]]
        out.append(q)
    return out


REST = {}


def tag(parts, g):
    for p in parts:
        p["grp"] = g
    return parts


def build_rest():
    parts = tag(body(), "body") + tag(spine_spikes(), "body") + tag(head_parts(), "head")
    for k, ring in enumerate(TAIL_RINGS):
        parts += tag(ring, ("tail", k))
    for fn, g in ((arm_side, "arm"), (leg_side, "leg")):
        side = fn()
        parts += tag(side, g + "R") + tag([mirror(p) for p in side], g + "L")
    return parts


def build_parts(pose=None):
    pose = pose or {}
    if "parts" not in REST:
        tail()
        REST["parts"] = build_rest()
        rest_w = wing_side()
        allp = REST["parts"] + rest_w + [mirror(p) for p in rest_w]
        REST["lo"] = render.points(allp)[:, 1].min()
    global SHIFT
    SHIFT = -REST["lo"]
    wing = wing_side(pose.get("wing", {"sh_z": pose.get("flap", 0.0)}))
    out = []
    for p in REST["parts"]:
        q = dict(p)
        q["tr"] = list(p["tr"]) + pose_tr(p["grp"], pose)
        if p.get("jaw") is not None:
            q["tr"] = list(p["tr"][:-1]) + [(p["jaw"], (pose.get("jaw", 0.0), 0, 0))] + list(p["tr"][-1:]) + pose_tr(p["grp"], pose)
        out.append(q)
    out += wing + [mirror(p) for p in wing]
    return shift(out, SHIFT + pose.get("bob", 0.0))


def pose_tr(g, pose):
    tr = []
    if isinstance(g, tuple) and g[0] == "tail":
        k = g[1]
        for j in range(min(k, len(TAIL_JOINTS) - 1), -1, -1):
            tr.append((tuple(TAIL_JOINTS[j]), (pose.get("tail_x", [0] * 20)[j], 0, pose.get("tail_z", [0] * 20)[j])))
    elif g == "head":
        tr.append((tuple(NECK_END), (pose.get("nod", 0.0), pose.get("look", 0.0), 0)))
    elif g in ("legR", "legL"):
        hip = LEG_HIP * (np.array([1, 1, 1]) if g == "legR" else np.array([-1, 1, 1]))
        tr.append((tuple(hip), (pose.get("leg" + g[-1], 0.0), 0, 0)))
    elif g in ("armR", "armL"):
        sh = ARM_SH * (np.array([1, 1, 1]) if g == "armR" else np.array([-1, 1, 1]))
        tr.append((tuple(sh), (pose.get("arm" + g[-1], 0.0), 0, 0)))
    return tr
