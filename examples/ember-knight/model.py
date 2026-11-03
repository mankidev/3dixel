import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import FACES, hexc, face_size, to_rgb, part

D = 2

ARMOR = [hexc(c) for c in ("#070505", "#120f0d", "#1f1a16", "#2e2620", "#40352b", "#574837", "#735f47", "#947c5b", "#b9a079", "#e0cba0")]
RED = [hexc(c) for c in ("#120a0a", "#1d0e0d", "#2b1311", "#3a1814", "#4d1f18", "#64281d", "#7c3424", "#984530", "#b35e42")]
MAIL = [hexc(c) for c in ("#1a1a1c", "#29292c", "#3b3a3f", "#4f4d53", "#66646b", "#807d85", "#9d9aa2", "#bcb9c0")]
BOOT = [hexc(c) for c in ("#0b0a09", "#141210", "#1d1a17", "#28241f", "#352f29", "#443c34", "#5a4f43", "#776a59", "#978871")]
EMBER = [hexc(c) for c in ("#3c0f05", "#8a2608", "#d24c0c", "#ff8a24", "#ffc867", "#fff0c4")]
STEEL = [hexc(c) for c in ("#121213", "#1c1c1e", "#29292c", "#37373b", "#48484d", "#5d5d63", "#7e7e85")]
GRIP = [hexc(c) for c in ("#120c08", "#1f150e", "#2e2016", "#3f2d1f", "#523c2a")]

FACE_LIGHT = {"top": 1, "front": 0, "left": 0, "right": -1, "back": -1, "bottom": -2}
BAYER = np.array([[0.0, 0.5], [0.75, 0.25]])


