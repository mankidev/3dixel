import math
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model
import render
from render import apply_transforms

BETA, STRIDE, N = 0.68, 8.0, 40
LIFT = {"F": 3.5, "H": 3.0}
FLEX = {"F": 38.0, "H": 30.0}
PHASE = {"RH": 0.0, "RF": 0.25, "LH": 0.5, "LF": 0.75}
Z0 = {"F": 8.0, "H": -5.0}


def hermite(u, m):
    return (u ** 3 - 2 * u * u + u) * m + (-2 * u ** 3 + 3 * u * u) + (u ** 3 - u * u) * m


def foot(leg, p, g):
    z0 = Z0[leg]
    if p < BETA:
        u = p / BETA
        return (g + 1.6, z0 + STRIDE / 2 - STRIDE * u, 0.0, 0.0), True
    u = (p - BETA) / (1 - BETA)
    s = math.sin(math.pi * u)
    z = z0 - STRIDE / 2 + STRIDE * hermite(u, -(1 - BETA) / BETA)
    return (g + 1.6 + LIFT[leg] * s, z, FLEX[leg] * s, 22.0 * s * s), False


def pose_at(t):
    bob = -0.8 - 0.4 * (0.5 + 0.5 * math.cos(4 * math.pi * t))
    g = -model.DY - bob
    feet, stance = {}, {}
    for name, ph in PHASE.items():
        feet[name], stance[name] = foot(name[1], (t + ph) % 1.0, g)
    return {
        "bob": bob,
        "feet": feet,
        "stance": stance,
        "nod": 2.5 * math.sin(4 * math.pi * t + 0.6),
        "head_yaw": 3.0 * math.sin(2 * math.pi * t),
        "tail": [3.5 * math.sin(2 * math.pi * (t - 0.12 * k)) for k in range(5)],
    }


def leg_error(pose):
    errs = []
    for k, (y, z, flex, _) in pose["feet"].items():
        chain = model.front_chain(flex) if k[1] == "F" else model.hind_chain(flex)
        end = model.FRONT_END if k[1] == "F" else model.HIND_END
        e = apply_transforms(end, chain(*model.WARM[k])[-1])
        errs.append(math.hypot(e[1] - y, e[2] - z))
    return max(errs)


def frames():
    model.WARM.clear()
    for i in range(N):
        model.build_parts(pose_at(i / N))
    for i in range(N):
        pose = pose_at(i / N)
        parts = model.build_parts(pose)
        yield i, pose, parts, leg_error(pose)


def check():
    for i, pose, parts, err in frames():
        low = render.points(parts)[:, 1].min()
        feet = " ".join(f"{k}{'s' if v else '-'}{pose['feet'][k][1]:6.2f}" for k, v in pose["stance"].items())
        print(f"{i:2d} bob {pose['bob']:+.2f} low {low:5.2f} ik {err:.3f} {feet}")


def gif(out, size=(480, 360), yaw=-62):
    view = dict(render.fit(model.build_parts(), size, 22, margin=0.78), shadow=0.55)
    with tempfile.TemporaryDirectory() as tmp:
        for i, pose, parts, err in frames():
            render.shot(parts, yaw, size, view).save(os.path.join(tmp, f"f{i:03d}.png"))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "16", "-i", os.path.join(tmp, "f%03d.png"),
                        "-vf", "split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];[b][p]paletteuse=dither=none",
                        "-loop", "0", out], check=True)


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        gif(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flesh-hound_walk.gif"))
