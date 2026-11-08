import os
import sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("CORE", os.path.join(HERE, "..", "..", "core")))
sys.path.insert(0, HERE)
import render
from anim import track
import model

N = 48
DIM = 0.8


def pose_at(t):
    return {
        "breath": track(t, [(0, 0), (0.5, 1), (1, 0)]),
        "nod": track(t, [(0, 0), (0.5, 2.5), (1, 0)]),
        "tilt": track(t, [(0, 0), (0.28, 0), (0.33, -11), (0.6, -11), (0.7, 0), (1, 0)]),
        "look": track(t, [(0, 0), (0.74, 0), (0.79, 8), (0.92, 8), (1, 0)]),
        "twitch_r": track(t, [(0, 0), (0.12, 0), (0.15, 1), (0.18, 0), (0.21, 1), (0.25, 0), (1, 0)]),
        "twitch_l": track(t, [(0, 0), (0.8, 0), (0.83, 1), (0.88, 0), (1, 0)]),
        "tap": track(t, [(0, 0), (0.45, 0), (0.5, 1), (0.55, 0), (0.6, 1), (0.65, 0), (1, 0)]),
        "sway": track(t, [(0, 0), (0.5, -2), (1, 0)]),
    }


def darken(parts):
    for p in parts:
        for k, img in p["tex"].items():
            if img is None:
                continue
            img = img.copy()
            if img.shape[-1] == 4:
                lit = img[..., 3] <= 1.5
                img[lit, :3] *= DIM
            else:
                img[..., :3] *= DIM
            p["tex"][k] = img
    return parts


def bloom(a):
    m = (a[..., 0] > 200) & (a[..., 1] > 150) & (a[..., 2] < 140)
    mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
    g = np.asarray(mask).astype(float)[..., None] / 255
    return a + g * np.array([255, 205, 60]) * 0.55


def frame(t, size, view):
    parts = darken(model.build_parts(pose_at(t)))
    im = render.shot(parts, -20, size, view, shadow=False, bg=(0, 0, 0))
    a = np.asarray(im).astype(float)
    h, w = a.shape[:2]
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    g = np.clip(1.15 - 0.85 * y ** 1.6, 0.3, 1.0) * np.clip(1.0 - 0.35 * x ** 2, 0, 1)
    a = bloom(a * g[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    if len(sys.argv) > 1:
        w, h, start, stop, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    else:
        w, h, start, stop, out = 300, 340, 0, N, None
    size = (w, h)
    view = render.fit(model.build_parts(), size, pitch=8, yaws=[-20])
    view["scale"] *= 0.96
    if out is None:
        frames = [frame(i / N, size, view) for i in range(N)]
        render.save_gif(frames, os.path.join(HERE, "grin-wraith_idle.gif"), 80)
        return
    os.makedirs(out, exist_ok=True)
    for i in range(start, stop):
        frame(i / N, size, view).save(os.path.join(out, f"f{i:03d}.png"))


if __name__ == "__main__":
    main()
