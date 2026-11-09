import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("CORE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core")))
sys.path.insert(0, HERE)
import numpy as np
import render
from anim import track
import model
import glow

N = int(os.environ.get("FRAMES", "40"))


def wave(t, ph=0.0):
    return math.sin(2 * math.pi * (t - ph))


def cyc(t, keys):
    return track(t % 1.0, keys)


SH_Z = [(0, 35), (0.55, -50), (1, 35)]
SH_Y = [(0, 0), (0.3, -1.5), (0.55, 0), (0.8, 1.5), (1, 0)]
FOLD = [(0, 0.05), (0.15, 0), (0.55, 0), (0.76, 0.35), (0.92, 0.12), (1, 0.05)]
BOB = [(0, -6), (0.58, 6), (1, -6)]


def pose_at(t):
    sz = cyc(t, SH_Z)
    return {
        "wing": {
            "sh_z": sz,
            "sh_y": cyc(t, SH_Y),
            "fold": cyc(t, FOLD),
            "wr_z": 0.75 * (cyc(t - 0.1, SH_Z) - sz),
        },
        "bob": cyc(t, BOB),
        "nod": 2.5 * wave(t, 0.3),
        "look": 2 * wave(t, 0.4),
        "jaw": 2.5 + 2.5 * wave(t, 0.1),
        "tail_x": [3.5 * (0.4 + j / 12) * wave(t, 0.15 + j * 0.05) for j in range(12)],
        "tail_z": [2.0 * (0.3 + j / 12) * wave(t, j * 0.06) for j in range(12)],
        "legR": 6 * wave(t, 0.25),
        "legL": 6 * wave(t, 0.35),
        "armR": 3 * wave(t, 0.2),
        "armL": 3 * wave(t, 0.27),
    }


def view_for(size):
    model.build_parts()
    c = model.B([0.0, 64.0, 4.0]) + np.array([0, model.SHIFT, 0])
    return {"pitch": 10, "scale": size[1] / 150.0, "target": tuple(c)}


def main():
    w, h, start, stop, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    size = (w, h)
    view = view_for(size)
    os.makedirs(out, exist_ok=True)
    for i in range(start, stop):
        glow.glow_shot(model.build_parts(pose_at(i / N)), -25, size, view).save(os.path.join(out, f"f{i:03d}.png"))
        print(i, flush=True)


if __name__ == "__main__":
    main()
