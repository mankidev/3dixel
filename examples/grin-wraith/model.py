import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import lock_fur, FACES, hexc, face_size, to_rgb, part, mirror, light_tone, noise_field, _domed
from render import box_faces, rot_matrix, apply_transforms


def pal(*c):
    return [hexc(x) for x in c]


BODY = pal("#030404", "#060708", "#0a0c0c", "#0f1112", "#151819", "#1c2021", "#242929", "#2e3434", "#3a4140", "#48504e")
GREEN = pal("#07160b", "#0d2611", "#143b18", "#1c5420", "#266f27", "#338d2e", "#45ab37", "#62c742", "#8fe060", "#c6f79a")
GLOWC = hexc("#3fbf2a")
YEL = pal("#2a1d04", "#6b4c08", "#b8890f", "#f7c81c", "#ffe85e", "#fffbd2")
GUM = pal("#120509", "#240914", "#3d1022", "#5c1931", "#7e2742", "#a03953", "#bc5466")
TEETH = pal("#3c3428", "#6c604c", "#9c8f74", "#c6ba9a", "#e6dcc0", "#f7f0dc")
N = len(BODY)

NORMALS = {"front": (0, 0, 1), "back": (0, 0, -1), "right": (1, 0, 0), "left": (-1, 0, 0), "top": (0, 1, 0), "bottom": (0, -1, 0)}
FACE_LIGHT = {"top": 1, "front": 0, "left": 0, "right": -1, "back": -1, "bottom": -2}
LIGHTS = [((0, 34, 12), 8.5, 0.55), ((18, 20, 15), 7.5, 0.9), ((-18, 20, 15), 7.5, 0.9), ((9, 7, 23), 7.5, 0.9)]

HB = 45
HEAD_F, HEAD_T = (-13, HB, -9), (13, HB + 26, 11)
UPPER_EYES = [(-7, HB + 21), (7, HB + 21)]
LOWER_EYES = [(-3, HB + 16), (3, HB + 16)]


def ytop(x):
    return HB + 11 + 0.035 * x * x


def ybot(x):
    return HB + 3 + 0.101 * x * x

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


def qd(v):
    lo = np.floor(v)
    fr = v - lo
    h, w = v.shape
    y, x = np.mgrid[0:h, 0:w]
    chk = (x + y) % 2 == 0
    up = (fr > 0.62) | ((fr > 0.42) & chk)
    return (lo + up).astype(int)


def domed(h, w, seed, step, L, amp=1.0):
    if h < 2 or w < 2:
        return np.zeros((h, w))
    return amp * np.clip(_domed(h, w, seed, step, 0.9, L), -2, 2)


def texel_pos(f, t, face, h, w, tr=()):
    o, u, v = (np.asarray(a, float) for a in box_faces(f, t)[face])
    c = (np.arange(w) + 0.5) / w
    r = (np.arange(h) + 0.5) / h
    P = o + u * c[None, :, None] + v * r[:, None, None]
    n = np.asarray(NORMALS[face], float)
    for pv, rot in tr:
        R = rot_matrix(*rot)
        pv = np.asarray(pv, float)
        P = (P - pv) @ R.T + pv
        n = R @ n
    return P, n


def glow_field(f, t, face, h, w, tr=()):
    P, n = texel_pos(f, t, face, h, w, tr)
    G = np.zeros((h, w))
    for c, rad, s in LIGHTS:
        d = np.asarray(c, float) - P
        dist = np.linalg.norm(d, axis=-1) + 1e-6
        facing = np.clip((d @ n) / dist, 0, 1)
        G += s * np.exp(-(dist / rad) ** 2) * (0.25 + 0.75 * facing)
    return G


def tinted(idx, G):
    idx = np.clip(idx, 0, N - 1)
    lvl = np.clip(qd(np.clip(G, 0, 1.3) * 3), 0, 3)
    base = to_rgb(idx, BODY)
    k = (lvl / 3)[..., None] * (0.25 + 0.75 * idx / (N - 1))[..., None]
    return np.clip(base + k * GLOWC, 0, 1)


def rgba(img, a=1.0):
    return np.concatenate([img, np.full(img.shape[:2] + (1,), a)], -1)


