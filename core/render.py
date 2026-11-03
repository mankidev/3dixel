import argparse
import importlib.util
import math
import os
import sys
import numpy as np
from PIL import Image

BG = (58, 58, 60)


def rot_matrix(rx, ry, rz):
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    mx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    my = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    mz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return mx @ my @ mz


def apply_transforms(p, transforms):
    p = np.asarray(p, float)
    for pivot, rot in transforms:
        pv = np.asarray(pivot, float)
        p = rot_matrix(*rot) @ (p - pv) + pv
    return p


def box_faces(f, t):
    x0, y0, z0 = f
    x1, y1, z1 = t
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    return {
        "front": ((x0, y1, z1), (dx, 0, 0), (0, -dy, 0)),
        "back": ((x1, y1, z0), (-dx, 0, 0), (0, -dy, 0)),
        "right": ((x1, y1, z1), (0, 0, -dz), (0, -dy, 0)),
        "left": ((x0, y1, z0), (0, 0, dz), (0, -dy, 0)),
        "top": ((x0, y1, z0), (dx, 0, 0), (0, 0, dz)),
        "bottom": ((x0, y0, z1), (dx, 0, 0), (0, 0, -dz)),
    }


OPPOSITE = {"front": "back", "back": "front", "right": "left", "left": "right", "top": "bottom", "bottom": "top"}
LIGHT = np.array([-0.35, 1.0, 0.55])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def render(parts, yaw, pitch, scale, size, center, ss=3, target=(0, 0, 0)):
    W, H = size[0] * ss, size[1] * ss
    sc = scale * ss
    color = np.zeros((H, W, 3), float)
    alpha = np.zeros((H, W), bool)
    depth = np.full((H, W), -1e9)
    cam = rot_matrix(pitch, 0, 0) @ rot_matrix(0, yaw, 0)
    cx, cy = W / 2, H / 2 + center * ss
    view = cam.T @ np.array([0, 0, 1.0])

    tgt = np.asarray(target, float)

    def proj(p):
        q = cam @ (p - tgt)
        return np.array([cx + q[0] * sc, cy - q[1] * sc]), q[2]

    for order, part in enumerate(parts):
        faces = box_faces(part["from"], part["to"])
        for name, (o, u, v) in faces.items():
            tex = part["tex"].get(name)
            if tex is None:
                continue
            o_w = apply_transforms(o, part["tr"])
            u_w = apply_transforms(np.add(o, u), part["tr"]) - o_w
            v_w = apply_transforms(np.add(o, v), part["tr"]) - o_w
            n = np.cross(u_w, v_w)
            nl = np.linalg.norm(n)
            if nl < 1e-9:
                continue
            n = -n / nl
            if np.dot(n, view) <= 0:
                if not part.get("double") or part["tex"].get(OPPOSITE[name]) is not None:
                    continue
                n = -n
            s0, d0 = proj(o_w)
            su, du = proj(o_w + u_w)
            sv, dv = proj(o_w + v_w)
            su, du = su - s0, du - d0
            sv, dv = sv - s0, dv - d0
            m = np.array([[su[0], sv[0]], [su[1], sv[1]]])
            det = np.linalg.det(m)
            if abs(det) < 1e-6:
                continue
            inv = np.linalg.inv(m)
            corners = np.array([s0, s0 + su, s0 + sv, s0 + su + sv])
            xa, ya = np.floor(corners.min(0)).astype(int)
            xb, yb = np.ceil(corners.max(0)).astype(int)
            xa, ya = max(xa, 0), max(ya, 0)
            xb, yb = min(xb, W - 1), min(yb, H - 1)
            if xa > xb or ya > yb:
                continue
            gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            px, py = gx - s0[0], gy - s0[1]
            a = inv[0, 0] * px + inv[0, 1] * py
            b = inv[1, 0] * px + inv[1, 1] * py
            inside = (a >= 0) & (a < 1) & (b >= 0) & (b < 1)
            if not inside.any():
                continue
            d = d0 + a * du + b * dv + order * 1e-4
            sub_d = depth[ya:yb + 1, xa:xb + 1]
            win = inside & (d > sub_d)
            if not win.any():
                continue
            th, tw = tex.shape[:2]
            ti = np.clip((b * th).astype(int), 0, th - 1)
            tj = np.clip((a * tw).astype(int), 0, tw - 1)
            texel = tex[ti, tj]
            shade = 0.58 + 0.42 * max(0.0, float(np.dot(n, LIGHT)))
            if n[1] < -0.5:
                shade = 0.5
            if texel.shape[-1] == 4:
                a = texel[..., 3]
                win &= a > 0.5
                if not win.any():
                    continue
                shade = np.where(a > 1.5, 1.0, shade)[..., None]
                texel = texel[..., :3]
            col = texel * shade
            sub_c = color[ya:yb + 1, xa:xb + 1]
            sub_c[win] = col[win]
            sub_d[win] = d[win]
            alpha[ya:yb + 1, xa:xb + 1] |= win
    return color, alpha, ss


