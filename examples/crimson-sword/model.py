import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import FACES, hexc, face_size, to_rgb, part, mirror

RED = [hexc(c) for c in ("#2e1a2e", "#502450", "#69243f", "#81274b", "#9f2440", "#c81d37", "#ff1600", "#ff5f5f", "#ffb6b6")]
METAL = [hexc(c) for c in ("#000205", "#151517", "#25293f", "#2a3e59", "#2a4c7b", "#2a6c8f", "#278fc6", "#85d4ff", "#d8f2ff")]

SHINE = [None]


def shine_at(y, x=0.0):
    s = SHINE[0]
    if s is None:
        return 0
    d = abs(y - (28 + s * 80) + 0.7 * x)
    return 2 if d < 1.6 else (1 if d < 3.5 else 0)


FACE_LIGHT = {"top": 1, "front": 0, "left": 0, "right": -1, "back": -1, "bottom": -2}


def glow(idx, pal, at=7):
    idx = np.clip(idx, 0, len(pal) - 1)
    img = np.concatenate([to_rgb(idx, pal), np.ones(idx.shape + (1,))], -1)
    img[..., 3] = np.where(idx >= at, 2.0, 1.0)
    return img


def crystal(h, w, base, seed=0, period=5):
    y, x = np.mgrid[0:h, 0:w]
    cx = (w - 1) / 2
    lit = np.round(1.2 - 2.4 * y / max(h - 1, 1) - 1.2 * x / max(w - 1, 1) + 0.6).astype(int)
    k = np.floor((y + 0.8 * np.abs(x - cx) + seed) / (period + 1)).astype(int)
    steps = np.array([0, 1, 0, -1, 0, 1])
    idx = base + lit + steps[k % len(steps)]
    edge = np.zeros_like(k, bool)
    edge[1:] = k[1:] != k[:-1]
    idx = np.where(edge & (x <= cx), idx + 2, idx)
    idx = np.where(edge & (x > cx), idx - 1, idx)
    spark = edge & (x <= cx) & (lit >= 1) & (k % 2 == 0)
    idx = np.where(spark, 8, idx)
    below = np.zeros_like(spark)
    below[1:] = spark[:-1]
    idx = np.where(below & (x <= cx), np.maximum(idx, 7), idx)
    return idx


def sharp_card(rows, pal, base):
    h = len(rows)
    w = max(r[1] for r in rows) + 1
    idx = crystal(h, w, base, 2)
    img = np.zeros((h, w, 4))
    for r, (a, b) in enumerate(rows):
        for c in range(a, b + 1):
            v = idx[r, c]
            if c == a:
                v += 2
            elif c == b:
                v = max(v, 6)
            v = int(np.clip(v, 0, len(pal) - 1))
            img[r, c, :3] = pal[v]
            img[r, c, 3] = 2.0 if v >= 7 else 1.0
    return img