def curls(face, h, w, seed, step=4, amp=0.8):
    L = face_light(face, h, w, seed)
    if h < 3 or w < 3:
        return light_tone(L, np.zeros((h, w)), N)
    d = "down" if face not in ("top", "bottom") else "left"
    lk, _ = lock_fur(h, w, seed, hi=6, direction=d)
    return light_tone(L * 0.75, (lk - 3) * 0.6 * amp / 0.8, N) - 1


def skin_idx(face, h, w, seed, fold=None, pebble=0.12, gap=(3, 5)):
    L = face_light(face, h, w, seed)
    det = np.zeros((h, w))
    if fold is not None:
        det += folds(h, w, seed + 7, fold == "v", gap)
    det += domed(h, w, seed + 3, 3.3, L, pebble)
    return light_tone(L, det, N)


def body_part(f, t, seed, tr=(), kind="skin", fold_by=None, edit=None, glow=True, step=3.2):
    tex = {}
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        if kind == "curl":
            idx = curls(face, h, w, seed + 11 * i, step)
        else:
            idx = skin_idx(face, h, w, seed + 11 * i, (fold_by or {}).get(face))
        if edit is not None:
            P, _ = texel_pos(f, t, face, h, w)
            edit(face, idx, P[..., 0], P[..., 1], P[..., 2])
        G = glow_field(f, t, face, h, w, tr) if glow else np.zeros((h, w))
        tex[face] = tinted(idx, G)
    return part(f, t, tex, tr)


def card(f, t, img, tr=(), axis="z"):
    texd = {"front": img, "back": img[:, ::-1]} if axis == "z" else {"right": img, "left": img[:, ::-1]}
    p = part(f, t, texd, tr)
    p["double"] = True
    return p


def orient(p0, p1):
    p0 = np.asarray(p0, float)
    v = np.asarray(p1, float) - p0
    n = np.linalg.norm(v)
    u = v / n
    a = -np.degrees(np.arcsin(np.clip(u[2], -1, 1)))
    c = np.degrees(np.arctan2(u[0], -u[1]))
    pv = tuple(p0)
    return [(pv, (a, 0, 0)), (pv, (0, 0, c))], n


def dil(m):
    out = m.copy()
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out


def spiral(h, w, base_idx, turns, phase=0.0):
    y, x = np.mgrid[0:h, 0:w]
    cy, cx = h / 2, w / 2
    dy, dx = y + 0.5 - cy, x + 0.5 - cx
    rho = np.hypot(dy, dx)
    phi = np.arctan2(dy, dx) + phase
    R = 0.5 * min(h, w)
    b = R / (2 * np.pi * turns)
    s = ((rho / b - phi) / (2 * np.pi)) % 1
    det = np.round(1.3 * np.cos(2 * np.pi * (s - 0.35))).astype(int)
    det[s < 0.16] = -3
    det[rho > R + 0.5] = 0
    return base_idx + det


def tube(h, w, base, seed=0, ring=4, lit_col=0):
    idx = np.full((h, w), base)
    if w > 1:
        idx[:, -1 if lit_col == 0 else 0] -= 1
        idx[:, lit_col] += 2
    rng = np.random.default_rng(seed)
    pos = int(rng.integers(1, ring + 1))
    while pos < h:
        idx[pos] -= 1
        pos += ring + int(rng.integers(1, 3))
    return idx


def horn_color(idx, g):
    idx = np.clip(idx, 0, N - 1)
    a = np.clip(g, 0, 1)[..., None]
    gi = np.clip(idx + 1, 0, len(GREEN) - 1)
    col = to_rgb(idx, BODY) * (1 - a) + to_rgb(gi, GREEN) * a
    img = rgba(col)
    img[..., 3] = np.where((g > 0.7) & (idx >= 5), 2.0, 1.0)
    return img


def horn_seg(p0, p1, th, g0, g1, seed):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = max(1, int(np.ceil(np.linalg.norm(d))) + 1)
    u = d / np.linalg.norm(d)
    phi = np.degrees(np.arccos(np.clip(u[1], -1, 1)))
    beta = np.degrees(np.arctan2(-u[2], u[0])) if np.hypot(u[0], u[2]) > 1e-6 else 0
    hh = th / 2
    f = (p0[0] - hh, p0[1] - 0.5, p0[2] - hh)
    t = (p0[0] + hh, p0[1] - 0.5 + L, p0[2] + hh)
    tex = {}
    for face in FACES:
        fh, fw = face_size(f, t, face)
        b = 4 + FACE_LIGHT[face]
        if face in ("top", "bottom"):
            idx = np.full((fh, fw), b)
            g = np.full((fh, fw), g1 if face == "top" else g0)
        else:
            idx = tube(fh, fw, b, seed, 4, 0 if face in ("front", "left") else fw - 1)
            r = np.arange(fh)[:, None] / max(fh - 1, 1)
            g = np.broadcast_to(g1 + (g0 - g1) * r, (fh, fw))
        tex[face] = horn_color(idx, g)
    pv = tuple(p0)
    return part(f, t, tex, [(pv, (0, 0, -phi)), (pv, (0, beta, 0))]), (phi, beta)