def dq(v):
    h, w = v.shape
    t = np.tile(BAYER, (h // 2 + 1, w // 2 + 1))[:h, :w]
    return np.floor(v + t).astype(int)


def fs(f, t, face):
    return face_size(f, t, face, D)


def plate(h, w, base, seed, lame=(6, 10), rivets=True, scratches=5, hot=0.3, shine=8.0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    u = x / max(w - 1, 1)
    v = y / max(h - 1, 1)
    hx = hot + rng.uniform(-0.08, 0.08)
    spot = np.exp(-((u - hx) / 0.15) ** 2) * np.exp(-((v - 0.28) / 0.4) ** 2)
    field = base - 0.5 + shine * spot - 0.8 * (u > 0.85) - 0.8 * v
    idx = dq(field)
    rows = []
    r = int(rng.integers(2, lame[0] + 1))
    while r < h - 1:
        rows.append(r)
        r += int(rng.integers(lame[0], lame[1] + 1))
    riv_row = int(rng.integers(0, len(rows))) if rows else -1
    for i, r in enumerate(rows):
        near = np.exp(-((u[0] - hx) / 0.22) ** 2)
        idx[r] = np.maximum(idx[r], base + np.round(4 * near).astype(int))
        idx[r + 1] = base - 2
        if rivets and w >= 8 and i == riv_row and r - 2 >= 0:
            off = int(rng.integers(1, 4))
            for c in range(off, w - 1, int(rng.integers(5, 9))):
                idx[r - 2, c] = base + 2 + (1 if abs(c / max(w - 1, 1) - hx) < 0.25 else 0)
                idx[r - 1, c] = base - 2
    for _ in range(scratches):
        sy, sx = int(rng.integers(0, h)), int(rng.integers(0, w))
        ln = int(rng.integers(2, 5))
        dx = 1 if rng.random() < 0.5 else -1
        for k in range(ln):
            yy, xx = sy + k, sx + k * dx
            if 0 <= yy < h and 0 <= xx < w and yy not in rows and yy - 1 not in rows:
                idx[yy, xx] += 1 if k < ln - 1 else 2
    idx[-1] = np.minimum(idx[-1], base - 2)
    return idx, rows


def cloth(h, w, base, seed, folds_n=None):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    field = np.zeros((h, w))
    n = folds_n or max(3, w // 2)
    for _ in range(n):
        cx = rng.uniform(-1, w)
        lean = rng.uniform(-0.15, 0.15)
        wid = rng.uniform(0.8, 2.2)
        amp = rng.uniform(0.7, 1.5)
        start = rng.uniform(0, h * 0.4)
        pos = cx + lean * y
        g = amp * np.exp(-((x - pos) / wid) ** 2) * (y >= start) * np.clip((y - start) / 6 + 0.3, 0, 1)
        sh = -0.8 * amp * np.exp(-((x - pos - wid * 1.3) / (wid * 0.7)) ** 2) * (y >= start)
        field += g + sh
    field += base - 1.2 * y / max(h - 1, 1) + 0.4
    idx = dq(field)
    for _ in range(max(2, w * h // 40)):
        wy = int(rng.integers(0, h))
        wx = int(rng.integers(0, max(1, w - 3)))
        ln = int(rng.integers(1, 4))
        idx[wy, wx:wx + ln] += -1 if rng.random() < 0.6 else 1
    if h > 4:
        idx[-2:] -= 1
    return idx


def tatter(img, seed, depth=8, pal=RED):
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    out = img if img.shape[-1] == 4 else np.concatenate([img, np.ones((h, w, 1))], -1)
    x = 0
    while x < w:
        span = int(rng.integers(1, 4))
        cut = int(rng.choice([0, 1, 2, depth // 3, depth // 2, depth, int(depth * 0.8)]))
        if cut:
            out[h - cut:, x:x + span, 3] = 0
            for k in range(span):
                if rng.random() < 0.5 and h - cut + 1 < h:
                    out[h - cut:h - cut + 1 + int(rng.integers(0, 3)), x + k:x + k + 1, 3] = 1
        edge = h - cut - 1
        if edge >= 0:
            out[edge, x:x + span, :3] = pal[1]
        x += span
    for _ in range(max(2, w // 4)):
        hy, hx = int(rng.integers(h // 2, h - 2)), int(rng.integers(0, w))
        out[hy, hx, 3] = 0
        if hy + 1 < h:
            out[hy + 1, hx, :3] = pal[1]
    return out


def leather(h, w, base, seed, straps=True):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    u = x / max(w - 1, 1)
    field = base + 2.6 * np.exp(-((u - 0.3) / 0.2) ** 2) - 0.7 * (u > 0.8) - 0.6 * y / max(h - 1, 1)
    idx = dq(field)
    r = int(rng.integers(1, 4))
    while r < h - 1:
        c = int(rng.integers(0, max(1, w - 3)))
        ln = int(rng.integers(2, 5))
        idx[r, c:c + ln] += 1
        idx[r + 1, c:c + ln] -= 1
        r += int(rng.integers(2, 5))
    if straps and h >= 10:
        s = int(rng.integers(h // 3, h // 2))
        idx[s] = base - 2
        idx[s + 1] = base + 1
        idx[s + 2] = base - 1
    idx[-1] = base - 3
    return idx


def mail(h, w, base, seed):
    y, x = np.mgrid[0:h, 0:w]
    u = x / max(w - 1, 1)
    field = base + 1.0 * np.exp(-((u - 0.4) / 0.3) ** 2) - 0.8 * y / max(h - 1, 1)
    idx = dq(field)
    ring = ((x + (y // 2)) % 2 == 0) & (y % 2 == 0)
    idx = np.where(ring, idx + 1, idx)
    idx = np.where((y % 2 == 1) & ((x + (y // 2)) % 2 == 1), idx - 1, idx)
    return idx


def rgba(idx, pal, glow_from=None):
    idx = np.clip(idx, 0, len(pal) - 1)
    img = np.concatenate([to_rgb(idx, pal), np.ones(idx.shape + (1,))], -1)
    if glow_from is not None:
        img[..., 3] = np.where(idx >= glow_from, 2.0, 1.0)
    return img


def textured(f, t, painter, pal, base, seed, tr=(), edit=None):
    tex = {}
    rows = {}
    for i, face in enumerate(FACES):
        h, w = fs(f, t, face)
        out = painter(h, w, base + FACE_LIGHT[face], seed + i * 7)
        if isinstance(out, tuple):
            idx, rows[face] = out
        else:
            idx = out
        tex[face] = rgba(idx, pal)
    if edit:
        edit(tex, rows)
    return part(f, t, tex, tr)


def plate_p(**kw):
    return lambda h, w, b, s: plate(h, w, b, s, **kw)


def limb(p0, p1, w, d, painter, pal, base, seed, top=0.0, edit=None):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    L = max(0.5, round(np.linalg.norm(v) * 2) / 2)
    u = v / np.linalg.norm(v)
    a = -np.degrees(np.arcsin(np.clip(u[2], -1, 1)))
    c = np.degrees(np.arctan2(u[0], -u[1]))
    f = (p0[0] - w / 2, p0[1] - L, p0[2] - d / 2)
    t = (p0[0] + w / 2, p0[1] + top, p0[2] + d / 2)
    pv = tuple(p0)
    return textured(f, t, painter, pal, base, seed, [(pv, (a, 0, 0)), (pv, (0, 0, c))], edit)


def card(f, t, img, tr=(), axis="z"):
    texd = {"front": img, "back": img[:, ::-1]} if axis == "z" else {"right": img, "left": img[:, ::-1]}
    p = part(f, t, texd, tr)
    p["double"] = True
    return p


def spike_img(h, w, pal, base):
    img = np.zeros((h, w, 4))
    for r in range(h):
        n = max(1, round(w * (r + 1) / h))
        if n % 2 != w % 2:
            n = min(w, n + 1)
        a = (w - n) // 2
        for c in range(a, a + n):
            tone = base + 2 - (r * 3) // h + (1 if c == a else 0) - (1 if c == a + n - 1 and n > 1 else 0)
            if r < 2:
                tone = base + 3
            img[r, c, :3] = pal[int(np.clip(tone, 0, len(pal) - 1))]
            img[r, c, 3] = 1
    return img


def crossed_spike(base_pt, hgt, wid, tr_local, pal=ARMOR, tone=4):
    x, y, z = base_pt
    img = spike_img(int(hgt * D), int(wid * D), pal, tone)
    p = card((x - wid / 2, y, z), (x + wid / 2, y + hgt, z), img, tr_local)
    q = card((x, y, z - wid / 2), (x, y + hgt, z + wid / 2), img, tr_local, axis="x")
    return [p, q]


LT, LS = 10.5, 10.5


def legs(parts, walk=None):
    flat = lambda h, w, b, sd: leather(h, w, b, sd, straps=False)
    for s, seed in ((-1, 10), (1, 30)):
        pitch = 0.0
        if walk is None:
            hip = (s * 2.25, 23, 0.0)
            if s < 0:
                knee, ankle, yaw = (-2.7, 12.5, -0.8), (-3.2, 2.0, -1.6), -8
            else:
                knee, ankle, yaw = (3.0, 13.0, 2.4), (4.2, 2.0, 1.2), 24
        else:
            knee, ankle, pitch = walk["legs"][s]
            hip = (s * 2.25, walk["hip_y"], 0.0)
            yaw = -4 if s < 0 else 10
        parts.append(limb(hip, knee, 3.5, 3.5, mail, MAIL, 4, seed))
        parts.append(limb(knee, ankle, 3, 3, leather, BOOT, 4, seed + 1, top=0.5))
        kx, ky, kz = knee
        parts.append(textured((kx - 1.5, ky - 1.5, kz + 1.25), (kx + 1.5, ky + 1.5, kz + 2.25), plate_p(lame=(3, 4), rivets=False, scratches=1), ARMOR, 4, seed + 2, [((kx, ky, kz + 1.75), (-12, 0, 0))]))
        parts.append(textured((kx - 1.75, ky - 3.5, kz - 1.75), (kx + 1.75, ky - 2, kz + 1.75), flat, BOOT, 5, seed + 3, [((kx, ky - 3, kz), (8, 0, s * 4))]))
        ax, ay, az = ankle
        turn = [((ax, ay, az), (pitch, 0, 0)), ((ax, ay, az), (0, yaw, 0))]
        oy = ay - 2.0

        def sole(tex, rows):
            for face in ("front", "left", "right", "back"):
                img = tex[face]
                img[-1, :, :3] = BOOT[0]
                img[-2, :, :3] = BOOT[2]
            img = tex["front"]
            img[0, 1:-1, :3] = BOOT[6]
        parts.append(textured((ax - 1.5, oy, az - 1.75), (ax + 1.5, oy + 1.5, az + 4.25), flat, BOOT, 4, seed + 4, turn, sole))
        parts.append(textured((ax - 1.5, oy + 1.5, az - 1.75), (ax + 1.5, oy + 3.5, az + 1.75), leather, BOOT, 4, seed + 5, [((ax, oy + 3.5, az - 1.75), (20, 0, 0))] + turn))
        parts.append(textured((ax - 1.25, oy, az + 3.75), (ax + 1.25, oy + 1.5, az + 5.25), flat, BOOT, 4, seed + 6, turn, sole))


def torso_lower(parts):
    parts.append(textured((-3.75, 22, -2.5), (3.75, 28, 2.5), mail, MAIL, 4, 50))

    def belt_edit(tex, rows):
        img = tex["front"]
        h, w = img.shape[:2]
        c = w // 2 + 2
        img[0:h, c - 2:c + 2, :3] = STEEL[4]
        img[1:h - 1, c - 1:c + 1, :3] = RED[1]
        img[0, c - 2:c + 2, :3] = STEEL[6]
        img[h - 1, c - 2:c + 2, :3] = STEEL[2]
    parts.append(textured((-4, 23.5, -2.75), (4, 25.5, 2.75), lambda h, w, b, s: leather(h, w, b, s, straps=False), RED, 5, 56, edit=belt_edit))
    parts.append(textured((-4.5, 21.5, 2.75), (4.5, 22.5, 3.25), lambda h, w, b, s: leather(h, w, b, s, straps=False), RED, 4, 57, [((0, 22, 3), (0, 0, 14))]))
    tail = tatter(rgba(leather(12, 3, 5, 58, straps=False), RED), 59, depth=3)
    parts.append(card((1.5, 17, 3.3), (3, 23, 3.3), tail))
    parts.append(textured((-4.25, 25.5, 2), (4.25, 27.5, 3), plate_p(lame=(9, 9), rivets=True, scratches=2, shine=5), ARMOR, 3, 46, [((0, 27.5, 2.5), (-14, 0, 0))]))
    parts.append(textured((-4, 27, 2), (4, 29, 3), plate_p(lame=(9, 9), rivets=False, scratches=2, shine=5), ARMOR, 3, 47, [((0, 29, 2.5), (-10, 0, 0))]))


def torso_upper(parts):
    parts.append(textured((-3.75, 27.5, -2.75), (3.75, 38.5, 2.75), mail, MAIL, 4, 52))
    parts.append(textured((-1, 28, 2.5), (1, 38, 3.5), mail, MAIL, 5, 51, [((0, 38, 3), (-3, 0, 0))]))
    for s in (-1, 1):
        f = (1, 28.5, 0.25) if s > 0 else (-5, 28.5, 0.25)
        t = (5, 38.5, 3.25) if s > 0 else (-1, 38.5, 3.25)
        piv = (s * 1, 38.5, 3.25)

        def edge(tex, rows, s=s):
            img = tex["front"]
            h, w = img.shape[:2]
            inner = 0 if s > 0 else w - 1
            img[:, inner, :3] = ARMOR[7]
            img[::5, inner, :3] = ARMOR[9]
            nxt = 1 if s > 0 else w - 2
            img[:, nxt, :3] = ARMOR[2]
        parts.append(textured(f, t, plate_p(lame=(5, 8), hot=0.25 if s > 0 else 0.7, shine=6.5), ARMOR, 4, 53 + s, [(piv, (0, s * 18, 0)), (piv, (0, 0, -s * 5))], edge))
    parts.append(textured((-4.75, 28, -3.25), (4.75, 38.5, -1.25), plate_p(lame=(5, 8), shine=4), ARMOR, 3, 55, [((0, 38.5, -2), (6, 0, 0))]))
    parts.append(textured((-3.25, 37, -3.25), (3.25, 40, 3.25), cloth, RED, 5, 60, [((0, 38.5, 0), (6, 10, 0))]))
    parts.append(textured((-2, 38.5, -2), (2, 42.5, 2), mail, MAIL, 4, 65))
    parts.append(textured((-2.5, 39.5, -2.5), (2.5, 41, 2.5), plate_p(lame=(2, 3), rivets=True, scratches=1, shine=6), ARMOR, 4, 66, [((0, 40, 0), (-6, 0, 0))]))
    drape = tatter(rgba(cloth(20, 7, 6, 61), RED), 62, depth=6)
    parts.append(card((-5.5, 29, 4.1), (-2, 39, 4.1), drape, [((-3.75, 39, 4.1), (-4, -18, -6))]))
    back = tatter(rgba(cloth(24, 9, 4, 63), RED), 64, depth=7)
    parts.append(card((-5.5, 26, -3.6), (-1, 38, -3.6), back, [((-3, 38, -3.6), (8, 0, 0))]))


def head_a(parts):
    tr = [((0, 40, 0), (8, 6, -5))]
    def hammered(tex, rows):
        rng = np.random.default_rng(77)
        for face in ("top", "front", "left"):
            img = tex[face]
            h, w = img.shape[:2]
            for _ in range(h * w // 14):
                yy, xx = int(rng.integers(0, h)), int(rng.integers(0, max(1, int(w * 0.65))))
                img[yy, xx, :3] = ARMOR[8 if rng.random() < 0.4 else 7]
    parts.append(textured((-3.25, 41.5, -3.25), (3.25, 46.5, 3.25), plate_p(lame=(4, 6), hot=0.3, shine=6), ARMOR, 4, 70, tr, hammered))
    parts.append(textured((-2.75, 38.5, -2.75), (2.75, 42, 2.75), plate_p(lame=(3, 4), rivets=False, scratches=2), ARMOR, 3, 71, tr))

    def visor_edit(side):
        def edit(tex, rows):
            img = tex["front"]
            h, w = img.shape[:2]
            slit = 2
            img[slit:slit + 2, :, :3] = ARMOR[0]
            img[slit - 1, :, :3] = ARMOR[7]
            img[slit + 2, :, :3] = ARMOR[2]
            ridge = w - 1 if side < 0 else 0
            img[:, ridge, :3] = ARMOR[7]
            img[slit:slit + 2, ridge, :3] = ARMOR[1]
            for yy in range(slit + 4, h - 1, 2):
                for xx in range(1 if side > 0 else 0, w - 1, 2):
                    img[yy, xx, :3] = ARMOR[0]
        return edit
    for side in (-1, 1):
        f = (-3, 40, 2.25) if side < 0 else (0, 40, 2.25)
        t = (0, 45, 3.25) if side < 0 else (3, 45, 3.25)
        parts.append(textured(f, t, plate_p(lame=(9, 9), rivets=False, scratches=2, hot=0.6 if side < 0 else 0.2, shine=5), ARMOR, 4, 72 + side, [((0, 42, 3.25), (0, side * 22, 0)), ((0, 45, 3), (-12, 0, 0))] + tr, visor_edit(side)))

    def band_edit(tex, rows):
        for face in ("front", "back", "left", "right"):
            img = tex[face]
            img[0, ::3, :3] = ARMOR[8]
            img[1, 1::3, :3] = ARMOR[1]
    parts.append(textured((-3.5, 46, -3.5), (3.5, 47, 3.5), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=4), ARMOR, 4, 75, tr, band_edit))

    def cap_edit(tex, rows):
        img = tex["top"]
        h, w = img.shape[:2]
        y, x = np.mgrid[0:h, 0:w]
        d = np.hypot((x - w * 0.38) / w, (y - h * 0.38) / h)
        idx = np.clip(np.round(8 - d * 9).astype(int), 2, 9)
        img[..., :3] = to_rgb(idx, ARMOR)
        img[h // 2, :, :3] = ARMOR[3]
        img[h // 2 - 1, : w // 2, :3] = ARMOR[8]
        for face in ("front", "left", "right", "back"):
            side = tex[face]
            side[0, :, :3] = ARMOR[7 if face in ("front", "left") else 5]
    parts.append(textured((-2.75, 46.5, -2.75), (2.75, 48.5, 2.75), plate_p(lame=(9, 9), rivets=False, scratches=1, shine=5), ARMOR, 4, 76, tr, cap_edit))
    parts.append(textured((-0.5, 48, -2.75), (0.5, 49, 2.75), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=4), ARMOR, 5, 77, tr))

    def crown(w, seed, gem=False):
        rng = np.random.default_rng(seed)
        h = 7
        img = np.zeros((h, w, 4))
        x = 0
        while x < w:
            hgt = int(rng.choice([2, 3, 4, 5, 6, 7, 7]))
            span = 1
            for c in range(x, min(w, x + span)):
                for r in range(h - hgt, h):
                    tone = 2 + (r - (h - hgt)) // 3
                    if r == h - hgt:
                        tone = 7 if hgt >= 3 else 5
                    if c == x and r > h - hgt:
                        tone += 1
                    img[r, c, :3] = ARMOR[min(tone, 9)]
                    img[r, c, 3] = 1
            x += span + (1 if rng.random() < 0.35 else 0)
        img[h - 1, :, :3] = ARMOR[4]
        img[h - 1, :, 3] = 1
        if gem:
            c = w // 2
            img[h - 3:h - 1, c - 1:c + 1, :3] = EMBER[3]
            img[h - 3, c - 1, :3] = EMBER[5]
            img[h - 3:h - 1, c - 1:c + 1, 3] = 2
        return img
    parts.append(card((-3.5, 46.5, 3.5), (3.5, 50, 3.5), crown(14, 80), tr))
    parts.append(card((-3.5, 46.5, -3.5), (3.5, 50, -3.5), crown(14, 81), tr))
    parts.append(card((3.5, 46.5, -3.5), (3.5, 50, 3.5), crown(14, 82), tr, axis="x"))
    parts.append(card((-3.5, 46.5, -3.5), (-3.5, 50, 3.5), crown(14, 83), tr, axis="x"))


def head(parts):
    head_a(parts)


def muscled_arm(parts, sh, el, wr, seed, side):
    sh, el, wr = np.asarray(sh, float), np.asarray(el, float), np.asarray(wr, float)
    parts.append(limb(sh, el, 3.5, 3.5, plate_p(lame=(4, 7), scratches=1), ARMOR, 3, seed))
    a, b = sh * 0.75 + el * 0.25, sh * 0.2 + el * 0.8
    off = np.array((side * 0.5, 0, 1.5))
    parts.append(limb(a + off, b + off, 2.5, 1, plate_p(lame=(3, 5), rivets=True, scratches=1, shine=6), ARMOR, 4, seed + 5))
    mid = el * 0.55 + wr * 0.45
    parts.append(limb(el, mid, 3.5, 3.5, plate_p(lame=(4, 6), scratches=1), ARMOR, 3, seed + 1, top=0.5))
    parts.append(limb(mid, wr, 3, 3, plate_p(lame=(4, 6), scratches=1), ARMOR, 3, seed + 2, top=0.5))


def left_arm(parts):
    plates = [((3.5, 37, -3.5), (9.5, 39.5, 3.5), (4, 39), -18),
              ((5, 35, -3.25), (10, 37.5, 3.25), (5.5, 37.5), -28),
              ((6.5, 33, -3), (10.5, 35.5, 3), (7, 35.5), -38)]
    for i, (f, t, pv, ang) in enumerate(plates):
        parts.append(textured(f, t, plate_p(lame=(3, 5), hot=0.35, shine=6.5 - i), ARMOR, 4 - (i > 1), 90 + i, [((pv[0], pv[1], 0), (0, 0, ang))]))
    sh, el, wr = (6.75, 36.5, 0), (8.1, 29.5, -0.4), (8.4, 23.0, 1.6)
    muscled_arm(parts, sh, el, wr, 100, 1)
    ex, ey, ez = el
    parts.append(textured((ex - 1.75, ey - 1.5, ez - 2.25), (ex + 1.75, ey + 1.5, ez - 0.75), plate_p(lame=(3, 3), rivets=False, scratches=1), ARMOR, 5, 102, [((ex, ey, ez - 1.5), (20, 0, -15))]))
    parts += crossed_spike((ex + 0.5, ey, ez - 2), 2, 1.5, [((ex + 0.5, ey, ez - 2), (-110, 0, -30))])
    wx, wy, wz = wr
    parts.append(textured((wx - 2.25, wy - 0.5, wz - 2.25), (wx + 2.25, wy + 2, wz + 2.25), plate_p(lame=(2, 3), rivets=True, scratches=0), ARMOR, 5, 103, [((wx, wy, wz), (14, 0, -6))]))
    hand(parts, wr, (8.3, 18.5, 2.6), -1, 104)


def hand(parts, wr, tip, inward, seed, fist=False):
    p0, p1 = np.asarray(wr, float), np.asarray(tip, float)
    v = p1 - p0
    u = v / np.linalg.norm(v)
    a = -np.degrees(np.arcsin(np.clip(u[2], -1, 1)))
    c = np.degrees(np.arctan2(u[0], -u[1]))
    pv = tuple(p0)
    base_tr = [(pv, (a, 0, 0)), (pv, (0, 0, c))]
    x, y, z = p0

    def knuckles(tex, rows):
        for face in ("front", "back", "left", "right"):
            img = tex[face]
            h, w = img.shape[:2]
            img[h - 2, :, :3] = ARMOR[7]
            img[h - 1, :, :3] = ARMOR[2]
            img[h - 2, ::2, :3] = ARMOR[9]

    def fingers(tex, rows):
        for face in ("front", "back"):
            img = tex[face]
            h, w = img.shape[:2]
            for c0 in range(2, w, 2):
                img[:, c0, :3] = ARMOR[1]
            img[0, :, :3] = ARMOR[6]
            img[h // 2, :, :3] = ARMOR[2]
    parts.append(textured((x - 1.5, y - 2.5, z - 0.75), (x + 1.5, y + 0.5, z + 0.75), plate_p(lame=(9, 9), rivets=False, scratches=1, shine=5), ARMOR, 4, seed, base_tr, knuckles))
    curl = (75 if fist else 35) * inward
    kn = (x, y - 2.5, z)
    parts.append(textured((x - 1.5, y - 4.5, z - 0.75), (x + 1.5, y - 2.5, z + 0.75), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=3), ARMOR, 3, seed + 1, [(kn, (0, 0, curl))] + base_tr, fingers))
    th = (x - inward * 1.0, y - 1.0, z + 0.75)
    parts.append(textured((th[0] - 0.5, th[1] - 2, th[2] - 0.5), (th[0] + 0.5, th[1], th[2] + 0.5), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=3), ARMOR, 3, seed + 2, [(th, (-35, 0, inward * 30))] + base_tr))


R_WRIST = np.array((-8.4, 24.8, 4.4))
SWORD_TIP = np.array((-31.5, 3.5, 11.0))


def grip_frame():
    down = np.array((0.0, -1.0, 0.0))
    hc = R_WRIST + 1.5 * down
    for _ in range(4):
        d = (SWORD_TIP - hc) / np.linalg.norm(SWORD_TIP - hc)
        hd = down - np.dot(down, d) * d
        hd /= np.linalg.norm(hd)
        hc = R_WRIST + 1.5 * hd
    return hc, d, hd


def right_arm(parts):
    parts.append(textured((-9.5, 36.5, -3.5), (-3.5, 39.5, 3.5), cloth, RED, 5, 110, [((-4, 39, 0), (0, 0, 16))]))
    parts.append(textured((-10, 34.5, -3.25), (-5, 37, 3.25), plate_p(lame=(3, 4), hot=0.3), ARMOR, 4, 111, [((-5.5, 37, 0), (0, 0, 26))]))
    sh, el, wr = (-6.75, 36.5, 0), (-8.3, 29.8, 1.6), tuple(R_WRIST)
    muscled_arm(parts, sh, el, wr, 112, -1)
    ex, ey, ez = el
    parts.append(textured((ex - 1.75, ey - 1.5, ez - 2.25), (ex + 1.75, ey + 1.5, ez - 0.75), plate_p(lame=(3, 3), rivets=False, scratches=1), ARMOR, 5, 114, [((ex, ey, ez - 1.5), (20, 0, 15))]))
    parts += crossed_spike((ex - 0.5, ey, ez - 2), 2, 1.5, [((ex - 0.5, ey, ez - 2), (-110, 0, 30))])
    wx, wy, wz = wr
    parts.append(textured((wx - 2.25, wy - 0.5, wz - 2.25), (wx + 2.25, wy + 2, wz + 2.25), plate_p(lame=(2, 3), rivets=True, scratches=0), ARMOR, 5, 115, [((wx, wy, wz), (14, 0, 6))]))
    hc, d, hd = grip_frame()
    hand(parts, R_WRIST, tuple(R_WRIST + 3 * hd), 1, 116, fist=True)


def coat(parts, sway=(0.0, 0.0), back=0.0, skirt=0.0):
    flare = 16
    sl, sr = sway

    def panel(w, h, seed, base=5):
        idx = cloth(int(h * D), int(w * D), base, seed)
        H, W = idx.shape
        band = int(H * 0.72)
        idx[band] = base - 3
        idx[band + 1] = base + 1
        idx[band + 1, ::3] = base + 3
        idx[band + 2] = base - 2
        idx[:, 0] = np.maximum(idx[:, 0] - 1, 0)
        img = rgba(idx, RED)
        return tatter(img, seed + 1, depth=18)
    parts.append(card((-5, 5, 3.25), (-1.5, 24, 3.25), panel(3.5, 19, 120), [((-3, 24, 3.25), (-flare - sr, 0, 0))]))
    parts.append(card((1.5, 4.5, 3.25), (5, 24, 3.25), panel(3.5, 19.5, 122), [((3, 24, 3.25), (-flare - sl, 0, 0))]))
    parts.append(card((-5.25, 3, -3.25), (5.25, 24, -3.25), panel(10.5, 21, 124, 4), [((0, 24, -3.25), (flare + back, 0, 0))]))
    parts.append(card((-5, 5, -3.25), (-5, 24, 3.25), panel(6.5, 19, 126, 4), [((-5, 24, 0), (0, 0, -flare))], axis="x"))
    parts.append(card((5, 4.5, -3.25), (5, 24, 3.25), panel(6.5, 19.5, 128, 4), [((5, 24, 0), (0, 0, flare))], axis="x"))
    skirt_img = tatter(rgba(mail(26, 6, 4, 130), MAIL), 131, depth=6, pal=MAIL)
    parts.append(card((-1.5, 11, 3), (1.5, 24, 3), skirt_img, [((0, 24, 3), (-6 - skirt, 0, 0))]))


def blade_img(L):
    h, w = int(L * D), 4
    img = np.zeros((h, w, 4))
    rng = np.random.default_rng(140)
    streak = np.zeros(h)
    r = 3
    while r < h:
        ln = int(rng.integers(3, 8))
        streak[r:r + ln] = rng.choice([-1, 1])
        r += ln + int(rng.integers(4, 10))
    for r in range(h):
        frac = r / max(h - 1, 1)
        span = (1, 2) if frac < 0.03 else ((1, 3) if frac < 0.06 else (0, 3))
        glint = np.exp(-((frac - 0.45) / 0.18) ** 2)
        hand = np.clip((frac - 0.88) / 0.12, 0, 1)
        tipfade = np.clip(frac / 0.15, 0, 1)
        for x in range(span[0], span[1] + 1):
            if x == 0:
                v = 4 + 2.4 * glint * tipfade
            elif x == 1:
                v = 3.4 + 0.8 * glint + 0.6 * streak[r] * (r % 2 == 0)
            elif x == 2:
                v = 1.6 + 0.4 * glint
            else:
                v = 2.2 + 0.8 * glint
            v -= 1.6 * hand
            if span[0] == x and x > 0:
                v += 1.0
            img[r, x, :3] = STEEL[int(np.clip(round(v), 0, len(STEEL) - 1))]
            img[r, x, 3] = 1
    return img


def sword(parts):
    tip = SWORD_TIP.copy()
    tip[1] = TIP_Y
    hc, d0, hd = grip_frame()
    guard = hc + 5.25 * d0
    d = (tip - guard) / np.linalg.norm(tip - guard)
    L = round(np.linalg.norm(tip - guard) * 2) / 2
    a = -np.degrees(np.arcsin(d[2]))
    c = np.degrees(np.arctan2(d[0], -d[1]))
    gx, gy, gz = guard
    tr = [(tuple(guard), (a, 0, 0)), (tuple(guard), (0, 0, c))]
    img = blade_img(L)
    parts.append(card((gx - 1, gy - L, gz), (gx + 1, gy, gz), img[::-1], tr))
    ric = textured((gx - 1, gy - 1.5, gz - 0.5), (gx + 1, gy, gz + 0.5), plate_p(lame=(9, 9), rivets=False, scratches=1, shine=4), STEEL, 3, 139, tr)
    parts.append(ric)

    def guard_edit(tex, rows):
        for face, img in tex.items():
            h, w = img.shape[:2]
            light = {"top": 4, "front": 3, "left": 3, "right": 2, "back": 2, "bottom": 1}[face]
            col = np.full((h, w), light)
            col[0, :] += 1
            col[-1, :] -= 1
            if face in ("front", "top") and w > 3:
                col[0, w // 3] = 6
            img[..., :3] = to_rgb(np.clip(col, 0, 6), STEEL)
    parts.append(textured((gx - 2.5, gy, gz - 0.5), (gx + 2.5, gy + 1, gz + 0.5), plate_p(lame=(9, 9), rivets=False, scratches=1, shine=4), STEEL, 4, 141, tr, guard_edit))
    for s in (-1, 1):
        ex = gx + s * 2.5
        parts.append(textured((ex - 0.5 if s > 0 else ex - 1.5, gy, gz - 0.5), (ex + 1.5 if s > 0 else ex + 0.5, gy + 1, gz + 0.5), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=3), STEEL, 4, 144 + s, [((ex, gy + 0.5, gz), (0, 0, s * 30))] + tr))
    parts.append(textured((gx - 1, gy + 1, gz - 0.75), (gx + 1, gy + 2, gz + 0.75), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=4), STEEL, 4, 146, tr))

    def wrap(h, w, b, sd):
        y, x = np.mgrid[0:h, 0:w]
        k = (y + x) % 3
        idx = b + np.select([k == 0, k == 2], [1, -1], 0)
        idx[:, 0] += 1
        return idx
    parts.append(textured((gx - 0.75, gy + 2, gz - 0.75), (gx + 0.75, gy + 8.5, gz + 0.75), wrap, GRIP, 2, 142, tr))
    parts.append(textured((gx - 1, gy + 8.5, gz - 1), (gx + 1, gy + 9, gz + 1), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=4), STEEL, 4, 147, tr))

    def disc(tex, rows):
        for face, img in tex.items():
            h, w = img.shape[:2]
            light = {"top": 4, "front": 3, "left": 3, "right": 2, "back": 2, "bottom": 1}[face]
            col = np.full((h, w), light)
            col[0, :] += 1
            col[:, -1] -= 1
            if face == "front" and h > 2 and w > 2:
                col[1, 1] = 6
                col[h // 2 - 1:h // 2 + 1, w // 2 - 1:w // 2 + 1] = light - 1
            img[..., :3] = to_rgb(np.clip(col, 0, 6), STEEL)
    pom = (gx, gy + 10, gz)
    parts.append(textured((gx - 1, gy + 9, gz - 0.5), (gx + 1, gy + 11, gz + 0.5), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=5), STEEL, 4, 148, [(pom, (0, 0, 45))] + tr, disc))
    parts.append(textured((gx - 0.5, gy + 11, gz - 0.5), (gx + 0.5, gy + 11.5, gz + 0.5), plate_p(lame=(9, 9), rivets=False, scratches=0, shine=3), STEEL, 4, 149, tr))


TIP_Y = 3.5
HIPS = ((0, 23, 0), (0, 4, -4))
CHEST = ((0, 28, 0), (5, 12, 6))
HEAD = ((0, 41.5, 0), (6, -14, -6))


def lift(group, dy):
    for p in group:
        p["from"] = (p["from"][0], p["from"][1] + dy, p["from"][2])
        p["to"] = (p["to"][0], p["to"][1] + dy, p["to"][2])
        p["tr"] = [((pv[0], pv[1] + dy, pv[2]), r) for pv, r in p["tr"]]
    return group


def pose_group(group, *joints):
    for p in group:
        p["tr"] = list(p["tr"]) + list(joints)
    return group


def build_groups(pose=None):
    lg, lo, up, hd, la, ra, ct, sw = [], [], [], [], [], [], [], []
    walk = (pose or {}).get("walk")
    legs(lg, walk)
    torso_lower(lo)
    torso_upper(up)
    head(hd)
    left_arm(la)
    right_arm(ra)
    coat(ct, walk["coat"] if walk else (0.0, 0.0), walk.get("coat_back", 0.0) if walk else 0.0, walk.get("skirt", 0.0) if walk else 0.0)
    sword(sw)
    hips, chest, headj = HIPS, CHEST, HEAD
    if walk:
        dy = walk["hip_y"] - 23
        for grp in (lo, up, hd, la, ra, ct, sw):
            lift(grp, dy)
        hips = ((0, 23 + dy, 0), (HIPS[1][0], HIPS[1][1] + walk["hip_yaw"], HIPS[1][2] + walk["hip_roll"]))
        chest = ((0, 28 + dy, 0), (CHEST[1][0] + walk.get("chest_pitch", 0), CHEST[1][1] + walk["chest_yaw"], CHEST[1][2] - walk["hip_roll"] * 0.6))
        headj = ((0, 41.5 + dy, 0), (HEAD[1][0] + walk.get("head_nod", 0) - walk.get("chest_pitch", 0) * 0.5, HEAD[1][1] - walk["chest_yaw"] * 0.5, HEAD[1][2]))
        pose_group(la, ((6.75, 36.5 + dy, 0), (walk["arm_l"], 0, 0)))
        pose_group(ra + sw, ((-6.75, 36.5 + dy, 0), (walk["arm_r"], 0, 0)))
    lift(hd, 1.5)
    pose_group(hd, headj, chest, hips)
    pose_group(up + la + ra + sw, chest, hips)
    pose_group(lo + ct, hips)
    return {"legs": lg, "lower": lo, "upper": up, "head": hd, "left_arm": la, "right_arm": ra, "coat": ct, "sword": sw}


def build_parts(pose=None):
    g = build_groups(pose)
    return [p for k in ("legs", "lower", "coat", "upper", "left_arm", "right_arm", "sword", "head") for p in g[k]]
