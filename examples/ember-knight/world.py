import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
import model
from model import rgba
from kit import hexc, part
from render import fit, render, rot_matrix, points

B = 8
DIRT = [hexc(c) for c in ("#120d0a", "#1e1510", "#2b1e16", "#39281d", "#483326", "#583f2f", "#6a4c39", "#7d5b45", "#916c53")]
FOG = np.array((0.085, 0.045, 0.04))
LIGHT = {"top": 1, "front": 0, "left": 0, "right": -1, "back": -1, "bottom": -2}


def light_and_fog(parts, light_pos, yaw, pitch, tgt, near, far):
    cam = rot_matrix(pitch, 0, 0) @ rot_matrix(0, yaw, 0)
    warm = np.array((1.0, 0.55, 0.25))
    for p in parts:
        c = points([p]).mean(0)
        lw = 0.0 if light_pos is None else np.clip(1 - np.linalg.norm(c - light_pos) / 40.0, 0, 1) ** 2 * 0.55
        dpt = -(cam @ (c - tgt))[2]
        k = np.clip((dpt - near) / (far - near), 0, 1) * 0.8
        for f, img in p["tex"].items():
            if img is None:
                continue
            glow = img[..., 3] > 1.5
            rgb = img[..., :3]
            rgb = rgb + rgb * warm * lw * 1.8
            rgb = rgb * (1 - k) + FOG * k
            img[..., :3] = np.where(glow[..., None], img[..., :3], np.clip(rgb, 0, 1))


def cast_shadow(floor, parts, light=(-0.35, 1.0, 0.55), strength=0.5):
    from PIL import ImageDraw
    from render import apply_transforms
    img = floor["tex"]["top"]
    hh, ww = img.shape[:2]
    (x0, _, z0), _ = floor["from"], floor["to"]
    k = 16 / B
    L = np.asarray(light, float)
    mask = Image.new("L", (ww, hh), 0)
    dr = ImageDraw.Draw(mask)
    for p in parts:
        (a0, b0, c0), (a1, b1, c1) = p["from"], p["to"]
        pts = []
        for x in (a0, a1):
            for y in (b0, b1):
                for z in (c0, c1):
                    q = apply_transforms((x, y, z), p["tr"])
                    t = q[1] / L[1]
                    gx, gz = q[0] - t * L[0], q[2] - t * L[2]
                    pts.append(((gx - x0) * k, (gz - z0) * k))
        pts = np.array(pts)
        hull = hull_mono(pts)
        dr.polygon([tuple(v) for v in hull], fill=255)
    m = np.array(mask) > 0
    yy, xx = np.mgrid[0:hh, 0:ww]
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    checker = (xx + yy) % 2 == 0
    shade = np.where(m, strength, 1.0)
    shade = np.where(edge & checker, 1.0, shade)
    img[..., :3] *= shade[..., None]


