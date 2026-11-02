import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
from kit import FACES, hexc, face_size, to_rgb, shaded_idx, part, mirror, weave_fur, lock_fur

WHITE = [hexc(c) for c in ("#7f8cb4", "#98a6cc", "#b2bfe0", "#c9d4ee", "#dde5f7", "#ecf1fb", "#f7f9fe", "#fffdf8")]
PINK = [hexc(c) for c in ("#a8687e", "#c98aa0", "#e0a7b8", "#f2c4cf")]
EYE = [hexc(c) for c in ("#2a0710", "#5e1222", "#9a2436", "#f4d2da")]

BODY_DIRS = {"top": "up", "bottom": "up", "right": "right", "left": "left", "front": "down", "back": "down"}
LEG_DIRS = {"top": "up", "bottom": "up", "right": "down", "left": "down", "front": "down", "back": "down"}
UP_DIRS = {k: "up" for k in FACES}


def furtex(f, t, seed, base=6, dirs=BODY_DIRS, locks=()):
    idx = shaded_idx(f, t, base)
    out = {}
    for i, face in enumerate(FACES):
        h, w = idx[face].shape
        if face in locks:
            fur, _ = lock_fur(h, w, seed + i, hi=2, direction=dirs[face])
            fur = fur - 1
        else:
            fur, _ = weave_fur(h, w, seed + i, lo=-1, hi=1, direction=dirs[face])
        out[face] = idx[face] + fur
    return out


def rgb(idx):
    return {k: to_rgb(v, WHITE) for k, v in idx.items()}


BODY_TR = [((0, 3.5, -1), (8, 0, 0))]
HEAD_TR = [((0, 4.5, 3.5), (12, 0, 0))]


def body(parts):
    f, t = (-2.5, 1.5, -5), (2.5, 5.5, 3)
    parts.append(part(f, t, rgb(furtex(f, t, 10, locks=("front",))), BODY_TR))


def head(parts):
    f, t = (-2, 3, 2.5), (2, 7, 6.5)
    tex = rgb(furtex(f, t, 20))
    tex["right"][1, 1] = EYE[1]
    tex["left"][1, 2] = EYE[1]
    parts.append(part(f, t, tex, HEAD_TR))
    nf, nt = (-0.5, 4.5, 6.5), (0.5, 5.5, 7.5)
    nose = {k: to_rgb(np.full(face_size(nf, nt, k), 2), PINK) for k in FACES}
    parts.append(part(nf, nt, nose, HEAD_TR))


def ear(side):
    f, t = (0, 6.5, 4), (2, 12.5, 5)
    tex = rgb(furtex(f, t, 30, dirs=UP_DIRS))
    fr = tex["front"]
    h = fr.shape[0]
    fr[1:h - 1, 0] = PINK[2]
    fr[1, 0] = PINK[1]
    fr[h - 2, 0] = PINK[1]
    side.append(part(f, t, tex, [((1, 6.5, 4.5), (-28, 0, -14))] + HEAD_TR))


def hind(side):
    f, t = (2, 0.5, -5), (4, 4.5, -1)
    side.append(part(f, t, rgb(furtex(f, t, 40))))
    f, t = (2, 0, -5), (4, 1, 1)
    side.append(part(f, t, rgb(furtex(f, t, 44, base=5, dirs=LEG_DIRS))))


def front_leg(side):
    f, t = (1, 0, 1.5), (2, 3, 2.5)
    side.append(part(f, t, rgb(furtex(f, t, 50, dirs=LEG_DIRS))))


def tail(parts):
    f, t = (-1, 2.5, -6.5), (1, 4.5, -4.5)
    parts.append(part(f, t, rgb(furtex(f, t, 60, base=7, dirs=UP_DIRS)), BODY_TR))


def build_side():
    side = []
    ear(side)
    hind(side)
    front_leg(side)
    return side


def build_parts():
    parts = []
    body(parts)
    head(parts)
    tail(parts)
    side = build_side()
    parts += side
    parts += [mirror(p) for p in side]
    return parts
