import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import FACES, hexc, face_size, to_rgb, part, mirror, light_tone, noise_field, _domed
from render import apply_transforms

FLESH = [hexc(c) for c in ("#1e0b18", "#311224", "#4a1830", "#64203c", "#802c48", "#9b3b54",
                           "#b44c5f", "#c8606a", "#d87577", "#e48c86", "#eea79a", "#f6c6b4")]
MOUTH = [hexc(c) for c in ("#0d0308", "#1f0610", "#350b19", "#521425", "#721e33", "#922c41", "#b13f50", "#cc5c66")]
TEETH = [hexc(c) for c in ("#6e2a3a", "#a45a66", "#c88a8e", "#e0b2ae", "#efd2c9", "#f8e8df", "#fff8f2")]
SPINE = [hexc(c) for c in ("#070407", "#110a10", "#1c1119", "#291923", "#3a2531", "#523845", "#77596a", "#a8899a")]
N = len(FLESH)

JAW = 42
DY = 4
CHEST_TR = [((0, 26, 0), (7, 0, 0))]
REAR_TR = [((0, 24, 1), (-13, 0, 0))]
NECK_TR = [((0, 22, 11), (20, 0, 0))]
HEAD_SHIFT = (0, -8, 1)
HEAD_TR = [((0, 27.5, 18), (2, 0, 0))]
SNOUT_TR = [((0, 27, 24), (5, 0, 0))] + HEAD_TR
HINGE = (0, 24.5, 19)
JAW_TR = [(HINGE, (JAW, 0, 0))] + HEAD_TR


def face_light(face, h, w, seed, top=1.0, low=0.3):
    r = np.arange(h)[:, None] / max(h - 1, 1)
    c = np.arange(w)[None, :] / max(w - 1, 1)
    if face == "top":
        L = np.full((h, w), top) - 0.08 * (1 - r)
    elif face == "bottom":
        L = np.full((h, w), low * 0.6)
    else:
        L = top - (top - low) * r
        if face == "right":
            L = L + 0.06 * (1 - c) - 0.05
        elif face == "left":
            L = L + 0.06 * c + 0.03
        elif face == "back":
            L = L - 0.08
        L = np.broadcast_to(L, (h, w)).copy()
    L = L + 0.12 * (noise_field(h, w, seed, 6) - 0.5)
    return np.clip(L, 0, 1)