def tip_img(h, w):
    img = np.zeros((h, w, 4))
    for r in range(h):
        n = max(1, round(w * (r + 1) / h))
        if n % 2 != w % 2:
            n = min(w, n + 1)
        a = (w - n) // 2
        for c in range(a, a + n):
            v = 9 - round(3 * r / max(h - 1, 1)) + (0 if c == a else -1) - (1 if c == a + n - 1 and n > 1 else 0)
            img[r, c, :3] = GREEN[int(np.clip(v, 0, 9))]
            img[r, c, 3] = 2.0
    return img


def horn(pts, ths, seed):
    out = []
    n = len(pts) - 1
    rot = None
    for i in range(n):
        p, rot = horn_seg(pts[i], pts[i + 1], ths[i], (i / n) ** 1.8, ((i + 1) / n) ** 1.8, seed + i * 5)
        out.append(p)
    phi, beta = rot
    x, y, z = pts[-1]
    tr = [((x, y, z), (0, 0, -phi)), ((x, y, z), (0, beta, 0))]
    img = tip_img(6, 3)
    out.append(card((x - 1.5, y, z), (x + 1.5, y + 6, z), img, tr))
    out.append(card((x, y, z - 1.5), (x, y + 6, z + 1.5), img, tr, axis="x"))
    return out


def claw_img():
    rows = [(0, 2), (0, 2), (1, 2), (1, 2), (2, 2)]
    img = np.zeros((5, 3, 4))
    for r, (a, b) in enumerate(rows):
        for c in range(a, b + 1):
            v = 5 + r + (1 if c == a else 0) - (1 if c == b and b > a else 0)
            v = int(np.clip(v, 0, 9))
            img[r, c, :3] = GREEN[v]
            img[r, c, 3] = 2.0 if v >= 7 else 1.0
    return img



def plate_part(f, t, tr, seed, kind="skin", fold_by=None, edit=None):
    return body_part(f, t, seed, tr, kind=kind, fold_by=fold_by, edit=edit)


