import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import FACES, hexc, face_size, to_rgb, part, noise_field, weave_fur, flow

D = 2

BONE = [hexc(c) for c in ("#07080c", "#10121a", "#1b1e28", "#292d39", "#3b3f4b", "#51555f", "#6b6e76", "#878990", "#a5a6a8", "#c3c2bb", "#dcd9cd", "#efebde")]
FLESH = [hexc(c) for c in ("#06040a", "#0e0914", "#181020", "#24182e", "#33223f", "#463052")]
EYE = [hexc(c) for c in ("#000000", "#040306", "#0b070b", "#17090f", "#3b1410", "#e8e2ea", "#6f6b7c", "#2a2230")]

FACE_LIGHT = {"top": 1, "front": 0, "left": 0, "right": -1, "back": -1, "bottom": -2}


def qd(v):
    lo = np.floor(v)
    fr = v - lo
    h, w = v.shape
    y, x = np.mgrid[0:h, 0:w]
    chk = (x + y) % 2 == 0
    up = (fr > 0.62) | ((fr > 0.42) & chk)
    return (lo + up).astype(int)


def fs(f, t, face):
    return face_size(f, t, face, D)


def rgba(idx, pal, glow_from=None):
    idx = np.clip(idx, 0, len(pal) - 1)
    img = np.concatenate([to_rgb(idx, pal), np.ones(idx.shape + (1,))], -1)
    if glow_from is not None:
        img[..., 3] = np.where(idx >= glow_from, 2.0, 1.0)
    return img


def hair(h, w, seed, direction):
    if h < 2 or w < 2:
        return np.zeros((h, w), int)
    idx, _ = weave_fur(h, w, seed, lo=0, hi=2, direction=direction)
    return idx - 1


def cracks(idx, rng, n, base, lo_cap=3):
    h, w = idx.shape
    for _ in range(n):
        y, x = int(rng.integers(0, h)), int(rng.integers(0, w))
        dy, dx = rng.choice([-1, 0, 1]), rng.choice([-1, 1])
        for _ in range(int(rng.integers(8, 22))):
            if not (0 <= y < h and 0 <= x < w):
                break
            idx[y, x] = min(idx[y, x], base - lo_cap)
            if y + 1 < h:
                idx[y + 1, x] = max(idx[y + 1, x], base + 1)
            if rng.random() < 0.6:
                x += dx
            else:
                y += dy if dy else rng.choice([-1, 1])
            if rng.random() < 0.15:
                dx = -dx


