import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
import model
import walk
import world
from kit import part
from render import fit, points, render

N = int(os.environ.get("KN_FRAMES", 96))
CYCLES = 4
SIZE = tuple(int(v) for v in os.environ.get("KN_SIZE", "640,800").split(","))
YAW, PITCH = -20, 22
PERIOD = CYCLES * walk.SPEED
PERIOD_PX = int(round(PERIOD * 16 / world.B))


def periodic_noise(H, W, cell, rng):
    gh, gw = H // cell, W // cell + 2
    g = rng.random((gh, gw))
    yy, xx = np.mgrid[0:H, 0:W] / cell
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = yy - y0, xx - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % gh
    y0 = y0 % gh
    a, b = g[y0, x0], g[y0, x0 + 1]
    c, d = g[y1, x0], g[y1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def floor_tile(nx, seed=904):
    rng = np.random.default_rng(seed)
    H, W = PERIOD_PX, nx * 16
    base = 4 + world.LIGHT["top"]
    large = periodic_noise(H, W, H // 2, rng)
    mid = periodic_noise(H, W, H // 8, rng)
    small = periodic_noise(H, W, max(2, H // 32), rng)
    v = base - 0.8 + (large - 0.5) * 1.8 + (mid - 0.5) * 1.3 + (small - 0.5) * 0.5
    idx = world.band_dither(v)
    speck = periodic_noise(H, W, 2, rng)
    idx = np.where(speck > 0.82, idx + 1, np.where(speck < 0.16, idx - 1, idx))
    return world.rgba(idx, world.DIRT)


def frame(i, tile, view, nx, reps):
    t = i / N
    g = walk.build((CYCLES * t) % 1.0)
    knight = [q for k in g for q in g[k]]
    shift = (PERIOD * t) % PERIOD
    top = np.concatenate([tile] * reps, 0).copy()
    z0 = -reps * PERIOD / 2 - shift
    x0 = -nx * world.B / 2
    floor = part((x0, -world.B, z0), (-x0, 0, z0 + reps * PERIOD), {"top": top})
    world.cast_shadow(floor, knight)
    tgt = np.asarray(view["target"])
    world.fog_floor(floor, YAW, PITCH, tgt, 15, 95)
    W, H = SIZE
    color, alpha, ss = render([floor] + knight, YAW, PITCH, view["scale"], SIZE, 0, target=tgt)
    yy = np.linspace(0, 1, H * ss)[:, None, None]
    sky = (np.array((0.025, 0.014, 0.013)) * (1 - yy) + world.FOG * yy) * np.ones((1, W * ss, 3))
    yy3, xx3 = np.mgrid[0:H * ss, 0:W * ss]
    halo = np.exp(-(((xx3 - W * ss * 0.58) / (W * ss * 0.38)) ** 2 + ((yy3 - H * ss * 0.36) / (H * ss * 0.3)) ** 2))
    bt = np.tile(np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0, (H * ss // 4 + 1, W * ss // 4 + 1))[:H * ss, :W * ss]
    halo = np.floor(halo * 5 + bt) / 5
    sky = sky + np.array((0.16, 0.035, 0.025))[None, None] * halo[..., None]
    sky[alpha] = color[alpha]
    r = np.hypot((xx3 - W * ss / 2) / (W * ss * 0.62), (yy3 - H * ss * 0.5) / (H * ss * 0.62))
    sky *= (1 - 0.55 * np.clip(r - 0.6, 0, 1) * 2.2).clip(0.35, 1)[..., None]
    img = np.array(Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8)).resize(SIZE, Image.BOX)).astype(float)
    world.mist(img, seed=31, t=t)
    dust(img, seed=21, t=t)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def dust(img, seed, t):
    rng = np.random.default_rng(seed)
    H, W = img.shape[:2]
    k = W / 640
    for i in range(170):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        vy = int(rng.choice([-2, -3, -3, -4, -5]))
        vx = int(rng.choice([-1, 0, 0, 1]))
        wob = int(rng.integers(1, 4))
        ph = rng.uniform(0, 6.28)
        x = (x0 + vx * t * W + 10 * k * np.sin(6.28 * wob * t + ph)) % W
        y = (y0 + vy * t * H) % H
        sz = max(1, int(round((2 if rng.random() < 0.25 else 1) * k * 1.5)))
        a = rng.uniform(0.12, 0.3)
        col = np.array((150, 110, 96))
        xi, yi = int(x), int(y)
        img[yi:yi + sz, xi:xi + sz] = img[yi:yi + sz, xi:xi + sz] * (1 - a) + col * a


def main():
    a, b = int(sys.argv[1]), int(sys.argv[2])
    out = sys.argv[3]
    os.makedirs(out, exist_ok=True)
    rest = model.build_parts()
    view = fit(rest, SIZE, PITCH, margin=0.78)
    if SIZE[0] < 640:
        pass
    nx = 60
    tile = floor_tile(nx)
    reps = int(np.ceil(60 * world.B / PERIOD)) + 2
    for i in range(a, b):
        frame(i, tile, view, nx, reps).save(os.path.join(out, f"f{i:03d}.png"))
        print("frame", i, flush=True)


if __name__ == "__main__":
    main()
