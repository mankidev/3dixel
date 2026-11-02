import os
from PIL import Image, ImageDraw, ImageFont
from render import BG, fit, shot


def ease(u):
    return u * u * (3 - 2 * u)


def track(t, keys):
    t %= 1.0
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return v0 + (v1 - v0) * ease(u)
    return keys[-1][1]


def label_font(size=20):
    for path in ("/system/fonts/Roboto-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def loop(build_parts, pose_at, out, name, n=48, delay=80, yaw=-35, size=(640, 480), pitch=24, every=4):
    view = fit(build_parts(), size, pitch)
    frames = [shot(build_parts(pose_at(i / n)), yaw, size, view) for i in range(n)]
    frames[0].save(os.path.join(out, f"{name}_idle.gif"), save_all=True, append_images=frames[1:], duration=delay, loop=0)
    font = label_font()
    pick = sorted(set(range(0, n, every)) | {n - 1})
    tw, th = size[0] // 2, size[1] // 2
    sheet = Image.new("RGB", (tw * 4, th * ((len(pick) + 3) // 4)), BG)
    for j, i in enumerate(pick):
        im = frames[i].resize((tw, th))
        ImageDraw.Draw(im).text((8, 6), str(i), fill=(230, 230, 230), font=font)
        sheet.paste(im, ((j % 4) * tw, (j // 4) * th))
    sheet.save(os.path.join(out, f"{name}_idle_sheet.png"))
    return frames
