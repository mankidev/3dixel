import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render
from anim import track
import model

N = 60
DIM = 0.5


def pose_at(t):
    tap = track(t, [(0, 0), (0.46, 0), (0.56, 1), (0.64, 0), (0.69, 0.35), (0.75, 0), (1, 0)])
    tap_y = track(t, [(0, 0), (0.46, 0), (0.56, 15), (0.64, 0), (0.69, 4), (0.75, 0), (1, 0)])
    shuf = track(t, [(0, 0), (0.08, 0), (0.14, 3), (0.22, 0), (1, 0)])
    return {
        "bob": track(t, [(0, 0), (0.25, -0.7), (0.5, 0), (0.75, -0.7), (1, 0)]),
        "pitch": track(t, [(0, 0), (0.3, 2.5), (0.6, -1.0), (0.85, 1.5), (1, 0)]),
        "roll": track(t, [(0, 0), (0.3, 0), (0.36, -13), (0.58, -13), (0.7, 0), (1, 0)]),
        "chel": track(t, [(0, 0), (0.16, 0), (0.19, 7), (0.22, 0), (0.25, 7), (0.29, 0), (0.86, 0), (0.89, 6), (0.93, 0), (1, 0)]),
        "lift": {1: (5.0 * tap, tap_y, 7.0 * tap), 0: (0.0, shuf, 0.0)},
        "arm": (track(t, [(0, 0), (0.4, -5), (0.8, 3), (1, 0)]), track(t, [(0, 0), (0.3, 4), (0.7, -4), (1, 0)])),
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


def frame(t, size, view):
    parts = darken(model.build_parts(pose_at(t)))
    im = render.shot(parts, 0, size, view, shadow=False, bg=(0, 0, 0))
    a = np.asarray(im).astype(float)
    h, w = a.shape[:2]
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    g = np.clip(1.15 - 0.85 * y ** 1.6, 0.25, 1.0) * np.clip(1.0 - 0.35 * x ** 2, 0, 1)
    return Image.fromarray(np.clip(a * g[..., None], 0, 255).astype(np.uint8))


def main():
    if len(sys.argv) > 1:
        w, h, start, stop, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    else:
        w, h, start, stop, out = 240, 280, 0, N, None
    size = (w, h)
    view = render.fit(model.build_parts(), size, pitch=6, yaws=[0])
    view["scale"] *= 0.97
    if out is None:
        here = os.path.dirname(os.path.abspath(__file__))
        frames = [frame(i / N, size, view) for i in range(N)]
        render.save_gif(frames, os.path.join(here, "idle.gif"), 70)
        sheet = Image.new("RGB", (w * 5, h * ((N // 4 + 4) // 5)))
        for j, i in enumerate(range(0, N, 4)):
            sheet.paste(frames[i], ((j % 5) * w, (j // 5) * h))
        sheet.save(os.path.join(here, "idle_sheet.png"))
        return
    os.makedirs(out, exist_ok=True)
    for i in range(start, stop):
        frame(i / N, size, view).save(os.path.join(out, f"f{i:03d}.png"))


if __name__ == "__main__":
    main()
