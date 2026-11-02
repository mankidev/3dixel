---
name: 3dixel
description: Builds Blockbench-style 3D models (low cube count, pixel textures painted in code) from a description, renders previews, and checks every step with the user. Use whenever the user asks for a Blockbench model, a Minecraft-style mob, or any blocky 3D creature or prop.
---

# 3dixel

You build the model in code: boxes, pivots and textures painted pixel by pixel. You do not have Blockbench, so you see the model only through the core renderer. Show every step to the user and fix what they say before you add more.

## Showing an image

1. Render with the core (`render.py`) into the project folder.
2. Open the PNG yourself with the Read tool and look at it before the user does.
3. Give the user the full path of each file.

Read shows only the first frame of a GIF. Check motion on the numbered frame sheet.

## Use the core

`core/` holds everything a model needs. Start every model from `examples/rabbit/model.py`, not from an empty file.

- `kit.py`
  - `part(f, t, tex, tr)`: one box from corner `f` to corner `t`. `tex` maps each face (`front back right left top bottom`) to an image. `tr` is a list of `(pivot, (rx, ry, rz))` rotations, innermost first.
  - `mirror(p)`: the same part on the other side (x flipped, textures flipped).
  - `face_size`, `shaded_idx`, `side_bands`, `to_rgb`, `hexc`: palette index textures with top light and sides darker toward the bottom.
  - `mixels(parts)`: lists parts whose size is not whole or whose texture size does not match the face.
  - `chain`, `solve_leg`: a leg as a chain of segments; one joint angle is solved so the foot touches the ground. `chain` takes an optional `hairfn(k, f, t, tr)` that returns extra parts (one part or a list) for each segment, for hair cards or tip spikes.
  - Fur: `weave_fur`, `lock_fur`, `tip_fur` return `(idx, alpha)`. `direction` (`right up left down`) is where the hair tips point. `paint(idx, alpha, pal)` gives RGB, or RGBA when part of it is cut out.
  - Hair planes for shaggy animals only: `hair_card`, `hair_plane`, `fringe_plane`, `strands`, `flow`, `fur`.
  - Scales: `domed_scales` (body and back: uneven domed scales with a bright core in the light), `keeled_scales` (legs and tail: long overlapping scales with a ridge, `direction` is where they point), `belly_scutes` (belly and throat: plates across the body, light in the middle, dark at the sides). They return `(idx, alpha)` for a palette of `n` tones (dark to light), lit by `light_map`. Pass your own `light` map to match the lighting of the part.
  - `encrusted_shell`: old crusted shell (growth bands that follow the shape, raised bumps, dark pits, a broken crust on top) for crabs, turtles, rock golems. Use it on large faces; on small parts it turns into noise.
- `render.py`
  - `python render.py <model_folder> [--gif] [--closeup x,y,z,r] [--name n] [--out dir]` writes `<name>_preview.png`, `<name>_views.png` (front, side, back), and optionally a turntable GIF and a close-up.
  - The model folder needs `model.py` with `build_parts()`.
  - Framing is automatic. The model always fills the frame, so the image does not show real size.
- `anim.py`: `track(t, keys)` with smoothstep keyframes, and `loop(build_parts, pose_at, out, name)` for an idle GIF and a frame sheet.

Textures with `alpha > 1.5` are drawn unlit (glowing eyes, cracks). Parts with `"double": True` are drawn from both sides (planes).

## 1. Before building

- Ask what the animal or object is and what style the user wants, if it is not clear.
- Think about the real animal from the side first: how long the body is compared to its height, where the highest point of the back is, where the head sits.
- Pick the size from the real scale: 16 units = 1 block. A rabbit body is about 8 units long.
- Count the cubes before you write code.

## 2. Shape

- Few cubes. A simple mob is 12 to 30 cubes: one cube per body part, two or three segments per leg at most.
- Eyes, teeth, patterns and edges go in the texture, not in extra cubes. If a cube does not change the silhouette, leave it out.
- Box sizes are whole numbers and at least 1. One texture pixel is one unit. Positions and pivots may be halves.
- No mixels: the whole model uses one pixel size. No cube smaller than one unit (teeth, claws, spikes as tiny cubes), no half-unit length, no face texture denser than the face. Small details such as teeth go in the texture of the jaw.
- No layers: do not stack a slightly smaller box on top of a big one to fake roundness. One box per body part. Roundness comes from the texture, from rotating the box, and from separate real parts (head, jaw, thigh).
- Slopes and curves come from rotated boxes, not from stairs of boxes.
- Four-legged animals: the body is long, low and level. The head sits in front of the body, not on top of it. A tall body with the head on top reads as a bird.
- Small animals: a slightly small head and a 1-pixel eye.
- Exaggerate what makes the animal: long ears, big claws, a heavy jaw.
- Legs must show. A wild boar's legs are about 40% of its shoulder height. A box body on short, thin legs reads as a crate or a cow.
- A hump (boar, bison): split the body into a front box and a rear box and tilt the rear one down. One level box gives a flat back.
- Tusks, horns and claws: two segments, a thick root and a thin tip, bent the way the real one curves. One small straight cube reads as a stub.
- Two dark pixels side by side merge into one block: two nostrils next to each other look like one hole. Make the part an odd width so one pixel sits between them.
- When one part grows, check the whole body again. Giant legs on an unchanged body make the body read as missing; scale the body and the claws with them.
- Crab claws are held in front of the mouth and folded inward, fingers pointing toward the middle. Claws sticking straight forward read as a forklift.