def folds(h, w, seed, vertical, gap=(2, 4), seg=(6, 16), wob=0.6):
    if vertical:
        return folds(w, h, seed, False, gap, seg, wob).T
    rng = np.random.default_rng(seed)
    d = np.zeros((h, w))
    y = rng.uniform(0.5, gap[0])
    while y < h:
        x0 = int(rng.integers(-3, max(1, w // 2)))
        x1 = x0 + int(rng.integers(seg[0], seg[1] + 1))
        ph = rng.uniform(0, 6.28)
        for x in range(max(0, x0), min(w, x1)):
            yy = int(round(y + wob * np.sin(x * 0.55 + ph)))
            if 0 <= yy < h:
                d[yy, x] = -2.0
            if 0 <= yy - 1 < h and d[yy - 1, x] > -1:
                d[yy - 1, x] = 0.9
            if 0 <= yy + 1 < h and d[yy + 1, x] > -1:
                d[yy + 1, x] = min(d[yy + 1, x], -0.6)
        y += rng.uniform(*gap)
    return d


def skin_idx(face, h, w, seed, fold=None, pebble=0.25, top=1.0, low=0.3, gap=(2, 4)):
    L = face_light(face, h, w, seed, top, low)
    det = np.zeros((h, w))
    if fold is not None:
        det += folds(h, w, seed + 7, fold == "v", gap)
    if pebble and h > 2 and w > 2:
        det += pebble * np.clip(_domed(h, w, seed + 3, 3.3, 0.9, L), -1.5, 1.5)
    return light_tone(L, det, N)


def skin(f, t, seed, folds_by_face=None, pebble=0.25, extra=None, top=1.0, low=0.3, gap=(2, 4)):
    fb = folds_by_face or {}
    out = {}
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        idx = skin_idx(face, h, w, seed + 11 * i, fb.get(face), pebble, top, low, gap)
        if extra is not None:
            extra(face, idx)
        out[face] = to_rgb(idx, FLESH)
    return out


def pit(idx, r, c, big=False):
    h, w = idx.shape
    rows = (r, r + 1) if big else (r,)
    cols = (c, c + 1) if big else (c,)

    def bump(y, x, v):
        if 0 <= y < h and 0 <= x < w:
            idx[y, x] = min(N - 1, idx[y, x] + v)

    for x in cols:
        bump(rows[0] - 1, x, 2)
        bump(rows[-1] + 1, x, 1)
    for y in rows:
        bump(y, cols[0] - 1, 1)
        bump(y, cols[-1] + 1, 1)
    for k, y in enumerate(rows):
        for x in cols:
            if 0 <= y < h and 0 <= x < w:
                idx[y, x] = 0 if k == 0 else 2


NECK_SP = (2.5, ((12.5, 12), (17.5, 11)))
CHEST_SP = (2, ((10, 9), (3, 8)))
REAR_SP = (2, ((-4, 7), (-11, 6), (-18, 5)))
HEAD_SP = (2.2, ((18.5, 10),))


def socket(idx, x0, z0, sp):
    h, w = idx.shape
    x, pts = sp
    for xx in (x, -x):
        cl = int(np.floor(xx - x0 - 0.5))
        for zb, _ in pts:
            r0, r1 = int(np.floor(zb - 1 - z0)), int(np.floor(zb + 2 - z0))
            for r in range(r0 - 1, r1 + 1):
                for c in range(cl - 1, cl + 3):
                    if 0 <= r < h and 0 <= c < w:
                        core = r0 <= r < r1 and cl <= c <= cl + 1
                        idx[r, c] = 2 if core else max(0, idx[r, c] - 2)


def card(f, t, axis, img, tr):
    tex = {k: None for k in FACES}
    tex["right" if axis == "x" else "front"] = img
    return {"from": f, "to": t, "tex": tex, "tr": list(tr), "double": True}


def spine_img(L, curve, sheath=0):
    widths = [4 if k / (L - 1) < 0.15 else 3 if k / (L - 1) < 0.4 else 2 if k / (L - 1) < 0.75 else 1 for k in range(L)]
    offs, o = [], 0
    for k in range(L):
        u = k / (L - 1)
        target = (curve * u + 0.35 * u * u) * (L - 1)
        if k > 0 and target - o >= 0.5:
            o += 1
        offs.append(o)
    W = max(offs[k] + widths[k] for k in range(L))
    img = np.zeros((L, W, 4))
    for k in range(L):
        s = k / (L - 1)
        r = L - 1 - k
        wd = widths[k]
        for j in range(wd):
            if k < sheath:
                tone = FLESH[7 if j == 0 else 4 if j == wd - 1 else 6]
            elif wd == 1:
                tone = SPINE[3 if k < L - 1 else 2]
            elif j == 0:
                tone = SPINE[int(round(6 - 3 * s))]
            elif j == wd - 1:
                tone = SPINE[1]
            else:
                tone = SPINE[3 if j == 1 else 2]
            img[r, offs[k] + j, :3] = tone
            img[r, offs[k] + j, 3] = 1
    return img



def spine(x, y0, zb, L, curve, lean, roll, tr):
    img = spine_img(L, curve)
    w = img.shape[1]
    z1 = zb + 2
    rt = [((x, y0, zb), (lean, 0, roll))] + tr
    return [card((x, y0, z1 - w), (x, y0 + L, z1), "x", img, rt)]


def teeth_img(heights, down):
    H = max(heights) + 1
    W = 2 * len(heights) - 1
    img = np.zeros((H, W, 4))
    gr = 0 if down else H - 1
    for c in range(W):
        img[gr, c, :3] = MOUTH[6 if c % 2 == 0 else 5]
        img[gr, c, 3] = 1
    for i, hgt in enumerate(heights):
        c = 2 * i
        for k in range(hgt):
            r = 1 + k if down else H - 2 - k
            v = 1 + (k + 1) * 5 / hgt
            img[r, c, :3] = TEETH[int(round(min(v, 6)))]
            img[r, c, 3] = 1
    return img


def body(parts):
    def chest_extra(face, idx):
        h, w = idx.shape
        if face in ("right", "left"):
            dc = -1 if face == "right" else 1
            for c in (5, 7, 9, 11):
                cc = c if face == "right" else w - 1 - c
                idx[7:12, cc] = np.minimum(N - 1, idx[7:12, cc] + 1)
                idx[7:12, cc + dc] -= 1
        if face == "top":
            idx[:, w // 2] += 1
            idx[:, w // 2 - 1] -= 1
            socket(idx, -8, -2, CHEST_SP)
    f, t = (-8, 11, -2), (8, 26, 15)
    parts.append(part(f, t, skin(f, t, 10, {"right": "v", "left": "v", "front": "h", "bottom": "v"}, extra=chest_extra), CHEST_TR))

    def rear_extra(face, idx):
        if face == "top":
            idx[:, idx.shape[1] // 2] += 1
            socket(idx, -6.5, -23, REAR_SP)
    f, t = (-6.5, 13, -23), (6.5, 24, 1)
    parts.append(part(f, t, skin(f, t, 20, {"right": "v", "left": "v", "back": "h", "bottom": "v"}, extra=rear_extra), REAR_TR))


def neck(parts):
    def extra(face, idx):
        if face in ("right", "left"):
            w = idx.shape[1]
            for r, c in ((0, 2), (3, 3), (6, 1)):
                pit(idx, r, c if face == "right" else w - 2 - c, big=True)
        if face == "top":
            socket(idx, -6.5, 10, NECK_SP)
    f, t = (-6.5, 17, 10), (6.5, 26, 20)
    parts.append(part(f, t, skin(f, t, 30, {"right": "v", "left": "v", "bottom": "h", "top": "h"}, extra=extra), NECK_TR))


def mouth_tex(f, t, face, kind, seed):
    h, w = face_size(f, t, face)
    rng = np.random.default_rng(seed)
    idx = np.full((h, w), 2)
    if kind == "palate":
        for r in range(h):
            for c in range(w):
                k = (r + abs(c - (w - 1) / 2) * 0.6) % 2.5
                idx[r, c] = 3 if k < 1 else 1
        idx[:, 0] = 5
        idx[:, -1] = 5
    elif kind == "tongue":
        cx = (w - 1) / 2
        for r in range(h):
            for c in range(w):
                d = abs(c - cx)
                idx[r, c] = 4 if d < cx - 0.6 else 6
                if d < 0.6:
                    idx[r, c] = 3
                if r < 1:
                    idx[r, c] = min(idx[r, c], 2)
        idx += (rng.random((h, w)) < 0.12).astype(int)
    else:
        idx[:] = 1
        idx[-1, :] = 2
    return to_rgb(idx, MOUTH)


def head(parts):
    def skull_extra(face, idx):
        h, w = idx.shape
        if face == "top":
            idx[3:6, 3] -= 1
            idx[3:6, 4] -= 1
            socket(idx, -4, 17, HEAD_SP)
        if face in ("right", "left"):
            idx[0, :] = np.minimum(N - 1, idx[0, :] + 1)
    f, t = (-4, 24, 17), (4, 31, 25)
    tex = skin(f, t, 40, {"right": "v", "left": "v", "top": "h"}, extra=skull_extra)
    tex["bottom"] = mouth_tex(f, t, "bottom", "throat", 41)
    parts.append(part(f, t, tex, HEAD_TR))

    def snout_extra(face, idx):
        w = idx.shape[1]
        if face in ("right", "left"):
            for c in (1, 3, 5, 7):
                pit(idx, 1, c if face == "right" else w - 1 - c)
            idx[-1, :] = np.minimum(N - 1, idx[-1, :] + 2)
        if face == "top":
            idx[:, w // 2] += 1
            idx[:, w // 2 - 1] += 1
            idx[:, 0] -= 1
            idx[:, -1] -= 1
        if face == "front":
            idx[-1, :] = np.minimum(N - 1, idx[-1, :] + 2)
    f, t = (-3, 25, 24), (3, 29, 34)
    tex = skin(f, t, 50, {"right": "h", "left": "h", "top": "h"}, extra=snout_extra)
    tex["bottom"] = mouth_tex(f, t, "bottom", "palate", 51)
    parts.append(part(f, t, tex, SNOUT_TR))

    def jaw_extra(face, idx):
        if face in ("right", "left", "front"):
            idx[0, :] = np.minimum(N - 1, idx[0, :] + 2)
    f, t = (-3.5, 21.5, 18), (3.5, 24.5, 26)
    tex = skin(f, t, 60, {"right": "h", "left": "h", "bottom": "h"}, extra=jaw_extra, top=0.8)
    tex["top"] = mouth_tex(f, t, "top", "throat", 61)
    parts.append(part(f, t, tex, JAW_TR))
    f, t = (-2.5, 21.5, 25), (2.5, 24.5, 34)
    tex = skin(f, t, 70, {"right": "h", "left": "h", "bottom": "h"}, extra=jaw_extra, top=0.8)
    tex["top"] = mouth_tex(f, t, "top", "tongue", 71)
    parts.append(part(f, t, tex, JAW_TR))

    parts.append(card((-2.5, 20, 33.8), (2.5, 25, 33.8), "z", teeth_img([4, 5, 4], True), [((0, 25, 33.8), (-40, 0, 0))] + SNOUT_TR))
    parts.append(card((-2.5, 24.5, 33.4), (2.5, 28.5, 33.4), "z", teeth_img([3, 1, 3], False), [((0, 24.5, 33.4), (35, 0, 0))] + JAW_TR))


def cheek():
    z0, z1, y0, y1 = 18.5, 25, 20, 25
    w, h = round(z1 - z0), round(y1 - y0)
    img = np.zeros((h, w, 4))
    a = np.radians(JAW)
    for r in range(h):
        for c in range(w):
            y = y1 - r - 0.5
            z = z1 - c - 0.5
            jaw_y = HINGE[1] - (z - HINGE[2]) * np.tan(a)
            if y < 24.2 and y > jaw_y - 0.6 and z > HINGE[2] - 0.2:
                v = 4 if y > 23.4 else 2 + (1 if (c + r) % 3 == 0 else 0)
                img[r, c, :3] = MOUTH[v]
                img[r, c, 3] = 1
    return card((3.3, y0, z0), (3.3, y1, z1), "x", img, HEAD_TR)


def head_side(side):
    side.append(card((2.5, 20, 25), (2.5, 25, 34), "x", teeth_img([4, 2, 3, 2, 3], True), SNOUT_TR))
    side.append(card((2.0, 24.5, 25.5), (2.0, 28.5, 33.5), "x", teeth_img([3, 2, 3, 2], False), JAW_TR))
    side.append(cheek())


def spines(side):
    for (x, pts), y0, lean, tr in ((NECK_SP, 25.2, -24, NECK_TR), (CHEST_SP, 25.4, -12, CHEST_TR), (REAR_SP, 23.4, -2, REAR_TR)):
        for z, L in pts:
            side.extend(spine(x, y0, z, L, 0.35, lean, -8, tr))


def head_spines(side):
    side.extend(spine(HEAD_SP[0], 30.4, HEAD_SP[1][0][0], HEAD_SP[1][0][1], 0.35, -14, -8, HEAD_TR))


def limb(f, t, seed, tr, knee=False, shin=False, muscle=False):
    def extra(face, idx):
        h, w = idx.shape
        if muscle and face in ("right", "left"):
            ys, xs = np.mgrid[0:h, 0:w]
            fx = xs if face == "right" else w - 1 - xs
            bulge = ((ys - h * 0.35) / (h * 0.32)) ** 2 + ((fx - w * 0.4) / (w * 0.42)) ** 2 < 1
            idx[bulge] += 1
            groove = np.abs(fx - (w * 0.85 - ys * 0.45)) < 0.5
            idx[groove & (ys > 1) & (ys < h - 2)] -= 2
            idx[(ys > h * 0.7) & ~groove] -= 1
        if muscle and face == "front":
            idx[1:h // 2, :] += 1
        if face == "front" and w >= 3:
            idx[:, w // 2] = np.minimum(N - 1, idx[:, w // 2] + 1)
            if knee and h > 3:
                idx[-3:-1, w // 2 - 1:w // 2 + 1] = np.minimum(N - 1, idx[-3:-1, w // 2 - 1:w // 2 + 1] + 1)
                idx[-1, :] -= 1
        if face == "back" and w >= 3:
            idx[:, w // 2] -= 1
            if shin:
                idx[:, w // 2 - 1] += 1
        if face in ("right", "left") and h > 4:
            idx[1:3, :] += 1
    return part(f, t, skin(f, t, seed, {k: "h" for k in ("front", "back", "right", "left")}, pebble=0.35, extra=extra, gap=(3, 7), top=0.85, low=0.5), tr)


def paw(f, t, seed, tr=()):
    def extra(face, idx):
        h, w = idx.shape
        if face == "top":
            idx[-3:, 1] -= 1
            idx[-1, :] += 1
        if face == "front":
            idx[:, 1] -= 1
            idx[0, :] += 1
        if face in ("right", "left"):
            idx[-1, :] -= 1
            idx[0, :] += 1
            idx[0, :2 if face == "right" else w - 2:] -= 1
        if face == "back":
            idx[:, 1] -= 1
        if face == "bottom":
            idx[:] = 1
            idx[1:3, :] = 3
            idx[-1, :] = 2
    tr = list(tr)
    out = [part(f, t, skin(f, t, seed, {"right": "v", "left": "v"}, pebble=0.2, extra=extra, top=0.8), tr)]
    zf, y = t[2], f[1]
    for cx in (f[0] + 0.5, t[0] - 0.5):
        out.append(card((cx, y, zf - 2), (cx, y + 3, zf + 2), "x", claw_side(), tr))
        out.append(card((cx - 0.5, y, zf + 1.5), (cx + 0.5, y + 2, zf + 1.5), "z", claw_front(), tr))
    return out


CLAW_SIDE = ((0, 1, 6), (0, 2, 3), (0, 3, 3), (1, 0, 4), (1, 1, 2), (2, 0, 1))


def claw_side():
    img = np.zeros((3, 4, 4))
    for r, c, v in CLAW_SIDE:
        img[r, c, :3] = SPINE[v]
        img[r, c, 3] = 1
    return img


def claw_front():
    img = np.zeros((2, 1, 4))
    img[0, 0, :3] = SPINE[4]
    img[1, 0, :3] = SPINE[1]
    img[..., 3] = 1
    return img


def solve(build, lo, hi, target=1.6):
    angles = np.arange(lo, hi, 0.25)
    err = [abs(apply_transforms(*build(a))[1] - target) for a in angles]
    return float(angles[int(np.argmin(err))])


WARM = {}


def ik(end_local, chain, target, start, key):
    def err(v):
        p = apply_transforms(end_local, chain(*v)[-1])
        return (p[1] - target[0]) ** 2 + (p[2] - target[1]) ** 2

    cands = [list(start)] + ([list(WARM[key])] if key in WARM else [])
    a = min(cands, key=err)
    e, step = err(a), 6.0
    while step > 0.02:
        moved = False
        for i in (0, 1):
            for d in (step, -step):
                b = list(a)
                b[i] += d
                eb = err(b)
                if eb < e:
                    a, e, moved = b, eb, True
        if not moved:
            step /= 2
    WARM[key] = a
    return a, e ** 0.5


FRONT_END, HIND_END = (4, -3, 9), (4, -5, -10)


def front_chain(flex=0.0):
    pa, splay = -18 + flex, 12

    def trs(up, f):
        up_tr = [((4, 20, 9), (up, 0, splay))]
        fa_tr = [((4, 10, 9), (f - up, 0, 0))] + up_tr
        pa_tr = [((4, 0, 9), (pa - f, 0, 0))] + fa_tr
        return up_tr, fa_tr, pa_tr
    return trs


def hind_chain(flex=0.0):
    mt, splay = -12 + flex, 6

    def trs(th, s):
        th_tr = [((4, 21, -10), (th, 0, splay))] + REAR_TR
        sh_tr = [((4, 10, -10), (s - th, 0, 0))] + th_tr
        mt_tr = [((4, 1, -10), (mt - s, 0, 0))] + sh_tr
        return th_tr, sh_tr, mt_tr
    return trs


def rest_front(g):
    trs = front_chain()
    return 30.0, solve(lambda f: (FRONT_END, trs(30, f)[2]), -60, 40, g + 1.6)


def rest_hind(g):
    trs = hind_chain()
    return -35.0, solve(lambda s: (HIND_END, trs(-35, s)[2]), 0, 120, g + 1.6)


def front_leg(side, g, foot=None, key="F"):
    if foot is None:
        a, trs, pitch = rest_front(g), front_chain(), 0.0
    else:
        y, z, flex, pitch = foot
        trs = front_chain(flex)
        a, _ = ik(FRONT_END, trs, (y, z), rest_front(-DY), key)
    up_tr, fa_tr, pa_tr = trs(*a)
    side.append(limb((1, 10, 5), (7, 20, 13), 100, up_tr, knee=True, muscle=True))
    side.append(limb((1.5, 0, 6.5), (6.5, 10, 11.5), 110, fa_tr, shin=True, muscle=True))
    side.append(limb((2, -3, 7.5), (6, 0, 10.5), 120, pa_tr))
    x, ey, z = apply_transforms(FRONT_END, pa_tr)
    side.extend(paw((x - 2, ey - 1.6, z - 1.5), (x + 2, ey + 0.4, z + 3.5), 130, [((x, ey, z), (pitch, 0, 0))]))
    return a


def hind_leg(side, g, foot=None, key="H"):
    if foot is None:
        a, trs, pitch = rest_hind(g), hind_chain(), 0.0
    else:
        y, z, flex, pitch = foot
        trs = hind_chain(flex)
        a, _ = ik(HIND_END, trs, (y, z), rest_hind(-DY), key)
    th_tr, sh_tr, mt_tr = trs(*a)
    side.append(limb((1, 10, -14.5), (7, 21, -5.5), 200, th_tr, knee=True, muscle=True))
    side.append(limb((2, 1, -12), (6, 10, -8), 210, sh_tr, shin=True, muscle=True))
    side.append(limb((2, -5, -11.5), (6, 1, -8.5), 220, mt_tr, shin=True))
    x, ey, z = apply_transforms(HIND_END, mt_tr)
    side.extend(paw((x - 2, ey - 1.6, z - 1.5), (x + 2, ey + 0.4, z + 3.5), 230, [((x, ey, z), (pitch, 0, 0))]))
    return a


def tail(parts, sway=None):
    tr = REAR_TR
    pivot = (0, 19, -19)
    for k, (L, w, a) in enumerate(((9, 7, -6), (8, 5, -4), (8, 4, 2), (7, 3, 8), (6, 3, 10))):
        x, y, z = pivot
        yaw = 0.0 if sway is None else sway[k]
        tr = [((x, y, z), (a, yaw, 0))] + tr
        f, t = (-w / 2, y - w / 2, z - L), (w / 2, y + w / 2, z)
        tsp = (1.4, ((z - 5, 5),) if k == 0 else ((z - 4, 4),))

        def extra(face, idx, k=k, f=f, tsp=tsp):
            if face == "top" and k < 2:
                socket(idx, f[0], f[2], tsp)
        parts.append(part(f, t, skin(f, t, 300 + k, {k2: "v" for k2 in ("right", "left", "top", "bottom")}, pebble=0.2, extra=extra), tr))
        if k < 2:
            for zz, sl in tsp[1]:
                sp = spine(tsp[0], y + w / 2 - 0.6, zz, sl, 0.35, 4, -8, tr)
                parts += sp + [mirror(p) for p in sp]
        pivot = (x, y, z - L)


def shift(parts, d):
    out = []
    for p in parts:
        q = dict(p)
        q["from"] = tuple(np.add(p["from"], d))
        q["to"] = tuple(np.add(p["to"], d))
        q["tr"] = [(tuple(np.add(pv, d)), r) for pv, r in p["tr"]]
        out.append(q)
    return out


FRONT_SHIFT, HIND_SHIFT = (2.5, 0, 0), (2, 0, -8)


def legs_side(pose, side_name):
    out = []
    g = -DY - (pose or {}).get("bob", 0.0)
    feet = (pose or {}).get("feet", {})
    legs = []
    front_leg(legs, g, feet.get(side_name + "F"), side_name + "F")
    out += shift(legs, FRONT_SHIFT)
    legs = []
    hind_leg(legs, g, feet.get(side_name + "H"), side_name + "H")
    out += shift(legs, HIND_SHIFT)
    return out


def turn(parts, pivot, rot):
    for p in parts:
        p["tr"] = p["tr"] + [(pivot, rot)]
    return parts


def build_parts(pose=None):
    pose = pose or {}
    parts = []
    body(parts)
    neck(parts)
    hg, hs = [], []
    head(hg)
    head_side(hs)
    head_spines(hs)
    hg = shift(hg + hs + [mirror(p) for p in hs], HEAD_SHIFT)
    nod, yaw = pose.get("nod", 0.0), pose.get("head_yaw", 0.0)
    if nod or yaw:
        turn(hg, (0, 19.5, 19), (nod, yaw, 0))
    parts += hg
    tail(parts, pose.get("tail"))
    sp = []
    spines(sp)
    parts += sp + [mirror(p) for p in sp]
    parts += legs_side(pose, "R")
    parts += [mirror(p) for p in legs_side(pose, "L")]
    return shift(parts, (0, DY + pose.get("bob", 0.0), 0))