def pec_edit(face, idx, X, Y, Z):
    if face != "front":
        return
    h, w = idx.shape
    r = np.arange(h)[:, None]
    c = np.arange(w)[None, :]
    idx[h - 2:] -= 1
    idx[(r == h - 3) & (c > 1) & (c < w - 2)] += 1
    idx[(r < 3) & (c < w // 2)] += 1


def belly_edit(face, idx, X, Y, Z):
    if face == "top":
        idx -= 3
    if face != "front":
        return
    h, w = idx.shape
    r = np.arange(h)[:, None]
    c = np.arange(w)[None, :]
    d = np.hypot((c - 2) / (w * 0.9), (r - h * 0.45) / (h * 0.5))
    idx += np.round(np.clip(1 - d, 0, 1) * 1.6).astype(int)
    idx[(np.abs(r - (h - 4 + 0.03 * c * c)) < 0.5) & (c < w - 2)] -= 2
    idx[(r == h // 2) & (c == 0)] = 0
    idx[(r == h // 2 - 1) & (c == 0)] += 1


def torso(parts, upper):
    R, W = 16, 16
    for k in range(8):
        th = 45 * k
        tr = [((0, 20.5, R), (-12, 0, 0)), ((0, 0, 0), (0, th, 0))]
        parts.append(plate_part((-W / 2, 0.5, R - 3), (W / 2, 20.5, R), tr, 31 + k, fold_by={"front": "v", "back": "v"}))
    parts.append(body_part((-14, 1, -13), (14, 21, 12), 29, fold_by={"front": "v"}))
    parts.append(body_part((-15, 16, -11), (15, 32, 8), 41, fold_by={"left": "h", "right": "h"}))
    bp = plate_part((0, 17, 6), (14, 36, 11), [((0, 36, 11), (10, 0, 0)), ((0, 26, 11), (0, 10, 0))], 45, edit=belly_edit, fold_by={"front": "h"})
    parts.extend([bp, mirror(bp)])
    parts = upper
    parts.append(body_part((-19, 29, -12), (19, 46, 7), 51, fold_by={"left": "h", "right": "h", "back": "h"}))
    pc = plate_part((0, 34, 6), (17, 45, 10), [((0, 45, 10), (8, 0, 0)), ((0, 40, 10), (0, 16, 0))], 55, edit=pec_edit)
    parts.extend([pc, mirror(pc)])
    parts.append(body_part((-22, 42, -13), (22, 54, 9), 61, kind="curl", step=4))
    parts.extend(ruff())


def ruff_img(W, H, seed):
    rng = np.random.default_rng(seed)
    img = np.zeros((H, W, 4))
    x = int(rng.integers(0, 2))
    while x < W:
        bw = int(rng.integers(3, 5))
        sh = int(rng.integers(H // 2, H - 2))
        for k in range(sh):
            u = k / max(sh - 1, 1)
            wd = max(1, round(bw * (1 - u) + 0.4))
            off = int(round(0.6 * k * (1 if (x // 3) % 2 else 0) / max(sh, 1) * 2))
            for j in range(wd):
                c = x + off + (bw - wd) // 2 + j
                if 0 <= c < W:
                    v = 2 + round(4 * u) + (1 if j == 0 else 0) - (1 if j == wd - 1 and wd > 1 else 0)
                    img[H - 3 - k, c, :3] = BODY[int(np.clip(v, 0, N - 1))]
                    img[H - 3 - k, c, 3] = 1
        x += bw
    for r in (H - 2, H - 1):
        for c in range(W):
            img[r, c, :3] = BODY[2 if r == H - 1 else 3]
            img[r, c, 3] = 1
    return img


def ruff():
    out = []
    y0, H = 50, 13
    spots = [(17.5, 8.5, "z", 25, 0, 9), (22, 3, "x", 0, -32, 11), (22, -7.5, "x", 0, -28, 11),
             (16, -13, "z", -28, 0, 10), (5.5, -13, "z", -30, 0, 11)]
    for sx in (1, -1):
        for i, (x, z, ax, rx, rz, W) in enumerate(spots):
            img = ruff_img(W, H, 700 + i * 13 + (sx > 0) * 5)
            px = sx * x
            tr = [((px, y0, z), (rx, 0, sx * rz))]
            if ax == "z":
                out.append(card((px - W / 2, y0, z), (px + W / 2, y0 + H, z), img, tr))
            else:
                out.append(card((px, y0, z - W / 2), (px, y0 + H, z + W / 2), img, tr, axis="x"))
    return out


def head_front(seed):
    f, t = HEAD_F, HEAD_T
    h, w = face_size(f, t, "front")
    P, _ = texel_pos(f, t, "front", h, w)
    X, Y = P[..., 0], P[..., 1]
    L = face_light("front", h, w, seed)
    fur = curls("front", h, w, seed + 3)
    cy = HB + 13.5
    rr = np.hypot(X / 12.5, (Y - cy) / 12.5) + (noise_field(h, w, seed + 5, 2) - 0.5) * 0.14
    bare = rr < 1
    skin = light_tone(L * 0.65 + 0.25, domed(h, w, seed + 7, 2.6, L, 0.15), N) + 1
    skin[rr > 0.88] -= 1
    idx = np.where(bare, skin, fur)
    ax = np.abs(X)
    idx[(ax > 6) & (ax < 11.5) & (np.abs(Y - (ytop(X) + 2)) < 0.5) & bare] -= 1
    yb = HB + 23.8 + 0.32 * (ax - 4)
    brow = (ax > 3) & (ax < 11)
    idx[brow & (np.abs(Y - yb) < 0.5)] += 2
    idx[brow & (np.abs(Y - yb + 1) < 0.5)] -= 1
    eyes = np.zeros((h, w), bool)
    sock = np.zeros((h, w), bool)
    for ex, ey in UPPER_EYES + LOWER_EYES:
        dx, dy = np.abs(X - ex), np.abs(Y - ey)
        sq = (dx < 2) & (dy < 2)
        eyes |= sq & ~((dx > 1) & (dy > 1))
        sock |= sq
    ds = dil(sock)
    idx[ds] = np.minimum(idx[ds], 1)
    hole = (Y < ytop(X)) & (Y > ybot(X))
    rim = dil(hole) & ~hole
    idx[dil(rim) & ~rim & ~hole] += 1
    idx[rim] = 0
    img = rgba(tinted(idx, np.zeros((h, w))))
    img[eyes | hole, 3] = 0
    for x0, n in ((-11.5, 6), (10.5, 3)):
        top = np.floor(ytop(x0)) - 0.5
        for k in range(n):
            m = (X == x0) & (Y == top - k)
            img[m, :3] = GREEN[8 - min(k, 3)]
            img[m, 3] = 2.0
        m = (X == x0 + (1 if x0 < 0 else -1)) & (Y == top - n + 1)
        img[m, :3] = GREEN[6]
        img[m, 3] = 2.0
    return img


def eye_part(cx, cy):
    img = np.zeros((6, 6, 4))
    img[..., :3] = BODY[0]
    img[..., 3] = 1
    for r in range(1, 5):
        for c in range(1, 5):
            if r in (1, 4) and c in (1, 4):
                continue
            inner = 2 <= r <= 3 and 2 <= c <= 3
            v = 5 if inner else 4 - (1 if (r == 4 and c == 4) else 0)
            img[r, c, :3] = YEL[v]
            img[r, c, 3] = 2.0
    tex = {k: None for k in FACES}
    tex["front"] = img
    return part((cx - 3, cy - 3, 9), (cx + 3, cy + 3, 10), tex)


def maw():
    f, t = (-12, HB + 2, 7), (12, HB + 16, 9)
    h, w = face_size(f, t, "front")
    P, _ = texel_pos(f, t, "front", h, w)
    X, Y = P[..., 0], P[..., 1]
    yt, yb = ytop(X), ybot(X)
    mid = (yt + yb) / 2
    depth = 1 - np.clip(np.abs(Y - mid) / np.maximum((yt - yb) / 2, 0.5), 0, 1)
    idx = np.round(2 - 2 * depth).astype(int)
    up = (Y > yt - 1.6) & (Y < yt + 0.5)
    lo = (Y < yb + 1.6) & (Y > yb - 0.5)
    idx[up] = 5
    idx[up & (Y < yt - 0.9)] = 4
    idx[lo] = 3
    idx[lo & (Y > yb + 0.9)] = 4
    tex = {k: None for k in FACES}
    tex["front"] = to_rgb(idx, GUM)
    out = [part(f, t, tex)]
    img = np.zeros((h, w, 4))
    for c, xc in enumerate(X[0]):
        ax = abs(xc)
        if ax > 10.6:
            continue
        if c % 2 == 0:
            n = 1 if ax > 9 else (3 if 5 < ax < 8 else 2)
            rows = [r for r in range(h) if Y[r, 0] < ytop(xc) - 1.6][:n]
            for k, r in enumerate(rows):
                img[r, c, :3] = TEETH[2 + round(3 * (k + 1) / n) - (1 if k == n - 1 and n > 1 else 0)]
                img[r, c, 3] = 1
        else:
            n = 1 if ax > 8.5 else (3 if 3.5 < ax < 5.5 else 2)
            rows = [r for r in range(h - 1, -1, -1) if Y[r, 0] > ybot(xc) + 1.6][:n]
            for k, r in enumerate(rows):
                img[r, c, :3] = TEETH[1 + round(3 * (k + 1) / n)]
                img[r, c, 3] = 1
    out.append(card((-12, HB + 2, 10.5), (12, HB + 16, 10.5), img))
    return out


def lobe():
    f, t = (11, HB + 11, -6), (20, HB + 26, 6)
    tr = [((15.5, HB + 18.5, 0), (0, 20, 0)), ((11, HB + 11, 0), (0, 0, -10))]
    tex = {}
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        idx = curls(face, h, w, 70 + i * 11, 4, 0.6)
        if face == "front":
            idx = spiral(h, w, idx, 1.3, 0.5)
        elif face == "right":
            idx = spiral(h, w, idx, 1.6, 2.0)
        tex[face] = tinted(idx, np.zeros((h, w)))
    return part(f, t, tex, tr)


def roof():
    top = HB + 26
    out = []
    out.append(body_part((-12, top - 3, 2), (12, top, 11), 81, [((0, top, 11), (35, 0, 0))], kind="curl"))
    out.append(body_part((-12, top - 3, -9), (12, top, 0), 82, [((0, top, -9), (-35, 0, 0))], kind="curl"))
    sp = body_part((4, top - 3, -9), (13, top, 11), 83, [((13, top, 0), (0, 0, -35))], kind="curl")
    out.extend([sp, mirror(sp)])
    out.append(body_part((-7, top + 1, -3), (7, top + 6, 5), 84, kind="curl"))
    return out


CENTER_HORN = ([(3.5, HB + 31, 0.5), (4.8, HB + 37, 0.5), (4.8, HB + 43, 0), (3.8, HB + 48, -0.5), (2.6, HB + 51, -0.5)], [4, 3, 3, 2])
SIDE_HORN = ([(18, HB + 25, 0), (21.5, HB + 28.5, 0), (23.5, HB + 33, 0), (23, HB + 37.5, 0), (21.5, HB + 40.5, 0)], [4, 3, 3, 2])


def head(parts):
    tex = {}
    for i, face in enumerate(FACES):
        h, w = face_size(HEAD_F, HEAD_T, face)
        tex[face] = tinted(curls(face, h, w, 80 + 11 * i), np.zeros((h, w)))
    tex["front"] = head_front(90)
    parts.append(part(HEAD_F, HEAD_T, tex))
    for cx, cy in UPPER_EYES + LOWER_EYES:
        parts.append(eye_part(cx, cy))
    parts.extend(maw())
    parts.extend(roof())
    lb = lobe()
    parts.extend([lb, mirror(lb)])
    for pts, ths in (CENTER_HORN, SIDE_HORN):
        for sx in (1, -1):
            parts.extend(horn([(sx * x, y, z) for x, y, z in pts], ths, 200 + sx * 7))


def green_part(f, t, tr, seed, split=False):
    tex = {}
    for i, face in enumerate(FACES):
        h, w = face_size(f, t, face)
        L = face_light(face, h, w, seed + i)
        det = folds(h, w, seed + 5 + i, False, (2, 3), (3, 8), 0.3) * 0.8 + domed(h, w, seed + 9 + i, 2.6, L, 0.3)
        idx = light_tone(L, det, len(GREEN)) + 1
        if split and face in ("right", "left") and w >= 5:
            for c in (w // 3, 2 * w // 3):
                idx[:, c] -= 2
        idx = np.clip(idx, 0, len(GREEN) - 1)
        img = rgba(to_rgb(idx, GREEN))
        img[..., 3] = np.where(idx >= 7, 2.0, 1.0)
        tex[face] = img
    return part(f, t, tex, tr)


def seg_box(p0, p1, w, d, top):
    tr, n = orient(p0, p1)
    L = max(1, int(round(n)))
    return (p0[0] - w / 2, p0[1] - L, p0[2] - d / 2), (p0[0] + w / 2, p0[1] + top, p0[2] + d / 2), tr, L


def limb(p0, p1, w, d, seed, top=1, edit=None):
    f, t, tr, L = seg_box(p0, p1, w, d, top)
    return body_part(f, t, seed, tr, fold_by={"front": "v", "back": "v", "left": "h"}, edit=edit)


def claw(tip, dirv):
    img = claw_img()
    tr, _ = orient(tip, np.asarray(tip) + dirv)
    x, y, z = tip
    return [card((x - 1.5, y - 5, z), (x + 1.5, y, z), img, tr),
            card((x, y - 5, z - 1.5), (x, y, z + 1.5), img, tr, axis="x")]


def digits(parts, f, tr, p0, L, d, dirv, flen, curl, seed, spread):
    dirv = np.asarray(dirv, float) / np.linalg.norm(dirv)
    for i, dz in enumerate((-d / 2 + 1.5, 0, d / 2 - 1.5)):
        root = apply_transforms((p0[0], p0[1] - L + 0.5, p0[2] + dz), tr)
        dv = dirv + np.asarray(spread, float) * (i - 1)
        dv = dv / np.linalg.norm(dv)
        tip = root + dv * flen
        ff, tt, trf, Lf = seg_box(tuple(root), tuple(tip), 3, 3, 1)
        parts.append(green_part(ff, tt, trf, seed + i * 7))
        end = apply_transforms((root[0], root[1] - Lf + 0.5, root[2]), trf)
        parts.extend(claw(tuple(end), dv + np.asarray(curl, float)))


def knee_edit(face, idx, X, Y, Z):
    h, w = idx.shape
    r = np.arange(h)[:, None]
    c = np.arange(w)[None, :]
    if face == "front":
        d = np.hypot((c - w / 2 + 0.5) / 2.6, (r - (h - 3)) / 2.2)
        idx[d < 1] += 1
        idx[(d >= 1) & (d < 1.45)] -= 1
        idx[(c == w // 2) & (r < h - 6) & (r > 2)] += 1
    if face == "back":
        idx[(c == w // 2) & (r > 2)] -= 1
        idx[(c == w // 2 + 1) & (r > 2)] += 1


def arm(parts, sx, E, W, K, fdir, curl, seed, twitch=0.0):
    S = (sx * 24, 47, 0)
    dl = body_part((19, 42, -5.5), (30, 51, 5.5), seed + 1, [((24.5, 46.5, 0), (0, 0, -25))], kind="curl")
    parts.append(dl if sx > 0 else mirror(dl))
    parts.append(limb(S, E, 9, 9, seed, top=2, edit=knee_edit))
    parts.append(limb(E, W, 8, 8, seed + 20, edit=knee_edit))
    f, t, tr, L = seg_box(W, K, 4, 9, 1)
    parts.append(green_part(f, t, tr, seed + 40))
    fd = np.asarray(fdir, float) + twitch * np.array([-sx * 0.55, 0.45, 0.1])
    digits(parts, f, tr, W, L, 9, fd, 5, curl, seed + 60, (0, 0, 0.12))


def leg(parts, H, Kn, A, B, tdir, curl, seed, tap=0.0):
    parts.append(limb(H, Kn, 11, 11, seed, top=3, edit=knee_edit))
    parts.append(limb(Kn, A, 8, 9, seed + 20, top=2, edit=knee_edit))
    f, t, tr, L = seg_box(A, B, 5, 9, 2)
    parts.append(green_part(f, t, tr, seed + 40))
    td = np.asarray(tdir, float) + tap * np.array([0, 0.7, 0])
    digits(parts, f, tr, A, L, 9, td, 5, curl, seed + 60, (0, 0, 0.15))


def shift(group, d):
    for p in group:
        p["from"] = tuple(np.add(p["from"], d))
        p["to"] = tuple(np.add(p["to"], d))
        p["tr"] = [(tuple(np.add(pv, d)), r) for pv, r in p["tr"]]


def turn(group, pivot, rot):
    for p in group:
        p["tr"] = list(p["tr"]) + [(pivot, rot)]


def build_parts(pose=None):
    pose = pose or {}
    br = pose.get("breath", 0.0)
    parts, upper, hd = [], [], []
    torso(parts, upper)
    head(hd)
    turn(hd, (0, HB + 2, -2), (pose.get("nod", 0.0), pose.get("look", 0.0), pose.get("tilt", 0.0)))
    shift(upper, (0, 0.6 * br, 0.15 * br))
    shift(hd, (0, 0.8 * br, 0.2 * br))
    arms = []
    for sx, E, W, K, fdir, seed, key in ((1, (28, 32, -1), (20, 26, 12), (18, 21, 14), (-0.1, -1, 0.15), 500, "twitch_l"),
                                         (-1, (-28, 32, -1), (-20, 26, 12), (-18, 21, 14), (0.1, -1, 0.15), 600, "twitch_r")):
        g = []
        arm(g, sx, E, W, K, fdir, (0, -0.4, 0.2), seed, pose.get(key, 0.0))
        turn(g, (sx * 24, 47, 0), (pose.get("sway", 0.0) * sx, 0, 0))
        shift(g, (0, 0.6 * br, 0))
        arms.extend(g)
    leg(parts, (-12, 10, 2), (-20, 7, 16), (2, 6.5, 22), (9, 7, 22), (1, -0.35, 0.1), (0, -0.5, 0), 800, pose.get("tap", 0.0))
    leg(parts, (12, 10, 2), (21, 7, 15), (8, 6, 15), (1, 6, 16), (-1, -0.1, 0.1), (0, -0.2, 0), 900)
    return parts + upper + hd + arms
