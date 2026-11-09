import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import FACES, hexc, face_size, to_rgb, part, mirror

STEEL = [hexc(c) for c in ("#121319", "#1f212b", "#30333f", "#454956", "#5d626d", "#7a7f88", "#9ca0a4", "#c4c4bf", "#ece8dc")]
WOOD = [hexc(c) for c in ("#0c0809", "#1a1012", "#2a1a1a", "#3b2420", "#4e3026", "#633e2c", "#7b4f36", "#956442")]
LEATHER = [hexc(c) for c in ("#120c0f", "#211419", "#341e22", "#4a2a29", "#613931", "#7b4c3c", "#95654e", "#ad7f63")]

FACE_LIGHT = {"top": 1, "front": 0, "left": 0, "right": -1, "back": -1, "bottom": -2}

BW, BH = 16, 34
HEAD_Y = 67
BOW = 1
CORE_X = 3
BLADE_X0 = 4


TOP_ROWS = [(12, 12), (12, 12), (11, 12), (11, 12), (10, 12), (10, 12), (10, 13), (10, 13), (9, 13), (9, 14), (8, 14), (7, 14), (4, 14), (0, 15), (0, 15), (0, 15), (0, 15)]


def blade_shape():
    rows = TOP_ROWS + TOP_ROWS[::-1]
    mask = np.zeros((BH, BW), bool)
    cmax = np.zeros(BH, int)
    for r, (a, b) in enumerate(rows):
        mask[r, a:b + 1] = True
        cmax[r] = b
    return mask, cmax


def blade_tex():
    mask, cmax = blade_shape()
    cy = (BH - 1) / 2
    img = np.zeros((BH, BW, 4))
    for r in range(BH):
        for c in range(BW):
            if not mask[r, c]:
                continue
            lit = round(0.9 - 1.8 * r / (BH - 1) - 0.7 * c / (BW - 1))
            e = cmax[r] - c
            up = r == 0 or not mask[r - 1, c]
            dn = r == BH - 1 or not mask[r + 1, c]
            if e == 0:
                v = 8 if r < cy + 4 else 7
            elif e == 1:
                v = 8 + lit
            elif e == 2:
                v = 7 + lit
            elif e == 3:
                v = 6 + lit
            elif e == 4:
                v = 4 + lit
            else:
                v = 5 + lit
                dist = math.hypot(r - cy, (c - 1.5) * 1.1)
                if abs(dist - 3.2) < 0.6:
                    v += 1 if r < cy else -1
                if c >= 4 and e >= 6 and (r * 5 + c * 3) % 11 == 0:
                    v -= 1
                if c >= 1 and e >= 5 and r % 3 == 1 and (c + r) % 5 in (0, 1):
                    v += 1 if r < cy else -1
            if up and e > 0:
                v = max(v + 2, 6)
            if dn and e > 0:
                v -= 2
            img[r, c, :3] = STEEL[int(np.clip(v, 0, 8))]
            img[r, c, 3] = 2.0 if e <= 1 else 1
    return img


def blade_cards():
    img = blade_tex()
    y0 = HEAD_Y - BH / 2
    p = part((BLADE_X0, y0, 0), (BLADE_X0 + BW, y0 + BH, 0), {"front": img, "back": img[:, ::-1]})
    p["double"] = True
    return [p]


def steel_face(h, w, base, seed=0, marks=True):
    y, x = np.mgrid[0:h, 0:w]
    idx = base + np.round(0.7 - 1.4 * y / max(h - 1, 1) - 0.5 * x / max(w - 1, 1)).astype(int)
    if h >= 4 and marks:
        idx[(y + 2 * x + seed) % 7 == 0] -= 1
    idx[0] += 1
    return idx


def neck():
    f, t = (CORE_X, HEAD_Y - 4, -1.5), (BLADE_X0 + 1, HEAD_Y + 4, 1.5)
    tex = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        tex[face] = to_rgb(steel_face(h, w, 4 + FACE_LIGHT[face], FACES.index(face)), STEEL)
    return part(f, t, tex)


