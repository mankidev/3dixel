import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "core"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import model
from anim import track
from render import fit, points, save_gif, shot

OUT = os.path.dirname(os.path.abspath(__file__))
N = 60
TILT = [((0, 3, 0), (0, 0, -10))]
KEYS = [(0, -0.2), (0.2, -0.2), (0.7, 1.2), (1.0, 1.2)]
SIZE = (420, 560)


def tilted(pose=None):
    parts = model.build_parts(pose)
    for p in parts:
        p["tr"] = list(p["tr"]) + TILT
    return parts


rest = tilted()
print("min y", round(float(points(rest)[:, 1].min()), 2))
view = dict(fit(rest, SIZE, 20), shadow=0.3)
frames = [shot(tilted({"shine": track(i / N, KEYS)}), -35 + 360 * i / N, SIZE, view) for i in range(N)]
save_gif(frames, os.path.join(OUT, "turn.gif"), 60)
pick = list(range(0, N, 5))
tw, th = SIZE[0] // 2, SIZE[1] // 2
sheet = Image.new("RGB", (tw * 6, th * ((len(pick) + 5) // 6)))
for j, i in enumerate(pick):
    sheet.paste(frames[i].resize((tw, th)), ((j % 6) * tw, (j // 6) * th))
sheet.save(os.path.join(OUT, "turn_sheet.png"))