## 3. Texture

- Small palette with hue shift: shadows move toward blue or purple, light toward warm. A white animal gets cool blue shadows.
- No random speckle noise. Patterns are placed on purpose.
- No frame on the edge of a face. The texture runs across faces; the renderer gives the light difference.
- Top and front faces are lighter than bottom and back. Side faces go darker from top to bottom.
- One strong accent on a pale body draws the eye: an eye, a crack, a crystal.
- Colors are not fixed. The texture functions return palette indices; the palettes in the examples are only examples. Build the palette from what the user asks for (hue-shifted, dark to light) and pass it in.
- Thin line sprites on planes (hooks, curls, antennae, vines) are pixel perfect: no L-shaped double corners. Use straight runs with one diagonal step at each corner; a line made only of diagonal steps looks like floating dots in 3D. A sprite must never be cut by the edge of its plane, or its inner end floats.
- Patterned textures (scales, plates, armor) are drawn with a light map, not as a flat repeat. The face goes from a lit corner to a shadow corner with hue shift. Details are strong in the light and fade in the shadow, where seams almost disappear. Each unit (a scale) is uneven in size and shaded like a dome. The same pattern repeated at the same contrast looks like wallpaper.
- A wild or dark animal keeps a low base tone and no bright blotches. Light fur makes it look tame.
- Hard parts (tusk, horn, claw, beak) are never one flat color: a gradient along the length (stained root, light tip), a dark growth ring near the root, a dark ridge line, a darker underside.
- Chitin (crab and insect leg tips, claw fingers): gradient from shell tone at the root to dark at the tip, two dark rings near the root, fine streaks running along the length (never across, which reads as plaid), a light shine line on the lit edge that fades toward the tip, a darker underside.
- Everything you add besides the base texture gets the same care: cards (teeth, spikes, tips, crests) and small cubes get a lit side and a shadow side, a gradient from root to tip and a highlight edge. A one-color card looks like a paper cutout.
- Sharp parts (teeth, claw tips, spikes, leg points) are cards, drawn as stepped full-pixel shapes. A point seen only edge-on disappears; use two crossed planes so it shows from every side.
- A card takes the palette of the part it sits on: teeth on a purple-black finger use the light tones of the same purple-black palette, spikes on a gray palm use the shell grays. When a card does not match, change the card, not the part.
- No face stays flat-shaded. Every part gets a texture that fits the animal: plates and sutures under a crab, wall plates and a crater on a barnacle, rings on an eye stalk, crust on the legs. A plain banded face looks bare next to a textured one.
- Plants and corals on a body are crossed planes with a branching full-pixel sprite; a one-pixel twig reads as an antenna. Give the trunk two pixels and the tips a lighter tone.
- A glowing eye glows only in the pupil (the front and outer face). A cube that glows on every face reads as a gem.
- Bare skin is not flat either. Fur runs over the snout bridge up to the bare tip; the tip gets a lighter rim and wrinkle lines behind it. Tilt the snout a little down so the profile narrows toward the tip.

## 4. Face and expression

- An angry face is a brow slanting down toward the nose over a dark eye.
- A brow painted in the texture disappears on dark fur. Use geometry: a hair card (`tip_fur`, dark root, lighter tips, leaning out from the face) on a bristly animal, a slanted 1-unit cube on a smooth one.
- Keep the eye black unless the user asks for a color.

## 5. Fur

- Body fur: `weave_fur`, short strands in rows that follow a soft light and dark field. Hair runs from head to tail; on legs it points down.
- Chest and neck: `lock_fur`, overlapping locks that are dark at the root and light at the tip.
- Tail and mane tips: `tip_fur`, dark at the root, light at the tip, with a ragged see-through end.
- On a white or short-haired animal, keep fur contrast low: base tone plus `weave_fur(lo=-1, hi=1)`.
- Fur must be neither noisy nor grid-like. Every dash with its own random length and tone looks noisy. Fixed bricks and checkers look like woven cloth.
- Hair cards and fringe planes only for animals whose hair breaks the silhouette (tarantula, hedgehog, shaggy wolf mane). A rabbit or a short-haired dog gets texture only.
- Never put a short, thin, ragged hair card on top of the head. Seen from above or the front it reads as a dark slit, not as hair. A head crest must be a full-pixel card: every bristle a whole pixel column, opaque, with a stepped outline drawn on purpose (no random ragged edge), root in the body tone, tips lighter.
- A crest along the back also starts in the body tone. A root in the darkest tone reads as a crack along the spine.
- When you offer fur options, make them differ in method (strand layout, direction, locks or cards), not only in noise settings.

## 6. Check before you show

- Look at the preview and all three views yourself. The side view shows most of the posture mistakes.
- Compare against the rules above: cube count, layers, head position, proportions, noise, face frames.
- Run `kit.mixels(build_parts())`. It must return an empty list; each entry is a part with a non-whole size or a texture that does not match its face.
- Look at the face up close (`render.closeup`, from the side as well as the front): eyes, brows, nostrils and tusks are too small to judge in the full preview.
- Aim close-ups at the real position of the part: build only that part, take `render.points(parts)` and use the middle of its bounds. A guessed target misses rotated parts such as claws.
- Fix what you find, then show the user and say what you changed.
- When the user asks for a change, keep the old `model.py` as `model_vN.py` so you can go back.
