import os
import sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("CORE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core")))
sys.path.insert(0, HERE)
import render
import model

BG_TOP = np.array([46, 38, 66], float)
BG_BOT = np.array([12, 10, 20], float)


def emissive_only(parts):
    out = []
    for p in parts:
        q = dict(p)
        tex = {}
        for k, img in p["tex"].items():
            if img is None:
                tex[k] = None
                continue
            if img.shape[-1] == 4:
                e = img.copy()
                lum = 0.3 * e[..., 0] + 0.59 * e[..., 1] + 0.11 * e[..., 2]
                lit = (e[..., 3] <= 1.5) | (lum < 0.42)
                e[lit, :3] = 0
                e[lit & (e[..., 3] > 0.5), 3] = 2.0
            else:
                e = np.concatenate([np.zeros_like(img), np.full(img.shape[:2] + (1,), 2.0)], -1)
            tex[k] = e
        q["tex"] = tex
        out.append(q)
    return out


def blur(a, r):
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(float)


def glow_shot(parts, yaw, size, view, strength=1.0):
    base = np.asarray(render.shot(parts, yaw, size, view, shadow=False, bg=(0, 0, 0))).astype(float)
    em = np.asarray(render.shot(emissive_only(parts), yaw, size, view, shadow=False, bg=(0, 0, 0))).astype(float)
    h, w = base.shape[:2]
    y = np.linspace(0, 1, h)[:, None, None]
    bg = BG_TOP * (1 - y) + BG_BOT * y
    mask = base.sum(-1, keepdims=True) > 0
    a = np.where(mask, base * 1.2, bg)
    s = min(size) / 400
    a = a + blur(em, 3 * s) * 0.7 * strength + blur(em, 12 * s) * 0.6 * strength + blur(em, 30 * s) * 0.35 * strength
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    name = sys.argv[1]
    out = os.path.join(HERE, "..")
    parts = model.build_parts()
    big = (720, 560)
    view = render.fit(parts, big, 18)
    glow_shot(parts, -30, big, view).save(os.path.join(out, f"{name}_glow.png"))
    small = (420, 330)
    view = render.fit(parts, small, 18)
    render.strip([glow_shot(parts, y, small, view) for y in (0, -90, 150)]).save(os.path.join(out, f"{name}_glow_views.png"))