def blade_rows():
    W = 13
    c = 6
    spans = []
    for n in (1, 1, 1, 3, 3, 3, 5, 5, 7, 7):
        spans.append((c - n // 2, c + n // 2))
    spans += [(c - 3, c + 3)] * 26
    spans += [(c - 4, c + 4)] * 13
    spans += [(c - 4, c + 4)] * 6
    spans += [(c - 5, c + 5)] * 2
    for k in range(8):
        spans.append(("fang", k))
    rows = []
    for s in spans:
        if s[0] == "fang":
            k = s[1]
            a = min(W - 1, k // 2 + 0)
            rows.append((0, W - 1) if k == 0 else (a, W - 1 - a))
        else:
            rows.append(s)
    return rows


def blade_card():
    rows = blade_rows()
    h = len(rows)
    W = 13
    c0 = W // 2
    cr = crystal(h, W, 0, 2)
    img = np.zeros((h, W, 4))
    dim_from = h - 26
    for r, (a, b) in enumerate(rows):
        for c in range(a, b + 1):
            if c < c0:
                v = 4 + cr[r, c]
            elif c > c0:
                v = 2 + cr[r, c] - (1 if c == c0 + 1 else 0)
            else:
                v = 8 if r < dim_from else 7 - (r - dim_from) // 9
            if c == a and c != c0:
                v = max(v + 2, 6)
            elif c == b and c != c0:
                v = 6 if r > h * 0.55 else v - 1
            g = shine_at(98 - r, c - c0)
            v = 8 if g == 2 else (max(v + 2, 6) if g == 1 else v)
            v = int(np.clip(v, 0, len(RED) - 1))
            img[r, c, :3] = RED[v]
            img[r, c, 3] = 2.0 if v >= 7 else 1.0
    for r in range(h - 8, h):
        k = r - (h - 8)
        if k > 1:
            img[r, 4 - k // 3 + 1:9 + k // 3 - 1, 3] = 0
    top = 98
    p = part((-6.5, top - h, 0), (6.5, top, 0), {"front": img, "back": img[:, ::-1]})
    p["double"] = True
    return p


def tube(h, w, base, seed=0, ring=3, lit_col=0):
    y, x = np.mgrid[0:h, 0:w]
    idx = np.full((h, w), base)
    if w > 1:
        idx[:, -1 if lit_col == 0 else 0] -= 1
        idx[:, lit_col] += 2
    rng = np.random.default_rng(seed)
    pos = int(rng.integers(1, ring + 1))
    while pos < h:
        idx[pos] -= 1
        if w > 1:
            idx[pos, lit_col] = base + 1
        pos += ring + int(rng.integers(1, 3))
    return idx


def rod(p0, p1, th, base, seed, pal=METAL, ring=3, extra=1):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = max(1, int(np.ceil(np.linalg.norm(d))) + extra)
    u = d / np.linalg.norm(d)
    phi = np.degrees(np.arccos(np.clip(u[1], -1, 1)))
    beta = np.degrees(np.arctan2(-u[2], u[0])) if np.hypot(u[0], u[2]) > 1e-6 else 0
    h = th / 2
    f = (p0[0] - h, p0[1] - extra / 2, p0[2] - h)
    t = (p0[0] + h, p0[1] - extra / 2 + L, p0[2] + h)
    tex = {}
    for face in FACES:
        fh, fw = face_size(f, t, face)
        b = base + FACE_LIGHT[face]
        if face in ("top", "bottom"):
            tex[face] = to_rgb(np.full((fh, fw), b - 1) + np.eye(fh, fw, dtype=int), pal)
        else:
            tex[face] = to_rgb(tube(fh, fw, b, seed, ring, 0 if face in ("front", "left") else fw - 1), pal)
    pv = tuple(p0)
    return part(f, t, tex, [(pv, (0, 0, -phi)), (pv, (0, beta, 0))])


def chain_rods(pts, ths, base, seed):
    out = []
    for i in range(len(pts) - 1):
        out.append(rod(pts[i], pts[i + 1], ths[i], base - (1 if ths[i] < 2 else 0), seed + i * 5))
    return out


def plate(h, w, base, rings=(), center=None, seed=0):
    y, x = np.mgrid[0:h, 0:w]
    lit = np.round(0.9 - 1.6 * y / max(h - 1, 1) - 0.8 * x / max(w - 1, 1) + 0.4).astype(int)
    idx = base + lit
    cy, cx = center if center else ((h - 1) / 2, (w - 1) / 2)
    dist = np.hypot(y - cy, x - cx)
    ang = np.arctan2(y - cy, x - cx)
    for R in rings:
        band = np.abs(dist - R) < 0.55
        idx = np.where(band & (y < cy), idx + 1, idx)
        idx = np.where(band & (y >= cy), idx - 1, idx)
    if h >= 4 and w >= 8:
        swirl = np.abs(((dist * 0.9 + ang * 1.2 + seed) % 4.5) - 2.25) < 0.3
        far = dist > (max(rings) + 1 if rings else 1.5)
        idx = np.where(swirl & far, idx - 1, idx)
        lip = np.zeros_like(swirl)
        lip[1:] = (swirl & far)[:-1]

        for ry, rx in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
            yy, xx = min(max(ry, 1), h - 2), min(max(rx, 1), w - 2)
            idx[yy, xx] = base + 3
            if yy + 1 < h:
                idx[yy + 1, xx] = base - 2
    return idx


def plate_part(f, t, base, rings=(), tr=(), centers=None):
    tex = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        c = centers.get(face) if centers else None
        r = rings if face in ("front", "back") else ()
        tex[face] = to_rgb(plate(h, w, base + FACE_LIGHT[face], r, c, FACES.index(face)), METAL)
    return part(f, t, tex, tr)


def guard(parts):
    parts.append(plate_part((-6, 28.5, -2.5), (6, 33.5, 2.5), 4, (1.5, 3.2, 4.8), centers={"front": (2, 5.5), "back": (2, 5.5)}))
    parts.append(plate_part((-3, 32, -2), (3, 38, 2), 4, (1.2, 2.6), [((0, 35, 0), (0, 0, 45))]))
    parts.append(plate_part((-3, 22.5, -2), (3, 28.5, 2), 3, (1.2, 2.6), [((0, 25.5, 0), (0, 0, 45))]))
    parts += crossbar()


def guard_side(side):
    horn = [(5, 30.5, 0), (9, 30, 0), (11.5, 31.2, 0), (13, 33.5, 0), (13.2, 36.5, 0), (12.5, 39.5, 0)]
    side += chain_rods(horn, (3, 3, 3, 2, 2), 4, 11)
    side.append(horn_tip([((12.5, 39.5, 0), (0, 0, 10))]))
    side.append(curl_card())
    side += thorn((13.6, 34.5, 0), -75)
    side += thorn((11, 31.6, 0), -40)
    side += shard((1.5, 8, 0), 3, 3, -120, 0, tone=3)


def line_sprite(cells, w, h, pal, base):
    img = np.zeros((h, w, 4))
    occ = np.zeros((h, w), bool)
    for x, y in cells:
        occ[y, x] = True
    for x, y in cells:
        up = y > 0 and occ[y - 1, x]
        dn = y < h - 1 and occ[y + 1, x]
        lf = x > 0 and occ[y, x - 1]
        v = base
        if not up or not lf:
            v += 2
        if not dn:
            v -= 2
        img[y, x, :3] = pal[int(np.clip(v, 0, len(pal) - 1))]
        img[y, x, 3] = 2.0 if v >= 7 else 1.0
    return img


def thick_path(path):
    cells = set()
    for x, y in path:
        cells.add((x, y))
        cells.add((x, y + 1))
    return sorted(cells)


def crossbar():
    w, h = 33, 5
    cells = [(x, 2) for x in range(0, 33)] + [(x, 1) for x in range(3, 30)]
    for cx in (2, 30):
        cells += [(cx, 0), (cx, 3), (cx, 4)]
    cells += [(0, 1), (32, 1)]
    img = line_sprite(sorted(set(cells)), w, h, METAL, 4)
    p = part((-16.5, 25.5, 0), (16.5, 30.5, 0), {"front": img, "back": img[:, ::-1]})
    p["double"] = True
    top = np.zeros((2, w, 4))
    top[:, :, :3] = METAL[4]
    top[0, :, :3] = METAL[6]
    top[:, ::4, :3] = METAL[3]
    top[..., 3] = 1
    top[:, :2, 3] = 0
    top[:, -2:, 3] = 0
    q = part((-16.5, 28.5, -1), (16.5, 28.5, 1), {"top": top, "bottom": top[::-1]})
    q["double"] = True
    return [p, q]


def curl_card():
    path = [(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 3), (6, 4), (6, 5), (7, 6), (7, 7), (7, 8), (6, 9), (5, 9), (4, 8), (4, 7)]
    w, h = 9, 12
    img = line_sprite(thick_path(path), w, h, METAL, 4)
    out = []
    for z in (-0.5, 0.5):
        p = part((3, 15, z), (12, 27, z), {"front": img, "back": img[:, ::-1]}, [((3, 26, 0), (0, 20 if z > 0 else -20, 0))])
        p["double"] = True
        out.append(p)
    return out


def shard(base_pt, length, width, ang_z, ang_y, pal=RED, tone=5):
    n = width
    rows = []
    for r in range(length):
        k = min(n, 1 + 2 * (r // 2))
        a = (n - k) // 2
        rows.append((a, a + k - 1))
    img = np.zeros((length, n, 4))
    for r, (a, b) in enumerate(rows):
        for c in range(a, b + 1):
            v = tone + (length - 1 - r) * 2 // length
            if r < 2:
                v = 8 - r
            elif c == a:
                v += 2
            elif c == b:
                v -= 2
            g = shine_at(base_pt[1] + 0.7 * (length - r), 0) if pal is RED else 0
            v = 8 if g == 2 else (max(v + 2, 6) if g == 1 else v)
            v = int(np.clip(v, 0, len(pal) - 1))
            img[r, c, :3] = pal[v]
            img[r, c, 3] = 2.0 if v >= 7 else 1.0
    x, y, z = base_pt
    tr = [((x, y, z), (0, 0, ang_z)), ((x, y, z), (0, ang_y, 0))]
    p = part((x - n / 2, y, z), (x + n / 2, y + length, z), {"front": img, "back": img[:, ::-1]}, tr)
    q = part((x, y, z - n / 2), (x, y + length, z + n / 2), {"right": img, "left": img[:, ::-1]}, tr)
    p["double"] = q["double"] = True
    return [p, q]


def thorn(pt, ang_z):
    rows = [(1, 1), (1, 1), (0, 2), (0, 2)]
    img = np.zeros((4, 3, 4))
    for r, (a, b) in enumerate(rows):
        for c in range(a, b + 1):
            v = 7 - r + (1 if c == a else 0) - (2 if c == b and b > a else 0)
            img[r, c, :3] = METAL[int(np.clip(v, 0, 8))]
            img[r, c, 3] = 1
    x, y, z = pt
    tr = [((x, y, z), (0, 0, ang_z))]
    p = part((x - 1.5, y, z), (x + 1.5, y + 4, z), {"front": img, "back": img[:, ::-1]}, tr)
    q = part((x, y, z - 1.5), (x, y + 4, z + 1.5), {"right": img, "left": img[:, ::-1]}, tr)
    p["double"] = q["double"] = True
    return [p, q]


def horn_tip(tr):
    rows = [(1, 1)] * 2 + [(0, 1)] * 1 + [(0, 2)] * 1
    h = len(rows)
    img = np.zeros((h, 3, 4))
    tones = [7, 6, 6, 5]
    for r, (a, b) in enumerate(rows):
        for c in range(a, b + 1):
            img[r, c, :3] = METAL[tones[r] + (1 if c == a else 0) - (1 if c == b and b > a else 0)]
            img[r, c, 3] = 1
    p = part((11, 39, 0), (14, 39 + h, 0), {"front": img, "back": img[:, ::-1]}, tr)
    p["double"] = True
    q = part((12.5, 39, -1.5), (12.5, 39 + h, 1.5), {"right": img, "left": img[:, ::-1]}, tr)
    q["double"] = True
    return [p, q]


def wrap_tex(f, t, base):
    tex = {}
    off = 0
    for face in ("front", "right", "back", "left"):
        h, w = face_size(f, t, face)
        y, x = np.mgrid[0:h, 0:w]
        k = (y + x + off) % 4
        idx = base + FACE_LIGHT[face] + np.select([k == 0, k == 3], [1, -1], 0)
        tex[face] = to_rgb(idx, METAL)
        off += w
    for face in ("top", "bottom"):
        h, w = face_size(f, t, face)
        tex[face] = to_rgb(np.full((h, w), base - 1), METAL)
    return tex


def ferrule(y0, y1, base):
    f, t = (-2, y0, -2), (2, y1, 2)
    tex = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        if face in ("top", "bottom"):
            idx = plate(h, w, base + FACE_LIGHT[face], (1.5,))
        else:
            idx = np.full((h, w), base + FACE_LIGHT[face])
            idx[0] += 2
            idx[-1] -= 1
            idx[:, 0] += 1
            idx[:, -1] -= 1
            idx[0, ::2] += 1
            if h > 2:
                idx[h // 2, :] -= 1
                idx[h // 2, 1::3] += 2
        tex[face] = to_rgb(idx, METAL)
    return part(f, t, tex)


def handle(parts):
    f, t = (-1.5, 12, -1.5), (1.5, 21, 1.5)
    parts.append(part(f, t, wrap_tex(f, t, 2)))
    parts.append(ferrule(20, 22, 4))
    parts.append(ferrule(11, 12, 4))
    vine = []
    for k in range(7):
        a = np.radians(200 + k * 75)
        vine.append((1.9 * np.cos(a), 22.5 - k * 1.5, 1.9 * np.sin(a)))
    parts.extend(chain_rods(vine, (1,) * 6, 5, 51))
    f, t = (-1.5, 7, -1.5), (1.5, 11, 1.5)
    tex = {face: glow(crystal(*face_size(f, t, face), 4 + FACE_LIGHT[face], 3, 2), RED) for face in FACES}
    parts.append(part(f, t, tex, [((0, 9, 0), (0, 45, 0))]))
    rows = [(0, 2), (0, 2), (1, 1), (1, 1)]
    img = sharp_card(rows, RED, 4)
    for ax in ("x", "z"):
        if ax == "x":
            p = part((-1.5, 3, 0), (1.5, 7, 0), {"front": img[::-1], "back": img[::-1, ::-1]})
        else:
            p = part((0, 3, -1.5), (0, 7, 1.5), {"right": img[::-1], "left": img[::-1, ::-1]})
        p["double"] = True
        parts.append(p)


def build_parts(pose=None):
    SHINE[0] = (pose or {}).get("shine")
    parts = [blade_card()]
    guard(parts)
    handle(parts)
    side = []
    guard_side(side)
    flat = []
    for p in side:
        flat += p if isinstance(p, list) else [p]
    parts += flat
    parts += [mirror(p) for p in flat]
    return parts