def hull_mono(pts):
    P = sorted(map(tuple, pts))
    if len(P) <= 2:
        return np.array(P)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in P:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(P):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def paint_shadow(parts, cx, cz, rx, rz):
    for p in parts:
        (x0, y0, z0), (x1, y1, z1) = p["from"], p["to"]
        if y1 != 0 or "top" not in p["tex"]:
            continue
        img = p["tex"]["top"]
        hh, ww = img.shape[:2]
        yy, xx = np.mgrid[0:hh, 0:ww]
        wx = x0 + (xx + 0.5) * B / 16
        wz = z0 + (yy + 0.5) * B / 16
        r = ((wx - cx) / rx) ** 2 + ((wz - cz) / rz) ** 2
        t = np.tile(np.array([[0.0, 0.5], [0.75, 0.25]]), (hh // 2 + 1, ww // 2 + 1))[:hh, :ww]
        shade = np.where(r < 0.6, 0.45, np.where(r < 1.0, np.where(t < (1 - r) / 0.4, 0.45, 0.72), 1.0))
        img[..., :3] *= shade[..., None]


def smooth_noise(H, W, cell, rng):
    gh, gw = int(H // cell) + 2, int(W // cell) + 2
    g = rng.random((gh, gw))
    yy, xx = np.mgrid[0:H, 0:W] / cell
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = yy - y0, xx - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = g[y0, x0], g[y0, x0 + 1]
    c, d = g[y0 + 1, x0], g[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy




def band_dither(v, strip=0.12):
    H, W = v.shape
    yy, xx = np.mgrid[0:H, 0:W]
    lo = np.floor(v)
    f = v - lo
    near = np.abs(f - 0.5) < strip
    checker = (xx + yy) % 2 == 0
    return np.where(near, np.where(checker, lo + 1, lo), np.where(f >= 0.5, lo + 1, lo)).astype(int)


def floor_dirt(i0, i1, k0, k1, seed=904):
    rng = np.random.default_rng(seed)
    nx, nz = i1 - i0, k1 - k0
    H, W = nz * 16, nx * 16
    base = 4 + LIGHT["top"]
    large = smooth_noise(H, W, 80, rng)
    mid = smooth_noise(H, W, 22, rng)
    small = smooth_noise(H, W, 7, rng)
    v = base - 0.8 + (large - 0.5) * 1.8 + (mid - 0.5) * 1.3 + (small - 0.5) * 0.5
    idx = band_dither(v)
    speck = smooth_noise(H, W, 1.6, rng)
    idx = np.where(speck > 0.82, idx + 1, np.where(speck < 0.16, idx - 1, idx))
    return part((i0 * B, -B, k0 * B), (i1 * B, 0, k1 * B), {"top": rgba(idx, DIRT)})




def floor_part(i0, i1, k0, k1, seed=900):
    return floor_dirt(i0, i1, k0, k1)


def fog_floor(p, yaw, pitch, tgt, near, far):
    cam = rot_matrix(pitch, 0, 0) @ rot_matrix(0, yaw, 0)
    img = p["tex"]["top"]
    hh, ww = img.shape[:2]
    (x0, y0, z0), (x1, y1, z1) = p["from"], p["to"]
    yy, xx = np.mgrid[0:hh, 0:ww]
    pts = np.stack([x0 + (xx + 0.5) * B / 16, np.zeros_like(xx, float), z0 + (yy + 0.5) * B / 16], -1) - tgt
    dpt = -(pts @ cam.T)[..., 2]
    side = np.abs((pts @ cam.T)[..., 0])
    k = np.clip((dpt - near) / (far - near), 0, 1) ** 0.7
    k = np.maximum(k, np.clip((side - 70) / 60, 0, 1) * 0.9)
    k = np.maximum(k, np.clip((-dpt - 40) / 60, 0, 1) * 0.6)
    img[..., :3] = img[..., :3] * (1 - k[..., None]) + FOG * k[..., None]


def compose(out, yaw=-20, pitch=22, size=(640, 800)):
    knight = model.build_parts()
    kv = fit(knight, size, pitch, margin=0.78)
    world = []
    floor = floor_part(-30, 30, -30, 30)
    fx, fz = kv["foot"]
    cast_shadow(floor, knight)
    tgt = np.asarray(kv["target"])
    light_and_fog(world, None, yaw, pitch, tgt, 15, 95)
    fog_floor(floor, yaw, pitch, tgt, 15, 95)
    world = [floor] + world
    W, H = size
    color, alpha, ss = render(world + knight, yaw, pitch, kv["scale"], size, 0, target=tgt)
    yy = np.linspace(0, 1, H * ss)[:, None, None]
    sky = (np.array((0.025, 0.014, 0.013)) * (1 - yy) + FOG * yy) * np.ones((1, W * ss, 3))
    yy3, xx3 = np.mgrid[0:H * ss, 0:W * ss]
    halo = np.exp(-(((xx3 - W * ss * 0.58) / (W * ss * 0.38)) ** 2 + ((yy3 - H * ss * 0.36) / (H * ss * 0.3)) ** 2))
    bt = np.tile(np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0, (H * ss // 4 + 1, W * ss // 4 + 1))[:H * ss, :W * ss]
    halo = np.floor(halo * 5 + bt) / 5
    sky = sky + np.array((0.16, 0.035, 0.025))[None, None] * halo[..., None]
    sky[alpha] = color[alpha]
    yy2, xx2 = np.mgrid[0:H * ss, 0:W * ss]
    r = np.hypot((xx2 - W * ss / 2) / (W * ss * 0.62), (yy2 - H * ss * 0.5) / (H * ss * 0.62))
    sky *= (1 - 0.55 * np.clip(r - 0.6, 0, 1) * 2.2).clip(0.35, 1)[..., None]
    img = np.array(Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8)).resize(size, Image.BOX)).astype(float)
    mist(img, seed=31)
    dust(img, seed=21)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out)


def mist(img, seed, t=0.0):
    rng = np.random.default_rng(seed)
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    field = np.zeros((H, W))
    for i in range(7):
        cy = rng.uniform(H * 0.25, H * 0.7)
        amp = rng.uniform(18, 40)
        ph = rng.uniform(0, 6.28)
        wl = rng.uniform(140, 320)
        band = cy + amp * np.sin(xx / wl * 6.28 + ph + t * 6.28)
        field += np.exp(-((yy - band) / rng.uniform(20, 45)) ** 2) * rng.uniform(0.4, 0.9)
    field = np.clip(field, 0, 1)
    b = np.tile(np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0, (H // 4 + 1, W // 4 + 1))[:H, :W]
    q = np.floor(field * 4 + b) / 4
    q = np.repeat(np.repeat(q[::2, ::2], 2, 0), 2, 1)[:H, :W]
    col = FOG * 255 * 1.5
    img[:] = img * (1 - 0.35 * q[..., None]) + col * 0.35 * q[..., None]


def dust(img, seed, t=0.0):
    rng = np.random.default_rng(seed)
    H, W = img.shape[:2]
    for i in range(140):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        vx, vy = rng.uniform(-6, 6), rng.uniform(-14, -4)
        x = (x0 + vx * t * 10 + 6 * np.sin(t * 6.28 + i)) % W
        y = (y0 + vy * t * 10) % H
        sz = 2 if rng.random() < 0.7 else 4
        a = rng.uniform(0.18, 0.45)
        col = np.array((150, 110, 96))
        xi, yi = int(x) // 2 * 2, int(y) // 2 * 2
        img[yi:yi + sz, xi:xi + sz] = img[yi:yi + sz, xi:xi + sz] * (1 - a) + col * a



if __name__ == "__main__":
    compose(sys.argv[1] if len(sys.argv) > 1 else "world.png")