def compose(color, alpha, ss, bg=BG, shadow=None):
    H, W = alpha.shape
    out = np.zeros((H, W, 3), float)
    out[:] = np.array(bg, float) / 255
    if shadow is not None:
        sx, sy, rx, ry = (v * ss for v in shadow)
        yy, xx = np.mgrid[0:H, 0:W]
        r = ((xx - sx) / rx) ** 2 + ((yy - sy) / ry) ** 2
        out *= np.where(r < 1, 0.72, 1.0)[..., None]
    out[alpha] = color[alpha]
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    return img.resize((W // ss, H // ss), Image.BOX)


def corners(part):
    (x0, y0, z0), (x1, y1, z1) = part["from"], part["to"]
    return [apply_transforms((x, y, z), part["tr"]) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def points(parts):
    return np.array([c for p in parts for c in corners(p)])


def fit(parts, size, pitch=28, yaws=range(0, 360, 15), margin=0.84):
    pts = points(parts)
    lo, hi = pts.min(0), pts.max(0)
    tgt = (lo + hi) / 2
    reach = 1e-6
    for yaw in yaws:
        cam = rot_matrix(pitch, 0, 0) @ rot_matrix(0, yaw, 0)
        q = (pts - tgt) @ cam.T
        reach = max(reach, np.abs(q[:, 0]).max() / size[0], np.abs(q[:, 1]).max() / size[1])
    radius = np.hypot(pts[:, 0] - tgt[0], pts[:, 2] - tgt[2]).max()
    return {"scale": margin / (2 * reach), "target": tuple(tgt), "ground": float(lo[1]), "radius": float(radius), "pitch": pitch}


def shot(parts, yaw, size, view, shadow=True, bg=BG):
    pitch, scale, tgt = view["pitch"], view["scale"], np.asarray(view["target"], float)
    color, alpha, ss = render(parts, yaw, pitch, scale, size, 0, target=tgt)
    sh = None
    if shadow:
        cam = rot_matrix(pitch, 0, 0) @ rot_matrix(0, yaw, 0)
        q = cam @ (np.array([tgt[0], view["ground"], tgt[2]]) - tgt)
        r = view["radius"] * view.get("shadow", 0.85) * scale
        sh = (size[0] / 2 + q[0] * scale, size[1] / 2 - q[1] * scale, r, r * math.sin(math.radians(pitch)))
    return compose(color, alpha, ss, bg=bg, shadow=sh)


def save_gif(frames, path, delay=80):
    step = max(1, len(frames) // 8)
    sample = frames[::step]
    w, h = frames[0].size
    sheet = Image.new("RGB", (w, h * len(sample)))
    for i, f in enumerate(sample):
        sheet.paste(f, (0, i * h))
    pal = sheet.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q = [f.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=delay, loop=0, optimize=False)


def strip(images):
    w, h = images[0].size
    sheet = Image.new("RGB", (w * len(images), h))
    for i, im in enumerate(images):
        sheet.paste(im, (i * w, 0))
    return sheet


def closeup(parts, target, radius, size=(420, 360), pitch=28, yaws=(0, -30)):
    view = {"pitch": pitch, "scale": min(size) / (2.4 * radius), "target": target}
    return strip([shot(parts, y, size, view, shadow=False) for y in yaws])


def preview(parts, out, name, gif=False, pitch=28, shadow=0.85):
    big, small = (720, 560), (420, 330)
    view = dict(fit(parts, big, pitch), shadow=shadow)
    shot(parts, -35, big, view).save(os.path.join(out, f"{name}_preview.png"))
    view = dict(fit(parts, small, pitch), shadow=shadow)
    strip([shot(parts, y, small, view) for y in (0, -90, 145)]).save(os.path.join(out, f"{name}_views.png"))
    if gif:
        frames = [shot(parts, -35 + i * 15, small, view) for i in range(24)]
        save_gif(frames, os.path.join(out, f"{name}_turntable.gif"))


def load_model(path):
    path = os.path.abspath(path)
    if os.path.isdir(path):
        path = os.path.join(path, "model.py")
    folder = os.path.dirname(path)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location("model", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["model"] = mod
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--name")
    ap.add_argument("--out")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--pitch", type=float, default=28)
    ap.add_argument("--closeup", help="x,y,z,radius")
    ap.add_argument("--shadow", type=float, default=0.85)
    a = ap.parse_args()
    mod = load_model(a.model)
    folder = a.model if os.path.isdir(a.model) else os.path.dirname(os.path.abspath(a.model))
    out = a.out or folder
    name = a.name or os.path.basename(os.path.abspath(folder))
    parts = mod.build_parts()
    preview(parts, out, name, a.gif, a.pitch, a.shadow)
    if a.closeup:
        x, y, z, r = (float(v) for v in a.closeup.split(","))
        closeup(parts, (x, y, z), r, pitch=a.pitch).save(os.path.join(out, f"{name}_closeup.png"))