def core():
    f, t = (-CORE_X, HEAD_Y - 5, -2), (CORE_X, HEAD_Y + 5, 2)
    tex = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        b = 4 + FACE_LIGHT[face]
        idx = steel_face(h, w, b, FACES.index(face), face not in ("front", "back"))
        if face in ("front", "back"):
            y, x = np.mgrid[0:h, 0:w]
            idx[int(h // 2) - 1:int(h // 2) + 1, int(w // 2) - 1:int(w // 2) + 1] = b - 2
            idx[(h - 1) // 2 - 1, (w - 1) // 2] = b + 1
            for ry, rx in ((1, 1), (1, w - 2), (h - 2, 1), (h - 2, w - 2)):
                idx[ry, rx] = 7
                idx[ry + 1 if ry + 1 < h else ry, rx] = b - 2
            idx[-1] -= 1
        if face == "top":
            idx[:, :] = b
            idx[0] += 1
            idx[:, 0] += 1
            wood = np.full((h, w), -1)
            wy, wx = np.mgrid[0:h, 0:w]
            inside = (np.abs(wx - (w - 1) / 2) <= 1) & (np.abs(wy - (h - 1) / 2) <= 1)
            img = to_rgb(idx, STEEL)
            dd = np.hypot(wx - (w - 1) / 2, wy - (h - 1) / 2)
            wt = np.where(dd < 0.8, 3, np.where(dd < 1.3, 5, 4))
            img[inside] = to_rgb(wt, WOOD)[inside]
            tex[face] = img
            continue
        tex[face] = to_rgb(idx, STEEL)
    return part(f, t, tex)


def spike():
    widths = [1, 1, 1, 1, 3, 3, 3, 5, 5]
    h, w = len(widths), 5
    img = np.zeros((h, w, 4))
    for r, n in enumerate(widths):
        a = (w - n) // 2
        for c in range(a, a + n):
            v = 5 + (h - 1 - r) * 0 - (r // 5)
            if r < 3:
                v = 8 - r
            elif c == 2:
                v = 7 if r < 6 else 6
            elif c < 2:
                v = 6
            else:
                v = 3 + (1 if r < 5 else 0)
            if c == a and c != 2:
                v = max(v, 6) + 1
            img[r, c, :3] = STEEL[int(np.clip(v, 0, 8))]
            img[r, c, 3] = 1
    y0 = HEAD_Y + 5
    p = part((-2.5, y0, 0), (2.5, y0 + h, 0), {"front": img, "back": img[:, ::-1]})
    q = part((0, y0, -2.5), (0, y0 + h, 2.5), {"right": img, "left": img[:, ::-1]})
    p["double"] = q["double"] = True
    return [p, q]


def band(f, t, base, grooves=()):
    tex = {}
    for face in FACES:
        h, w = face_size(f, t, face)
        b = base + FACE_LIGHT[face]
        if face in ("top", "bottom"):
            y, x = np.mgrid[0:h, 0:w]
            d = np.hypot(y - (h - 1) / 2, x - (w - 1) / 2)
            idx = np.where(d < 1.0, b - 2, np.where(d < 1.6, b + 1, b))
            idx[0, :] = np.maximum(idx[0, :], b + 1)
        else:
            idx = np.full((h, w), b)
            idx[0] += 2
            idx[-1] -= 1
            idx[:, 0] += 1
            idx[:, -1] -= 1
            for g in grooves:
                if g < h:
                    idx[g] = b - 2
                    if g - 1 >= 0:
                        idx[g - 1, ::2] = b + 2
            if face in ("front", "left"):
                idx[1:-1, 1] = np.maximum(idx[1:-1, 1], b + 2)
        tex[face] = to_rgb(idx, STEEL)
    return tex


def wood_tex(f, t, base, seed):
    tex = {}
    rng = np.random.default_rng(seed)
    for face in FACES:
        h, w = face_size(f, t, face)
        b = base + FACE_LIGHT[face]
        if face in ("top", "bottom"):
            tex[face] = to_rgb(np.full((h, w), b - 1), WOOD)
            continue
        y, x = np.mgrid[0:h, 0:w]
        idx = b + np.round(0.4 - 0.8 * y / max(h - 1, 1)).astype(int)
        idx[:, 0 if face in ("front", "left") else w - 1] += 1 if face in ("front", "left") else -1
        for _ in range(max(2, h // 4)):
            c = int(rng.integers(0, w))
            s = int(rng.integers(0, h))
            L = int(rng.integers(5, 12))
            idx[s:s + L, c] += 1 if rng.random() < 0.4 else -1
        if face == "front":
            ky = h // 3
            for r in range(max(0, ky - 2), min(h, ky + 3)):
                for c in range(w):
                    d = math.hypot((r - ky) * 0.6, c - 1)
                    if d < 0.6:
                        idx[r, c] = b - 2
                    elif d < 1.3:
                        idx[r, c] = b - 1 if r >= ky else b + 1
        tex[face] = to_rgb(idx, WOOD)
    return tex


def wrap_tex(f, t, base):
    tex = {}
    off = 0
    for face in ("front", "right", "back", "left"):
        h, w = face_size(f, t, face)
        y, x = np.mgrid[0:h, 0:w]
        k = (y + x + off) % 4
        idx = base + FACE_LIGHT[face] + np.select([k == 0, k == 3], [1, -2], 0)
        idx += np.round(0.5 - y / max(h - 1, 1)).astype(int)
        idx[0] = base + FACE_LIGHT[face] - 2
        idx[1] = base + FACE_LIGHT[face] + 1
        idx[-1] = base + FACE_LIGHT[face] - 2
        idx[-2] = base + FACE_LIGHT[face] + 1
        tex[face] = to_rgb(idx, LEATHER)
        off += w
    for face in ("top", "bottom"):
        h, w = face_size(f, t, face)
        idx = np.full((h, w), base - 1)
        idx[0] += 1
        tex[face] = to_rgb(idx, LEATHER)
    return tex


def haft_nodes():
    ys = [3, 14, 30, 50, HEAD_Y + 4]
    xs = [BOW, BOW * 0.35, 0, 0, 0]
    return list(zip(xs, ys))


def along(p0, p1, half, start, length, texfn):
    (x0, y0), (x1, y1) = p0, p1
    f = (x0 - half, y0 + start, -half)
    t = (x0 + half, y0 + start + length, half)
    rz = -math.degrees(math.atan2(x1 - x0, y1 - y0))
    return part(f, t, texfn(f, t), [((x0, y0, 0), (0, 0, rz))])


def haft():
    nodes = haft_nodes()
    out = []
    for i in range(len(nodes) - 1):
        p0, p1 = nodes[i], nodes[i + 1]
        L = math.ceil(math.dist(p0, p1)) + 1
        out.append(along(p0, p1, 1.5, -0.5 if i else 0, L, lambda f, t, i=i: wood_tex(f, t, 3, 7 + i)))
    out.append(along(nodes[0], nodes[1], 2, 4, 16, lambda f, t: wrap_tex(f, t, 4)))
    return out


def build_parts(pose=None):
    parts = haft()
    f, t = (BOW - 2, 0, -2), (BOW + 2, 4, 2)
    parts.append(part(f, t, band(f, t, 4, (2,))))
    parts.append(part((-2, HEAD_Y - 8, -2), (2, HEAD_Y - 5, 2), band((-2, HEAD_Y - 8, -2), (2, HEAD_Y - 5, 2), 4, (1,))))
    parts.append(core())
    parts += spike()
    side = [neck()] + blade_cards()
    parts += side
    parts += [mirror(p) for p in side]
    return parts
