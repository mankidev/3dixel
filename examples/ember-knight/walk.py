import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
import model
from render import fit, points, rot_matrix, shot

A = 16.6
STANCE = 0.6
STRIDE = 2 * (model.LT + model.LS) * np.sin(np.radians(A))
SPEED = STRIDE / STANCE


def smooth(u):
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))


LIFT = 4.5


def foot_path(p):
    p %= 1.0
    half = STRIDE / 2
    if p < STANCE:
        u = p / STANCE
        return np.array((2.0, half - STRIDE * u)), 0.0
    u = (p - STANCE) / (1 - STANCE)
    z = -half + STRIDE * smooth(u)
    y = 2.0 + LIFT * np.sin(np.pi * u) ** 0.8
    pitch = 26 * np.sin(np.pi * np.clip(u / 0.7, 0, 1)) * (1 - smooth((u - 0.5) / 0.5))
    return np.array((y, z)), pitch


def ik(hip, foot):
    hy, hz = hip
    fy, fz = foot
    dy, dz = hy - fy, fz - hz
    d = min(np.hypot(dy, dz), model.LT + model.LS - 0.02)
    base = np.arctan2(dz, dy)
    a = np.arccos(np.clip((model.LT ** 2 + d ** 2 - model.LS ** 2) / (2 * model.LT * d), -1, 1))
    th = base + a
    knee = np.array((hy - model.LT * np.cos(th), hz + model.LT * np.sin(th)))
    return knee


def walk_pose(t):
    w = 2 * np.pi * t
    hip_y = 22.15 - 0.4 * np.cos(2 * w)
    legs = {}
    for s, ph in ((1, t % 1.0), (-1, (t + 0.5) % 1.0)):
        foot, pitch = foot_path(ph)
        knee = ik((hip_y, 0.0), foot)
        x = s * 2.25
        legs[s] = ((x, knee[0], knee[1]), (x + s * 0.3, foot[0], foot[1]), pitch)
    impact = np.exp(-(((t * 2) % 1.0 - 0.06) / 0.09) ** 2) + np.exp(-(((t * 2) % 1.0 - 1.06) / 0.09) ** 2)
    sl = legs[1][1][2] / (STRIDE / 2)
    sr = legs[-1][1][2] / (STRIDE / 2)
    return {
        "legs": legs,
        "hip_y": hip_y,
        "hip_yaw": 8 * np.sin(w),
        "hip_roll": 4 * np.sin(w - 0.4),
        "chest_yaw": -6 * np.sin(w),
        "chest_pitch": 4 + 2.5 * impact,
        "head_nod": 2.5 * impact,
        "arm_l": 22 * np.sin(w + np.pi / 2 + 0.3),
        "arm_r": 8 * np.sin(w - np.pi / 2 + 0.3),
        "coat": (10 * max(0.0, sl) + 5 * max(0.0, np.sin(w - 0.6)), 10 * max(0.0, sr) + 5 * max(0.0, -np.sin(w - 0.6))),
        "coat_back": 5 * np.sin(2 * w - 0.8),
    }


def build(t):
    pose = {"walk": walk_pose(t)}
    lo, hi = -2.0, 8.0
    for _ in range(11):
        mid = (lo + hi) / 2
        model.TIP_Y = mid
        model.SWORD_TIP[1] = mid
        g = model.build_groups(pose)
        m = points(g["sword"][:1])[:, 1].min()
        if m < 0.05:
            lo = mid
        else:
            hi = mid
    model.TIP_Y = hi
    model.SWORD_TIP[1] = hi
    g = model.build_groups(pose)
    clear_coat(pose, g)
    return model.build_groups(pose)


def clear_coat(pose, g, margin=0.7, flare=16.0):
    w = pose["walk"]
    dy = w["hip_y"] - 23
    pv = np.array((0, 23 + dy, 0))
    rx, ry, rz = model.HIPS[1][0], model.HIPS[1][1] + w["hip_yaw"], model.HIPS[1][2] + w["hip_roll"]
    R = rot_matrix(rx, ry, rz)
    leg = g["legs"]
    sides = {}
    per = len(leg) // 2
    sides[-1] = points(leg[:per])
    sides[1] = points(leg[per:])
    need = {}
    for key, (xa, xb, z0, base) in {"r": (-5.5, -1.0, 3.25, flare), "l": (1.0, 5.5, 3.25, flare), "skirt": (-2.0, 2.0, 3.0, 6.0)}.items():
        best = 0.0
        for s in (-1, 1):
            P = (sides[s] - pv) @ R + pv
            P[:, 1] -= dy
            sel = (P[:, 0] > xa) & (P[:, 0] < xb) & (P[:, 1] < 23.5)
            for x, y, z in P[sel]:
                ang = np.degrees(np.arctan2(z - z0 + margin, 24 - y))
                best = max(best, ang - base)
        need[key] = max(0.0, best)
    sl, sr = w["coat"]
    w["coat"] = (max(sl, need["l"]), max(sr, need["r"]))
    w["skirt"] = need["skirt"]


def sheet(out, n=8, size=(260, 300)):
    rest = model.build_parts()
    view = dict(fit(rest, size, 18, margin=0.8), shadow=0.45)
    tiles = []
    for i in range(n):
        g = build(i / n)
        parts = [q for k in g for q in g[k]]
        im = shot(parts, -70, size, view)
        ImageDraw.Draw(im).text((6, 6), str(i), fill=(230, 230, 230))
        tiles.append(im)
    s = Image.new("RGB", (size[0] * 4, size[1] * ((n + 3) // 4)))
    for i, im in enumerate(tiles):
        s.paste(im, ((i % 4) * size[0], (i // 4) * size[1]))
    s.save(out)


if __name__ == "__main__":
    sheet(sys.argv[1] if len(sys.argv) > 1 else "walk_sheet.png")