def crust(h, w, base, seed, hair_dir="right", n_cracks=None):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    u = x / max(w - 1, 1)
    v = y / max(h - 1, 1)
    light = 1 - (u * 0.55 + v * 0.65)
    field = base - 0.6 + 1.6 * light + 1.6 * (noise_field(h, w, seed, 7) - 0.5)
    idx = qd(field) + hair(h, w, seed + 3, hair_dir)
    shade = field < base - 0.4
    hatch = shade & ((x - y) % 3 == 0) & (noise_field(h, w, seed + 9, 4) > 0.45)
    idx = np.where(hatch, idx - 1, idx)
    cracks(idx, rng, n_cracks if n_cracks is not None else max(1, h * w // 420), base)
    return idx


def gills(h, w, base, seed):
    y, x = np.mgrid[0:h, 0:w]
    cy, cx = h * 0.5, w * 0.5
    ang = np.arctan2(y - cy, x - cx)
    r = np.hypot((y - cy) / max(h, 1), (x - cx) / max(w, 1))
    k = ang * 22 / np.pi + 0.6 * noise_field(h, w, seed, 5)
    line = (k - np.floor(k)) < 0.35
    idx = np.full((h, w), base) + np.round(1.5 * r).astype(int)
    idx = np.where(line, idx - 2, idx)
    idx[r < 0.12] = base - 3
    return idx


def hairy(h, w, base, seed, ring=True):
    y, x = np.mgrid[0:h, 0:w]
    u = x / max(w - 1, 1)
    v = y / max(h - 1, 1)
    field = base + 0.3 + 1.1 * (0.5 - u) + 0.7 * (noise_field(h, w, seed, 14, 6) - 0.5) - 0.6 * v
    idx = np.round(field).astype(int)
    if h >= 6 and w >= 2:
        idx = flow(idx, seed + 5, "down")
    if w >= 3:
        c = max(0, int(w * 0.25))
        idx[:, c] = np.maximum(idx[:, c], base + 1 - (y[:, 0] > h * 0.7))
    if ring and h >= 10:
        idx[-4] = np.maximum(idx[-4], base + 1)
        idx[-3:] = np.minimum(idx[-3:], base - 3)
        idx[0] = np.minimum(idx[0], base - 1)
        mid = h // 2
        idx[mid] -= 1
    return idx


def textured(f, t, painter, pal, base, seed, tr=(), edit=None):
    tex = {}
    for i, face in enumerate(FACES):
        h, w = fs(f, t, face)
        tex[face] = rgba(painter(h, w, base + FACE_LIGHT[face], seed + i * 7), pal)
    if edit:
        edit(tex)
    return part(f, t, tex, tr)


def rot_for(p0, p1, pv=None):
    v = np.asarray(p1, float) - np.asarray(p0, float)
    u = v / np.linalg.norm(v)
    a = -np.degrees(np.arcsin(np.clip(u[2], -1, 1)))
    c = np.degrees(np.arctan2(u[0], -u[1]))
    pv = tuple(p0 if pv is None else pv)
    return [(pv, (a, 0, 0)), (pv, (0, 0, c))], np.linalg.norm(v)


def limb(p0, p1, w, painter, pal, base, seed, top=0.0):
    tr, n = rot_for(p0, p1)
    L = max(0.5, round(n * D) / D)
    f = (p0[0] - w / 2, p0[1] - L, p0[2] - w / 2)
    t = (p0[0] + w / 2, p0[1] + top, p0[2] + w / 2)
    return textured(f, t, painter, pal, base, seed, tr)


def card(f, t, img, tr=(), axis="z"):
    texd = {"front": img, "back": img[:, ::-1]} if axis == "z" else {"right": img, "left": img[:, ::-1]}
    p = part(f, t, texd, tr)
    p["double"] = True
    return p


def spike_img(h, w, base, dark_tip=True):
    img = np.zeros((h, w, 4))
    for r in range(h):
        n = max(1, round(w * (r + 1) / h))
        if n % 2 != w % 2:
            n = min(w, n + 1)
        a = (w - n) // 2
        for c in range(a, a + n):
            g = r / max(h - 1, 1)
            tone = base + 1 - (2 * (1 - g) if dark_tip else 0) + (1 if c == a else 0) - (1 if c == a + n - 1 and n > 1 else 0)
            img[r, c, :3] = BONE[int(np.clip(round(tone), 0, len(BONE) - 1))]
            img[r, c, 3] = 1
    return img


def crossed(base_pt, hgt, wid, tr_local, base=7, down=False):
    x, y, z = base_pt
    img = spike_img(int(hgt * D), int(wid * D), base)
    if down:
        img = img[::-1]
        y0, y1 = y - hgt, y
    else:
        y0, y1 = y, y + hgt
    return [card((x - wid / 2, y0, z), (x + wid / 2, y1, z), img, tr_local),
            card((x, y0, z - wid / 2 + 0.01), (x, y1, z + wid / 2 + 0.01), img, tr_local, axis="x")]


EYES = [(-2.5, 78.0, 2.0), (2.5, 78.0, 2.0), (-7.0, 79.5, 1.0), (7.0, 79.5, 1.0),
        (-4.5, 73.0, 1.0), (4.5, 73.0, 1.0), (-8.5, 76.5, 1.0), (8.5, 76.5, 1.0)]
FACE_F, FACE_T = (-10, 70, -7), (10, 84, 6)
HEAD_TR = [((0, 68, 0), (10, 0, 0))]


def eye_tex(h, w, face):
    y, x = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2, (w - 1) / 2
    d = np.hypot(y - cy, x - cx) / (max(h, w) / 2)
    idx = np.where(d > 0.92, 3, np.where(d > 0.7, 2, np.where(d > 0.4, 1, 0)))
    if face != "front":
        img = rgba(np.full((h, w), 2 if face == "top" else 1), EYE)
        if face == "top" and w >= 4:
            img[0, 1:w - 1, :3] = EYE[6]
        return img
    img = rgba(idx, EYE)
    glow = (y > cy) & (d > 0.45) & (d < 0.88)
    img[glow, :3] = EYE[4]
    img[glow, 3] = 2
    big = w >= 6
    hl = [(1, 1), (1, 2), (2, 1)] if big else [(1, 1)]
    halo = [(1, 3), (2, 2), (3, 1)] if big else [(1, 2)]
    for yy, xx in hl:
        img[yy, xx, :3] = EYE[5]
        img[yy, xx, 3] = 2
    for yy, xx in halo:
        img[yy, xx, :3] = EYE[6]
        img[yy, xx, 3] = 2
    img[h - 2, w - 2 if big else w - 1, :3] = EYE[7]
    img[h - 2, w - 2 if big else w - 1, 3] = 2
    return img


def fang_img(flip):
    H, W = 10, 8
    img = np.zeros((H, W, 4))
    for r in range(H):
        g = r / (H - 1)
        c = int(round(g * g * (W - 1)))
        wd = 3 if r < 4 else (2 if r < 7 else 1)
        for k in range(wd):
            cc = min(c + k, W - 1)
            tone = 2 + (1 if k == wd - 1 else 0)
            if k == 0 and r < 7:
                tone = 6 if r % 3 else 5
            if r >= H - 2:
                tone = 7 + (r == H - 1)
            img[r, cc, :3] = BONE[tone]
            img[r, cc, 3] = 1
    return img[:, ::-1] if flip else img


def hang_img(L, cw, seed, tone, gap=0.15):
    rng = np.random.default_rng(seed)
    H, W = int(L * D), int(cw * D)
    img = np.zeros((H, W, 4))
    prof = noise_field(1, W, seed, 1, 3)[0]
    for x in range(W):
        if rng.random() < gap:
            continue
        n = int(np.clip(round(H * (0.5 + 0.5 * prof[x])), 2, H))
        for k in range(n):
            g = k / max(n - 1, 1)
            t = tone - 1 + round(3 * g) - (1 if k == n - 1 else 0)
            img[k, x, :3] = BONE[int(np.clip(t, 0, len(BONE) - 1))]
            img[k, x, 3] = 1
    return img


def edge_fringe(f, t, edge, tr, seed, L, ang=14, cw=3.0, tone=8, span=None, y_top=None):
    out = []
    yt = f[1] + 0.5 if y_top is None else y_top
    lo, hi = span if span else ((f[0], t[0]) if edge in ("front", "back") else (f[2], t[2]))
    a = lo
    i = 0
    while a < hi - 0.4:
        b = min(a + cw, hi)
        w = b - a
        img = hang_img(L, w, seed + i, tone)
        ln = L
        rot = ang + 4 * ((i * 7) % 3 - 1)
        if edge == "front":
            z = t[2] + 0.05 + 0.01 * i
            out.append(card((a, yt - ln, z), (b, yt, z), img, [((a, yt, z), (-rot, 0, 0))] + list(tr)))
        elif edge == "back":
            z = f[2] - 0.05 - 0.01 * i
            out.append(card((a, yt - ln, z), (b, yt, z), img, [((a, yt, z), (rot, 0, 0))] + list(tr)))
        else:
            sgn = 1 if edge == "right" else -1
            x = (t[0] if sgn > 0 else f[0]) + sgn * (0.05 + 0.01 * i)
            out.append(card((x, yt - ln, a), (x, yt, b), img, [((x, yt, a), (0, 0, sgn * rot))] + list(tr), axis="x"))
        a = b
        i += 1
    return out


def top_fur(f, t, tr, seed, L=4.0, step=2.5, cw=3.0, ang=15, tone=9):
    out = []
    yt = t[1] + 0.05
    z = t[2] - 0.5
    row = 0
    while z - L * 0.9 > f[2] - 0.5:
        a = f[0] + (cw / 2 if row % 2 else 0)
        i = 0
        while a < t[0] - 0.4:
            b = min(a + cw, t[0])
            img = hang_img(L, b - a, seed + row * 31 + i, tone, gap=0.0)
            rot = 90 + ang + 3 * ((row + i) % 3 - 1)
            zz = z + 0.01 * i
            out.append(card((a, yt - L, zz), (b, yt, zz), img, [((a, yt, zz), (rot, 0, 0))] + list(tr)))
            a = b
            i += 1
        if row % 2 and f[0] < a:
            img = hang_img(L, cw / 2, seed + row * 31 + 99, tone, gap=0.0)
            out.append(card((f[0], yt - L, z), (f[0] + cw / 2, yt, z), img, [((f[0], yt, z), (90 + ang, 0, 0))] + list(tr)))
        z -= step
        row += 1
    return out


def head(parts, pose=None):
    pose = pose or {}
    dy = pose.get("bob", 0.0)
    chel = pose.get("chel", 0.0)
    hp = []
    for s in (-1, 1):
        f = (-13, 83, -10) if s < 0 else (0, 83, -10)
        t = (0, 89, 10) if s < 0 else (13, 89, 10)

        def cap_edit(tex, s=s):
            h, w = tex["bottom"].shape[:2]
            tex["bottom"] = rgba(gills(h, w, 4, 20 + s), BONE)
        ltr = [((0, 86, 0), (0, 0, -s * 7))]
        hp.append(textured(f, t, lambda h, w, b, sd: crust(h, w, b, sd, "up" if h > 20 else "right"), BONE, 9, 10 + s * 5, ltr, cap_edit))
        hp += edge_fringe(f, t, "front", ltr, 400 + s * 20, 1.5, ang=18, tone=9)
        hp += top_fur(f, t, ltr, 700 + s * 50)
        hp += edge_fringe(f, t, "back", ltr, 440 + s * 20, 7.0, tone=8)
        f = (-25, 83.5, -8) if s < 0 else (12, 83.5, -8)
        t = (-12, 86.5, 8) if s < 0 else (25, 86.5, 8)
        wtr = [((s * 12, 85, 0), (0, 0, -s * 24)), ((0, 86, 0), (0, 0, -s * 7))]
        hp.append(textured(f, t, lambda h, w, b, sd: crust(h, w, b, sd, "up" if h > 20 else "right"), BONE, 8, 15 + s * 5, wtr, cap_edit))
        hp += edge_fringe(f, t, "front", wtr, 480 + s * 20, 6.0, tone=9)
        hp += top_fur(f, t, wtr, 800 + s * 50, tone=8)
        hp += edge_fringe(f, t, "back", wtr, 520 + s * 20, 7.0, tone=8)
        hp += edge_fringe(f, t, "right" if s > 0 else "left", wtr, 560 + s * 20, 8.0, ang=10, tone=8)
        fl = (-22, 79, -8) if s < 0 else (8, 79, -8)
        tl = (-8, 82, 6) if s < 0 else (22, 82, 6)
        hp.append(textured(fl, tl, lambda h, w, b, sd: crust(h, w, b, sd, "left"), BONE, 7, 30 + s * 5, [((s * 8, 80.5, 0), (0, 0, s * 22))]))

    def face_edit(tex):
        img = tex["front"]
        h, w = img.shape[:2]
        idx = crust(h, w, 9, 41, "down", n_cracks=3)
        y, x = np.mgrid[0:h, 0:w]
        for ex, ey, r in EYES:
            cx = (ex - FACE_F[0]) * D - 0.5
            cy = (FACE_T[1] - ey) * D - 0.5
            dd = np.hypot(x - cx, y - cy)
            rr = r * D
            idx = np.where(dd < rr + 1.6, np.minimum(idx, 3), idx)
            lip = (dd >= rr + 1.6) & (dd < rr + 2.6) & (y < cy)
            idx = np.where(lip, np.maximum(idx, 10), idx)
            under = (dd >= rr + 1.6) & (dd < rr + 3.0) & (y > cy)
            idx = np.where(under, np.minimum(idx, 6), idx)
        out = rgba(idx, BONE)
        for ex, ey, r in EYES:
            c0 = int(round((ex - r - FACE_F[0]) * D))
            c1 = int(round((ex + r - FACE_F[0]) * D))
            r0 = int(round((FACE_T[1] - ey - r) * D))
            r1 = int(round((FACE_T[1] - ey + r) * D))
            out[r0:r1, c0:c1, 3] = 0
        tex["front"] = out
        bt = tex["bottom"]
        bh, bw = bt.shape[:2]
        yy, xx = np.mgrid[0:bh, 0:bw]
        mouth = (np.abs(xx - (bw - 1) / 2) < 3) & (yy > bh * 0.45)
        bt[mouth, :3] = to_rgb(np.clip(5 - (yy[mouth] - int(bh * 0.45)) // 3, 1, 5), FLESH)
    hp.append(textured(FACE_F, FACE_T, lambda h, w, b, sd: crust(h, w, b, sd, "down"), BONE, 8, 40, (), face_edit))
    for k, yt in enumerate((83.0, 80.0, 77.0, 74.0)):
        for side in ("left", "right"):
            hp += edge_fringe(FACE_F, FACE_T, side, (), 600 + k * 10 + (side == "left"), 4.0, ang=24, tone=7, span=(-6.0 + 1.5 * (k % 2), 5.0), y_top=yt)

    for sgn in (-1, 1):
        f = (-5, 65, 0.5) if sgn < 0 else (0.5, 65, 0.5)
        t = (-0.5, 70, 5.5) if sgn < 0 else (5, 70, 5.5)
        ctr = [((sgn * 2.75, 70, 3), (-16, -sgn * 10, sgn * (8 + chel)))]
        hp.append(textured(f, t, lambda h, w, b, sd: hairy(h, w, b, sd, ring=False), BONE, 6, 300 + sgn, ctr))
        f2 = (-4.5, 61.5, 1.5) if sgn < 0 else (1, 61.5, 1.5)
        t2 = (-1, 65, 5) if sgn < 0 else (4.5, 65, 5)
        hp.append(textured(f2, t2, lambda h, w, b, sd: hairy(h, w, b, sd, ring=False) - (np.arange(h)[:, None] > h * 0.6), BONE, 5, 305 + sgn, ctr))
        outer = "left" if sgn < 0 else "right"
        for k, yt in enumerate((69.5, 67.5)):
            hp += edge_fringe(f, t, "front", ctr, 310 + k * 4 + sgn, 2.5, ang=18, tone=7, span=(f[0] + 0.5 * (k % 2), t[0]), y_top=yt)
            hp += edge_fringe(f, t, outer, ctr, 330 + k * 4 + sgn, 3.0, ang=22, tone=7, y_top=yt)
        hp += edge_fringe(f2, t2, "front", ctr, 350 + sgn, 2.0, ang=16, tone=6, y_top=64.5)
        hp += edge_fringe(f2, t2, outer, ctr, 360 + sgn, 2.5, ang=22, tone=6, y_top=64.5)
        ix = -1 if sgn < 0 else 1
        fx0, fx1 = (ix - 4, ix) if sgn < 0 else (ix, ix + 4)
        hp.append(card((fx0, 57, 4.0), (fx1, 62, 4.0), fang_img(sgn > 0), ctr))
        hp.append(card((ix - sgn * 2, 57, 1.5), (ix - sgn * 2, 62, 5.5), fang_img(False), ctr, axis="x"))

    zf = FACE_T[2]
    for i, (ex, ey, r) in enumerate(EYES):
        f = (ex - r, ey - r, zf - 2)
        t = (ex + r, ey + r, zf - 1)
        tex = {face: eye_tex(*fs(f, t, face), face) for face in FACES}
        hp.append(part(f, t, tex))
        n = int(2 * r * D)
        walls = [
            ((ex - r, ey + r, zf - 1), (ex + r, ey + r, zf), "top", 2),
            ((ex - r, ey - r, zf - 1), (ex + r, ey - r, zf), "top", 5),
            ((ex - r, ey - r, zf - 1), (ex - r, ey + r, zf), "right", 3),
            ((ex + r, ey - r, zf - 1), (ex + r, ey + r, zf), "right", 3),
        ]
        for wf, wt, face, tone in walls:
            hh, ww = fs(wf, wt, face)
            yy, xx = np.mgrid[0:hh, 0:ww]
            idx = tone + ((xx + yy) % 3 == 0) - (yy == 0 if face == "top" else xx == 0)
            img = rgba(idx, BONE)
            opp = {"top": "bottom", "right": "left"}[face]
            wp = part(wf, wt, {face: img, opp: img})
            wp["double"] = True
            hp.append(wp)
    htr = [((0, 68, 0), (10 + pose.get("pitch", 0.0), 0, pose.get("roll", 0.0)))]
    for p in hp:
        p["tr"] = list(p["tr"]) + htr
    parts += shift(hp, dy)


def shift(group, dy):
    for p in group:
        p["from"] = (p["from"][0], p["from"][1] + dy, p["from"][2])
        p["to"] = (p["to"][0], p["to"][1] + dy, p["to"][2])
        p["tr"] = [((pv[0], pv[1] + dy, pv[2]), r) for pv, r in p["tr"]]
    return group


def ik_knee(hip, knee0, ankle0, hip1, ankle1):
    hip, knee0, ankle0, hip1, ankle1 = (np.asarray(v, float) for v in (hip, knee0, ankle0, hip1, ankle1))
    lf = np.linalg.norm(knee0 - hip)
    lt = np.linalg.norm(ankle0 - knee0)
    v = ankle1 - hip1
    d = min(np.linalg.norm(v), lf + lt - 1e-3)
    u = v / np.linalg.norm(v)
    b = (knee0 - hip) - np.dot(knee0 - hip, u) * u
    b /= np.linalg.norm(b)
    a = (lf * lf - lt * lt + d * d) / (2 * d)
    h = np.sqrt(max(lf * lf - a * a, 0.0))
    return tuple(hip1 + a * u + h * b)


def rot_x(p, pivot, deg):
    p, pv = np.asarray(p, float), np.asarray(pivot, float)
    c, s_ = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    q = p - pv
    return tuple(pv + np.array([q[0], q[1] * c - q[2] * s_, q[1] * s_ + q[2] * c]))


def hair_img(L, cw, rng, tone, span=3.0):
    H, W = int(L * D), int(cw * D)
    img = np.zeros((H, W, 4))
    for x in range(W):
        if rng.random() < 0.2:
            continue
        n = int(rng.integers(H // 2, H + 1))
        bend = int(rng.choice([-1, 0, 0, 1]))
        for k in range(n):
            xx = x + (bend if k >= n * 2 // 3 else 0)
            if not 0 <= xx < W:
                continue
            g = k / max(n - 1, 1)
            t = tone - 1 + round(span * g)
            img[k, xx, :3] = BONE[int(np.clip(t, 0, len(BONE) - 1))]
            img[k, xx, 3] = 1
    return img


def setae(p0, p1, w, seed, step=3.0, L=4.5, cw=2.0, ang=22, tone=8):
    rng = np.random.default_rng(seed)
    tr, n = rot_for(p0, p1)
    length = round(n * D) / D
    x0, y0, z0 = p0
    out = []
    e = w / 2 + 0.05
    for i, side in enumerate(("front", "right", "back", "left")):
        y = y0 - 0.5 - (step / 2 if i % 2 else 0)
        j = 0
        while y - L > y0 - length + 1.0:
            off = round(rng.uniform(-0.5, 0.5) * 2) / 2
            a = ang + rng.uniform(-6, 6)
            img = hair_img(L, cw, rng, tone, 1.2 if side in ("front", "back") else 3.0)
            dz = 0.01 * j
            if side == "front":
                bz = z0 + e + dz
                out.append(card((x0 + off - cw / 2, y - L, bz), (x0 + off + cw / 2, y, bz), img, [((x0, y, bz), (-a, 0, 0))] + tr))
            elif side == "back":
                bz = z0 - e - dz
                out.append(card((x0 + off - cw / 2, y - L, bz), (x0 + off + cw / 2, y, bz), img, [((x0, y, bz), (a, 0, 0))] + tr))
            else:
                sgn = 1 if side == "right" else -1
                bx = x0 + sgn * (e + dz)
                out.append(card((bx, y - L, z0 + off - cw / 2), (bx, y, z0 + off + cw / 2), img, [((bx, y, z0), (0, 0, sgn * a))] + tr, axis="x"))
            y -= step
            j += 1
    return out


def leg(parts, hip, knee, ankle, foot, seed):
    parts.append(limb(hip, knee, 2.5, hairy, BONE, 8, seed))
    parts += setae(hip, knee, 2.5, seed + 50)
    parts += setae(knee, ankle, 2, seed + 51, L=4.0)
    parts += setae(ankle, foot, 1.5, seed + 52, step=2.5, L=3.0, cw=1.5)
    tr, _ = rot_for(hip, knee, knee)
    kx, ky, kz = knee
    parts.append(textured((kx - 1.5, ky - 1.5, kz - 1.5), (kx + 1.5, ky + 1.5, kz + 1.5), lambda h, w, b, sd: hairy(h, w, b, sd, ring=False), BONE, 7, seed + 1, tr))
    parts.append(limb(knee, ankle, 2, hairy, BONE, 8, seed + 2, top=0.5))
    parts.append(limb(ankle, foot, 1.5, hairy, BONE, 7, seed + 3, top=0.5))
    parts += crossed(foot, 3, 1.5, [], base=6, down=True)


def arm(parts, sh, el, wr, hand_end, seed, side):
    parts.append(limb(sh, el, 2.5, hairy, BONE, 8, seed))
    parts += setae(sh, el, 2.5, seed + 50)
    parts += setae(el, wr, 2, seed + 51, L=4.0)
    parts += setae(wr, hand_end, 1.5, seed + 52, step=2.5, L=3.0, cw=1.5)
    ex, ey, ez = el
    tr, _ = rot_for(sh, el, el)
    parts.append(textured((ex - 1.5, ey - 1.5, ez - 1.5), (ex + 1.5, ey + 1.5, ez + 1.5), lambda h, w, b, sd: hairy(h, w, b, sd, ring=False), BONE, 7, seed + 1, tr))
    parts += crossed((ex, ey, ez), 3, 2, [((ex, ey, ez), (0, 0, -side * 90))], base=8)
    parts.append(limb(el, wr, 2, hairy, BONE, 8, seed + 2, top=0.5))
    parts.append(limb(wr, hand_end, 1.5, hairy, BONE, 8, seed + 3, top=0.5))
    hx, hy, hz = hand_end
    img = np.zeros((18, 9, 4))
    for i, c in enumerate((1, 3, 5, 7)):
        ln = (14, 17, 16, 12)[i]
        for r in range(ln):
            g = r / ln
            tone = 9 - int(4 * g)
            if r in (5, 10):
                tone = 4
            cc = c + (1 if r > ln - 4 and c < 4 else 0) - (1 if r > ln - 4 and c > 4 else 0)
            img[r, cc, :3] = BONE[tone]
            img[r, cc, 3] = 1
            if r < ln - 6:
                img[r, cc + 1 if cc + 1 < 9 else cc, :3] = BONE[max(tone - 3, 0)]
                img[r, cc + 1 if cc + 1 < 9 else cc, 3] = 1
    htr, _ = rot_for(wr, hand_end)
    parts.append(card((hx - 2.25, hy - 9, hz), (hx + 2.25, hy, hz), img, [((hx, hy, hz), (-15, 0, 0))]))
    parts.append(card((hx, hy - 9, hz - 2.25), (hx, hy, hz + 2.25), img, [((hx, hy, hz), (0, 0, side * 10))], axis="x"))


LEGS = [((-7, 67, 1), (-29, 74, 4), (-31, 32, 8), (-22, 3, 10), 100),
        ((7, 67, 1), (30, 72, 3), (32, 30, 7), (23, 3, 9), 120),
        ((-7, 67, -4), (-27, 72, -10), (-28, 30, -18), (-19, 3, -22), 180),
        ((7, 67, -4), (26, 73, -11), (29, 31, -19), (20, 3, -23), 200)]
ARMS = [((-8, 68, 2), (-20, 61, 6), (-6, 55, 9), (-4, 39, 10), 140, -1),
        ((8, 68, 2), (21, 57, 6), (6, 52, 9), (6, 37, 10), 160, 1)]


def build_parts(pose=None):
    pose = pose or {}
    dy = pose.get("bob", 0.0)
    lifts = pose.get("lift", {})
    sway = pose.get("arm", (0.0, 0.0))
    parts = []
    for i, (hip, knee, ankle, foot, seed) in enumerate(LEGS):
        lv = np.asarray(lifts.get(i, (0.0, 0.0, 0.0)), float)
        hip1 = (hip[0], hip[1] + dy, hip[2])
        ankle1 = tuple(np.asarray(ankle, float) + lv)
        foot1 = tuple(np.asarray(foot, float) + lv)
        knee1 = ik_knee(hip, knee, ankle, hip1, ankle1)
        leg(parts, hip1, knee1, ankle1, foot1, seed)
    for j, (sh, el, wr, he, seed, side) in enumerate(ARMS):
        sh1 = (sh[0], sh[1] + dy, sh[2])
        pts = [rot_x((p[0], p[1] + dy, p[2]), sh1, sway[j]) for p in (el, wr, he)]
        arm(parts, sh1, *pts, seed, side)
    head(parts, pose)
    return parts
