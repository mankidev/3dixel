---
name: 3dixel
description: Builds Blockbench-style 3D models (low cube count, pixel textures painted in code) from a description, renders previews, and checks every step with the user. Use whenever the user asks for a Blockbench model, a Minecraft-style mob, or any blocky 3D creature, prop or weapon.
---

# 3dixel

You are a modeler whose work competes with the best Blockbench models on Sketchfab. Before you show any image, put it side by side with the reference and list the differences.

You build the model in code: boxes, pivots and textures painted pixel by pixel. You do not have Blockbench, so you see the model only through the core renderer. Show every step to the user and fix what they say before you add more.

## Showing an image

1. Keep code and images apart: every `.py` file (model, old versions, check scripts) goes in `src/` inside the project folder, and the project folder itself holds only images. Render with the core into the project folder: `python render.py src --out . --name vN`.
2. Open the PNG yourself with the Read tool and look at it before the user does.
3. Give the user the full path of each file.

Read shows only the first frame of a GIF. Check motion on the numbered frame sheet.

## Use the core

`core/` holds everything a model needs. Start every model from an example, not from an empty file: `examples/rabbit/model.py` for animals, `examples/crimson-sword/model.py` for weapons and props, `examples/double-axe/model.py` for an axe (a blade outline drawn as row spans, an unlit cutting edge, a haft of rotated segments with a bent butt), `examples/ember-knight/` for armored humanoids, poses, a walk cycle and a block scene, `examples/pale-stalker/` for a hairy spider-like creature with lying hair cards, sunken eyes and an IK idle in a dark scene, `examples/flesh-hound/` for a hairless four-legged creature with quill cards, a hunched creature stance, a posable head and tail and a four-leg IK walk, `examples/grin-wraith/` for a heavy seated beast with a sloped head roof, a grin cut into the face, plates turned toward the middle, a spiked fur collar, glowing hands and feet with separate fingers and a dark-scene idle with bloom on the eyes, `examples/void-dragon/` for a hovering winged dragon with a wedge head of many rods, glowing wing membranes cut from triangle cards, a bloom pass (`glow.py`) and an articulated wing-flap idle (`anim_idle.py`). The dragon example also holds `beam(p0, p1, sx, sz, hint, ...)` (a box between two points with a chosen roll), `sprite_card` (a card in any frame), `membrane` and a robust `euler` for turning a basis into rotations. The sword example also holds helpers you can copy: `rod(p0, p1, th, ...)` (a box between two points with tube shading), `chain_rods` (a curved horn or tentacle from a list of points), `line_sprite` (a pixel-perfect line card), `crystal` (chevron facets with lit edges), `glow` (top tones drawn unlit), a shine pose, and `anim_turn.py` (tilted 360 turntable).

- `kit.py`
  - `part(f, t, tex, tr)`: one box from corner `f` to corner `t`. `tex` maps each face (`front back right left top bottom`) to an image. `tr` is a list of `(pivot, (rx, ry, rz))` rotations, innermost first.
  - `mirror(p)`: the same part on the other side (x flipped, textures flipped).
  - `face_size`, `shaded_idx`, `side_bands`, `to_rgb`, `hexc`: palette index textures with top light and sides darker toward the bottom. `face_size(f, t, face, density)` and `mixels(parts, density)` take a texture density in pixels per unit (default 1).
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
  - The ground shadow is centered on the median of the parts near the ground (feet, hems), so a long weapon does not pull it away. It is an ellipse sized from those parts (`--shadow`, default 0.85). Long legs or claws spread out make it too big: the shadow belongs under the body, so lower it (0.5 for a crab or spider with long legs). `anim.loop` takes the same `shadow=`.
- `anim.py`: `track(t, keys)` with smoothstep keyframes, and `loop(build_parts, pose_at, out, name, shadow=0.85)` for an idle GIF and a frame sheet. For animation, `build_parts(pose)` must take a pose dict whose default gives the rest pose; build the left and right side separately so they can move out of step.

Where two parts overlap in the same plane (equal-thickness segments of a chain lying in one plane, a card on a card), the renderer lets the later part in the list win, so previews do not flicker. Blockbench and the game do not: there the shared plane flickers (z-fighting) at every joint. Before export, give one of the two parts a different thickness or move it 0.01 out. A double-sided part that has both a front and a back texture draws only the side facing the camera.

Textures with `alpha > 1.5` are drawn unlit (glowing eyes, cracks). Parts with `"double": True` are drawn from both sides (planes).

## 1. Before building

- Ask what the animal or object is and what style the user wants, if it is not clear.
- Think about the real animal from the side first: how long the body is compared to its height, where the highest point of the back is, where the head sits.
- Pick the size from the real scale: 16 units = 1 block. A rabbit body is about 8 units long.
- "Giant" or "huge" means at least 5 to 6 blocks (80 to 96 units) in its largest size. Measure the bounds with `render.points(build_parts())` before showing, since the render always fills the frame.
- Count the cubes before you write code.
- When the user names a creature you cannot picture exactly (a monster from a game, a "void worm"), ask for a reference or concept image before the first blockout. A guessed design gets thrown away.
- When the reference is a character from a game or a film, do not rebuild it. Keep the archetype and change what identifies it (helmet, plume, weapon head), or ask for another reference.
- A giant crawler lies flat on the ground by default. Do not rear its head up like a snake unless the user asks.
- Read the reference part by part before the blockout: crop each region at twice its size and write down every limb and where it is. A leg folded across the front read as an arm, and a sitting rump read as a stump fading into smoke; the whole model was rebuilt.
- A Sketchfab model that is not offered for download is not ripped from the viewer. Work from its thumbnail and ask the user for screenshots from other angles; one view hid that a hanging column was the tail, not a leg. Free models of the same kind may be downloaded (CC licensed, `api.sketchfab.com/v3/models/<uid>/download` with the user's token) to study proportions, but use only the ones the user accepts as reference.
- Compare part by part with the reference at the same angle: render the part (head, wing) from the angle of the reference photo, mirror it if it faces the other way, and put both in one image. Answer honestly when the user asks whether it looks alike.
- Measure proportions on the reference as ratios before changing sizes: wing half-span against the height from head to tail tip, head length against chest width, tail length against the upper body. A part that looks too small is often another part that is too big (a long tail made big wings look small).

## 2. Shape

- Few cubes. A simple mob is 12 to 30 cubes: one cube per body part, two or three segments per leg at most.
- Eyes, patterns and edges go in the texture, not in extra cubes. If a cube does not change the silhouette, leave it out.
- Box sizes are whole numbers and at least 1. One texture pixel is one unit. Positions and pivots may be halves.
- No mixels: the whole model uses one pixel size. No cube smaller than one unit (teeth, claws, spikes as tiny cubes), no half-unit length, no face texture denser than the face.
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
- Spider legs arch: the femur rises up and out to a knee above the body, the tibia drops to the ground outside the body. Legs that hang straight down from the body read as stilts.
- A spider mouth is two chelicerae under the eyes: each a hairy root box and a narrower tip box, splayed into a V and darker than the body, with a curved fang card at each tip folding inward. A dark mouth shape painted on a jaw box read as a smile.
- A joint part (a knee or elbow knob) rotates around its own center. Rotated around the start of the segment before it, it drifts off the joint and floats in the air.
- A card that ends at a fixed point (a foot spike reaching the ground) keeps a fixed length. Sized from the pose, it stretches into a thin line when the leg lifts.
- Long segmented bodies (worms, centipedes, serpents) are a chain of rings, each placed at the end of the last with its own yaw and pitch. The rings must read as separate blocks: do not sink one deep into the next. Leave a small gap and fill it with a thinner joint box, the soft tissue between plates. Use about one ring per 1 to 1.5 body thickness; fewer, longer rings read as train cars or crates.
- Keep the cube count low by leaving out parts that do not change the silhouette, never by merging rings or jaw segments that do. A worm with 8 long rings and one-box jaws looked worse than one with 18 rings and two-part jaws.
- A tail tapers slowly. The tip of a giant worm stays at least a third as thick as its thickest ring, or the tail reads as a string.
- Spikes along a big body stay short: back spikes about half to two thirds of the body thickness, side spikes about a third. The base is wide (5 to 9 pixels) and narrows evenly to one pixel; a spike that is one pixel wide for half its length reads as a stick or an antenna.
- Nothing goes below the ground. Open jaws and lowered parts included, the lowest point of `render.points(build_parts())` must be at 0 or above.
- When the head and the body stop matching, scale the body, not the head the user approved: scale the body points around the hip with one helper (`B(v)` for points, `bsz(n)` for whole-number sizes) and move the head to the new neck end.
- A creature that only resembles an animal does not stand like it. For a dog-like monster: the head hangs below the shoulder line and reaches forward, the back peaks where the chest box meets the rear box (the chest tilted front down around its back top edge, the rear tilted back down around its front top edge), the front legs splay out from the shoulder and the hind legs crouch. An upright dog stance reads as a pet.
- A monster's body is big next to its head: the user grew it three times, to a chest about twice the head width and a body three times the head length, with a clear gap between the front and hind legs. Legs grow with it (thick upper segments, legs about half the shoulder height); legs left at the old size read as weak and short.
- Paws are about as wide as the leg above them. A wide flat paw block reads as an elephant foot or a slipper.
- A tail on a heavy body starts inside the rear box with a root about two thirds of the rear box height and tapers from there. A thin tail stuck on the back face reads as a stick.
- A box that does not read as a body part goes. A shoulder blade box sticking out of the chest read as a stray plank on the leg.
- A boxy head gets a roof: four slabs hinged on the top edges and tilted about 35 degrees inward, with a small cap over the gap between them. The head reads rounded from every side without stacking a smaller box.
- Chest and belly muscles are plates turned toward the middle on a narrower core (pecs about 16 degrees, belly plates about 10 and tucked under at the bottom). The waist stays narrower than the ribcage and the ribcage narrower than the shoulder collar.
- A heavy seated beast: the rump is a core box inside a ring of eight plates tilted out at the bottom, so it widens to the ground like a skirt instead of a crate. One leg folds forward across the body with the foot in front, the other folds under it.
- Lobes on the sides of a head stay small (about a third of the head width) and turn outward. Big flat lobes with a spiral read as loudspeakers, and a head that is wider than the shoulders crushes the body.
- A spiky fur collar is a ring of cards with a spiked top edge around the top of the shoulder box, tilted out. Thin single quills there read as whiskers.

## 3. Texture

- Small palette with hue shift: shadows move toward blue or purple, light toward warm. A white animal gets cool blue shadows.
- Keep the hue and saturation even through the middle of the palette. Legs are mostly side faces and land in the mid tones; when those were a saturated red and the lit tones salmon, the legs looked like they came from another model.
- No random speckle noise. Patterns are placed on purpose. Keep facet and engraving contrast at one tone up or down, and put bright sparkle pixels on some facet edges, not all of them; strong steps everywhere read as noise.
- One pixel is one unit, and it must read that way on every face. `shaded_idx` alone splits a long side into two or three flat bands; on a 22-unit blade each band is 7 units tall and reads as one giant pixel next to the 1-unit pixels of cards and small parts. `shaded_idx` is only a base, never the finished texture, not even in a blockout. Every face gets detail drawn at the 1-unit scale (facets, edges, cracks, wear, stepped light) so no flat area of one color is much bigger than the detail around it.
- No frame on the edge of a face. The texture runs across faces; the renderer gives the light difference.
- Top and front faces are lighter than bottom and back. Side faces go darker from top to bottom.
- One strong accent on a pale body draws the eye: an eye, a crack, a crystal.
- Colors are not fixed. The texture functions return palette indices; the palettes in the examples are only examples. Build the palette from what the user asks for (hue-shifted, dark to light) and pass it in.
- Thin line sprites on planes (hooks, curls, antennae, vines) are pixel perfect: no L-shaped double corners. Round curls drawn with diagonal steps look good. A sprite must never be cut by the edge of its plane: the cut side disappears and the inner end of a curl floats in the air. Place each sprite fully inside its plane.
- Patterned textures (scales, plates, armor) are drawn with a light map, not as a flat repeat. The face goes from a lit corner to a shadow corner with hue shift. Details are strong in the light and fade in the shadow, where seams almost disappear. Each unit (a scale) is uneven in size and shaded like a dome. The same pattern repeated at the same contrast looks like wallpaper.
- A wild or dark animal keeps a low base tone and no bright blotches. Light fur makes it look tame.
- Hard parts (tusk, horn, claw, beak) are never one flat color: a gradient along the length (stained root, light tip), a dark growth ring near the root, a dark ridge line, a darker underside.
- Chitin (crab and insect leg tips, claw fingers): gradient from shell tone at the root to dark at the tip, two dark rings near the root, fine streaks running along the length (never across, which reads as plaid), a light shine line on the lit edge that fades toward the tip, a darker underside.
- Everything you add besides the base texture gets the same care: cards (teeth, spikes, tips, crests) and small cubes get a lit side and a shadow side, a gradient from root to tip and a highlight edge. A one-color card looks like a paper cutout.
- Teeth are cards along the edge of the mouth, at the model's pixel size: a plane just inside the lip on each side of the upper and lower jaw, teeth 1 pixel wide with a 1-pixel gap, fangs 2 or 3 pixels tall, the rest 1. Open the jaw enough that both rows show. Not texture only, not tiny cubes.
- On a sloped snout the tooth card follows the lip: build it in the frame of the snout rod (along its axis, across its height) and put the toothed rows below the lip line, not inside the rod. Check the card corners against the rod corners in numbers; teeth placed inside the snout showed above it.
- A mouth always has front teeth: a forward-facing card at the tip of the upper and lower jaw, fangs at the corners and small teeth between. Side rows alone read as a toothless front.
- A card must sit in front of the face it belongs to. Teeth placed behind the front plane of the jaw were hidden in every view.
- Every sharp edge or point is a card, always: sword and axe edges, blade tips, teeth, claw tips, spikes, leg points. A box never makes a cutting edge. Sharp parts are cards, drawn as stepped full-pixel shapes. A point seen only edge-on disappears; use two crossed planes so it shows from every side.
- Quills and spines on a back are single cards (the user turned down boxes and crossed pairs there): few of them with clear gaps, about 5 units apart. Keep the card almost upright and draw the backward sweep in the sprite, one pixel back per row. A strongly tilted card breaks into staircases and reads as messy hair. Width 4, 3, 2, 1 from root to tip; 3, 2, 1 read too thin. The root is as dark as the quill, and the body texture under each root gets a dark socket with a darker ring, so the quill grows out of the skin.
- Claws are cards too: a hook sprite on a side card at the toe plus a small front card, so they show from the side and the front.
- A card takes the palette of the part it sits on: teeth on a purple-black finger use the light tones of the same purple-black palette, spikes on a gray palm use the shell grays. When a card does not match, change the card, not the part.
- No face stays flat-shaded. Every part gets a texture that fits the animal: plates and sutures under a crab, wall plates and a crater on a barnacle, rings on an eye stalk, crust on the legs. A plain banded face looks bare next to a textured one.
- Never a flat texture, with no exception: every face of every part, including legs, hooves, hands, inner and back faces, bottoms and small parts. A gradient alone counts as flat. Legs get muscle, a bone ridge on the shin, a tendon at the back, a knee cap; hooves get growth rings, a split and a shine line. Before showing, render a close-up of each limb and name the detail on every face; a face with nothing to name is not done.
- Plants and corals on a body are crossed planes with a branching full-pixel sprite; a one-pixel twig reads as an antenna. Give the trunk two pixels and the tips a lighter tone.
- A glowing eye glows only in the pupil (the front and outer face). A cube that glows on every face reads as a gem.
- Glow is an accent. Glowing whole edges, whole spikes or every seam looks like neon. Keep the shell dark and put the glow in the joints between plates and in the last pixels of spike tips.
- A "void" or shadow creature stays near black: even its lightest shell tone is a dark blue-gray, not a mid tone.
- The inside of a mouth uses the creature's own palette: flesh in a slightly lighter, more saturated version of the body hue, teeth in the light tones of the same palette. Red flesh and white bone in a dark blue body looked pasted on.
- Round patterns (a throat, a sucker, a ring of teeth) use the real distance from the center (`hypot`), not the larger of x and y. Square rings and dotted rings look like a circuit board. A few large teeth read better than many single pixels, which turn into speckle.
- Bare skin is not flat either. Fur runs over the snout bridge up to the bare tip; the tip gets a lighter rim and wrinkle lines behind it. Tilt the snout a little down so the profile narrows toward the tip.
- A dark beast stays near black: its lightest body tone about #48504e. Compare the mean lightness with the reference (visual-taste) before showing; mid grays read as a stone statue.
- Fur on a dark beast is `lock_fur`. Domed scales read as gravel, and small stamped curls turn into noise at preview size.
- A top face under an overhang (a belly plate under the pecs) gets darker by hand. Lit by the renderer, it reads as a pale ledge.

## 4. Face and expression

- An angry face is a brow slanting down toward the nose over a dark eye.
- A brow painted in the texture disappears on dark fur. Use geometry: a hair card (`tip_fur`, dark root, lighter tips, leaning out from the face) on a bristly animal, a slanted 1-unit cube on a smooth one.
- Keep the eye black unless the user asks for a color.
- Sunken eyes: cut holes in the face texture (alpha 0), put the eye cube one unit behind the face and build the socket walls as separate double-sided planes. A double-sided box does not draw its inner walls when the opposite face has a texture. Eyes that stick out of the face read as buttons.
- A realistic eye is a glass dome: black center, a soft window highlight of 2 or 3 pixels with a gray halo in the upper corner on the light side, a dark red glow in the lower half and a dark rim. Highlight and glow are unlit, so they still read in the dark.
- Hair over the eyes stays short (a brow fringe of 1 or 2 units). A long fringe hides the focal point.
- Some creatures have no eyes (worms, many deep or void monsters). Do not add eyes the reference does not show.
- A grin is a hole cut out of the face texture with a gum-and-throat box 2 units behind it and a teeth card between them: upper teeth hang below the upper gum, lower teeth stand on the lower gum one column over, fangs 3 pixels.
- Eye boxes sit in front of every recess box. An eye plane in the same plane as the mouth box lost to it, and the lower eyes were cut in half.
- Glowing eyes the user asks for are lit through the whole eye with the lightest tone in the middle and no pupil. In a dark scene, add a small blurred halo of the eye color around them in each frame.
- A slanted glowing eye (a stepped almond in a dark socket under the brow) has a direction: check on both sides which row sits toward the snout. The reference had the upper row toward the back and the lower row stepping toward the snout; the first try was the other way round.
- An eye box must not sit behind a cheek or brow part that covers it at the reference angle. Render the head from that angle before calling the eye done.

## 5. Fur

- Body fur: `weave_fur`, short strands in rows that follow a soft light and dark field. Hair runs from head to tail; on legs it points down.
- Chest and neck: `lock_fur`, overlapping locks that are dark at the root and light at the tip.
- Tail and mane tips: `tip_fur`, dark at the root, light at the tip, with a ragged see-through end.
- On a white or short-haired animal, keep fur contrast low: base tone plus `weave_fur(lo=-1, hi=1)`.
- Fur must be neither noisy nor grid-like. Every dash with its own random length and tone looks noisy. Fixed bricks and checkers look like woven cloth.
- Hair cards and fringe planes only for animals whose hair breaks the silhouette (tarantula, hedgehog, shaggy wolf mane). A rabbit or a short-haired dog gets texture only.
- Never put a short, thin, ragged hair card on top of the head. Seen from above or the front it reads as a dark slit, not as hair. A head crest must be a full-pixel card: every bristle a whole pixel column, opaque, with a stepped outline drawn on purpose (no random ragged edge), root in the body tone, tips lighter.
- Lying hair on top of the head is fine: full-pixel opaque cards tilted about 15 degrees from the surface, pointing back and overlapping like shingles. From above they read as fur, not as slits.
- Hairy legs (spiders): rows of lying hair cards on all four sides of every segment, tilted about 22 degrees toward the tip, the rows on the sides offset from the front and back. The side cards break the silhouette and get light tips. Cards that face the camera keep tones close to the surface (about one tone of spread), or they turn into a camouflage pattern. Under the cards the segment texture is one soft light field plus `flow`, without extra dither or noise.
- Plate edges get hanging fringe cards: a smooth length profile, root in the body tone, tips lighter.
- A crest along the back also starts in the body tone. A root in the darkest tone reads as a crack along the spine.
- When you offer fur options, make them differ in method (strand layout, direction, locks or cards), not only in noise settings.

## 6. Check before you show

- If the visual-taste skill is installed, run it on the preview and the close-ups (`--ref` with the reference) and fix every `FIX` line before you show. Before any GIF, render two views half a degree apart and run its `--pair` check.
- Look at the preview and all three views yourself. The side view shows most of the posture mistakes.
- Compare against the rules above: cube count, layers, head position, proportions, noise, face frames.
- Look at the largest faces for big pixels: a block of one color several units wide with nothing in it reads as a bigger pixel than the rest of the model. Break it up before showing.
- Run `kit.mixels(build_parts())`. It must return an empty list; each entry is a part with a non-whole size or a texture that does not match its face.
- Many hair cards near the ground pull the shadow median to one side. Override `foot` and `radius` in the view from `render.fit` so the shadow sits under the body.
- Look at the face up close (`render.closeup`, from the side as well as the front): eyes, brows, nostrils and tusks are too small to judge in the full preview.
- A dark model on the default dark background hides its silhouette. Check shape on a light background, and show glow on a dark one.
- Test any rotation helper by round trip. A basis turned into Euler angles loses its tilt in gimbal lock (`R[0][2] = ±1`, a card whose normal lies on the x axis); the tooth cards and spine cards came out flat until `euler` handled that case. Check `rot_matrix(*euler(R))` against `R` for random bases and for the locked case.
- Aim close-ups at the real position of the part: build only that part, take `render.points(parts)` and use the middle of its bounds. A guessed target misses rotated parts such as claws.
- Check for flicker before any GIF: render the same close-up at two yaws half a degree apart and compare them (with `taste.py --pair` when visual-taste is installed, or by looking at the difference image). Changes along the edges are normal motion. Patches inside faces are two faces fighting in one plane; fix the parts, not only the render.
- Fix what you find, then show the user and say what you changed.
- When the user asks for a change, keep the old `model.py` as `model_vN.py` so you can go back.

## 7. Animation

- A crawl is a wave of yaw offsets that runs along the rings: ring k turns by `A * sin(2*pi*(t + k*c))`, so the wave runs from head to tail. 10 to 15 degrees and about two waves along the body read well; under 10 degrees the motion barely shows.
- Keep the mob in place, like on a treadmill: after building, shift every part so a middle ring stays at its rest position. The game moves the mob forward.
- If rings rise as the wave passes, keep the lift at 1 unit or less. More looks like the body is boiling.
- An idle with planted feet: when the body bobs, solve each knee with a two-bone IK (fixed femur and tibia lengths, bending toward the rest knee). The lengths stay constant, so `mixels` stays empty in every frame and hair cards keep their count and do not flicker.
- Check each gesture in the view the GIF uses. A lifted front leg seen from the front hid behind the rear leg on the same side; lift it out and forward so it leaves the other leg's silhouette.
- A creepy idle: a slow breath, a sudden head tilt held for a while, quick twitches of the mouth parts, one leg tapping the ground twice. Fast moves sit between long still holds.
- A dark scene: black background, lit texels darkened to about half, unlit texels (eyes) kept as they are, and a falloff toward the bottom so the legs fade into the dark. A shadow ellipse is invisible on black; leave it out.
- Darken lit texels to half only on a pale model. A model that is already near black keeps about 0.8, or it disappears into the background.
- Pulsing glow only when the user asks for it. Then it is soft, never fully off, with the phase shifted along the body so the light travels.
- A shine is a diagonal band that slides once from the base of the blade to the tip, then the prop rests for the rest of the loop. The band center goes to the lightest tone and its halo two tones up, both unlit. Adding a fixed amount (+3) to every tone is invisible on small frames. Check the frame sheet: the band must be clear in at least three frames.
- A turntable loops without a jump when the yaw is `start + 360 * i / N` for `i` from 0 to N - 1. Tilt the prop around its lowest point so nothing sinks into the ground, and use the same pose keys over the same N so the shine loops too.
- Do not call the time parameter `t` in a function that also builds boxes with `f, t = ...`; the box corner overwrites the time.
- Rendering an animation takes over a minute on a phone. Run it in the background, never two renders at once, and stop a render that a newer request has made obsolete.
- Apply idle motion as outer transforms after building (shift and turn whole groups). Textures that depend on where a part is (glow fields, light maps) then stay the same in every frame and do not flicker.
- ffmpeg reads stdin: a script piped to a server over ssh is eaten by the first ffmpeg call. Use `ffmpeg -nostdin` or copy the script over first.
- Build the rest model once and pose copies by appending outer transforms per frame (tag parts by group: head, jaw, tail ring k, left and right limbs). Rebuilding all textures per frame was four times slower.
- Take the ground shift from the rest pose and keep it for all frames. A shift taken from each posed frame makes the whole model jump.
- A chain (tail) is posed by appending, for ring k, rotations about joints k, k-1, ..., 0 in that order, each about the joint's rest position.
- Parts rebuilt per frame (a membrane whose corner is pinned to the body) must not change their pattern. Compute the pattern once on the rest shape and sample it per frame in the same local frame (origin on a whole texel, fixed segment width, fixed random streams per segment); only the outline may change. A pattern computed from the posed shape moved its glow marks between frames and the user saw the symbol change. Measure it: the share of glow pixels that change between neighbouring frames, aligned by the texture origin, stays under about 10 percent away from the outline.
- A rotation of a fixed-length bone can land its length on an exact whole number; take the ceiling with a small tolerance (`ceil(L - 1e-4)`) or the texture size flips between frames.

## 8. Weapons and crystal props

- Read the reference at its real pixel size first. Find the pixel size from the run lengths of color changes along one row (5 screen pixels per art pixel is common), shrink the image to 1:1 and keep that PNG next to the reference. Take the width of each part row by row and the palette (quantize to about 40 colors) from it. For a big prop, half the art size keeps details at one unit or more.
- A sword or knife blade is one double-sided card, no spine box. The ridge in the middle comes from the texture: the half that faces the light is light, the other half is dark, with a 1-pixel bright ridge line between them. The edge pixels get a highlight on the lit side. Only the blade material goes on the blade card: a metal spike of the guard painted onto it reads as the blade itself turning blue. If the guard reaches over the blade, make it a separate part.
- Thin parts (crossbars, curls, threads, tendrils, thin horn tips) are cards with a pixel-perfect line sprite, not chains of 1-unit boxes.
- Weapons keep real proportions. The grip is about a fifth of the blade length and clearly thinner than the blade (3 units on a 7 to 9 unit blade). The pommel is at most one or two units wider than the grip. A grip as thick as the blade and a big pommel make the sword look like a toy.
- Curved metal parts (horns, tentacles, vines on a grip) are chains of rods between points on the curve, 4 to 6 segments, thinner toward the tip, with a card for the point. Tube shading is one light line along the lit edge and a ring now and then. A ring every few units plus a highlight on each ring reads as a checkerboard.
- A grip gets a spiral wrap that continues across its four faces (offset each face by the widths before it), and a metal ferrule at each end.
- Crystals shine: their two lightest tones are drawn unlit (`alpha > 1.5`), facets are chevrons with a lighter edge on the lit side, and only some facet edges get a sparkle pixel. With lit tones only, crystals look like dull plastic.
- A plain prop lacks flair. Cards add it where they belong: thorns on the outer curve of a horn, a crossed-card point on every horn tip, a small crystal cluster on the pommel. Keep the cutting edge clean: shards along the blade edge hide its shape and get removed.
- Small 2D details often do not read in 3D: a dangling thread looked like a stray line, small colored gems looked busy. Leave them out or ask. When a part is removed, fill the bare spot (an engraving, rings) so no flat area is left.
- An axe bit is one double-sided card per side, like a sword blade. Two cards angled into a wedge were turned down.
- Draw an axe bit outline as a list of row spans, half of it mirrored, and print it as ASCII before rendering. The cutting edge is a convex arc, never a straight vertical line. The corners end in long horns: about 6 rows from the tip before the bit gets wide, the last 2 rows one pixel wide, leaning a little outward along the arc. Short blunt corners do not read as sharp.
- The cutting edge of a steel bit: the outer 2 pixels in the lightest tones drawn unlit, a bevel band 3 to 4 pixels wide that follows the edge, then a 1-pixel darker grind line before the forged body. Lit edge pixels alone looked dull in the shadow.
- A long weapon haft is about four times the head height. Build it from 3 or 4 rotated boxes between points. Keep the top straight and in line with the head and bend only the butt end, about 1 unit, with the pommel moved along. A bow through the middle of the haft made the whole axe look crooked.
- Do not stamp emblems or symbols on a plain steel bit unless the user asks. A symbol added on request was taken out again: the plain forged steel looked better, and a symbol made of separate pixels reads as a checker pattern.
- Dark wood needs wide steps between its dark tones. With tones close together the grain lines vanish and the haft reads as one flat stick.
- A single-card blade disappears edge-on in the side view. That is expected; say so when you show it.

## 9. Armored humanoids

- One texture density for the whole model and its scene. A character as detailed as a reference sprite needs about the sprite's pixel count: at 1 pixel per unit a 48-unit knight had a ninth of the pixels of the reference and every texture turned into big blocks. Use `density=2` (pass it to `face_size` and `mixels`); sizes may then be halves, positions quarters.
- Measure the reference part by part: shoulder height against the chin, head width against shoulder width, coat length against the boots. A wide boxy torso and shoulders pushed above the chin were both wrong.
- No box man. The torso narrows from chest to waist; the breastplate is two plates turned toward the middle so the front comes to a ridge, with mail flush between them (not sunk behind); the belly gets overlapping lames. Limbs are tapering segments with moderate muscle (3.5 units on a 48-unit body, a bicep plate, a forearm that narrows to the wrist).
- A head sits on a neck you can see (mail neck and a gorget between scarf and helmet), not sunk into the collar.
- Helmets: a skull, a separate top cap, then the crown on the cap. One continuous eye slit; a ridge that splits it reads as two eyes. A V visor is two halves turned so the ridge comes forward; with the wrong sign the face caves in.
- Hands are a back plate, curled fingers and a thumb, never one box. A weapon grip passes through the middle of the fist and the fist turns across the grip.
- Boots: shaft narrowing to the ankle, a low sole, a sloped instep and a narrower toe, all turned around one ankle point, with the shaft reaching into the instep. A tall box foot as wide as the leg reads as an elephant foot, and a gap between shaft and heel reads as a broken leg.
- Pose with a joint chain: hips carry chest, chest carries head, arms and weapon. Weight on one leg, hips and shoulders tilted against each other, the torso and head turned. A symmetric upright stance looks like a statue. Place hands where the user says; do not default to a hand on the hip.
- Nothing passes through anything: cloth in front of plates, mail narrower than the gap between plates, drapes in front of the breastplate, cloth in front of a raised knee.
- Small glowing pixels on dark armor read as orange stones. Leave them out unless the user asks for glow.
- When the user is unhappy with a part twice, render three or four candidates that differ in structure (not only texture) next to the reference in the same views, and let them pick.

## 10. Scenes

- A background is built from blocks with the same renderer and the same density as the model, never a 2D painting. Minecraft-style blocks have 16x16 faces; at density 2 a block is 8 units, so a 48-unit boss stands six blocks tall.
- Build only what was asked. A floor alone means no walls, props or torches.
- An endless floor is one large part whose top texture is painted texel by texel; thousands of block parts are slow. Fog is applied per texel by camera depth, and the far floor disappears into the fog, whose color matches the bottom of the sky.
- Take the scene palette and mood from the character: warm dark tones for a bronze and crimson knight, a soft halo in the cloak color behind it, dust in a warm gray.
- Light and shade agree with the renderer's light (from the upper left front): texture highlights on the left and front edges, shadows toward the back right. Cast the character's shadow by projecting every part's corners along the light onto the floor, filling the convex hull of each part, with a 1-pixel dither edge. Use one shadow only: an extra ellipse under the feet shows as a second shadow.
- Realistic texture means a better texture, not more things. Regular Bayer dither everywhere reads as cloth; use clumped grain of 1 to 3 pixels and broad bands with a narrow dither strip only where two tones meet.
- Dust is 1 to 2 pixels, faint, and moves a whole number of times across the frame per loop. Bigger specks read as bubbles.
- Heavy frame renders go to a server: send code with tar over ssh, run two processes, pull only the result. Make the script executable or call it with `bash` (files from Termux arrive without the execute bit), never `pkill -f` a name that appears in the same ssh command, and compare the pulled file's checksum with the last one so an old result is never shown as new.

## 11. Walk cycles

- Solve the legs with IK, not with guessed joint angles. The stance foot is nailed to the floor and slides back at exactly the treadmill speed; the swing foot follows a lifted path; the knee comes from a two-bone solve between hip and foot; the hip height is a smooth curve that dips at each footfall. Never lift the whole body to fix a foot below the ground: that one-frame jump reads as a stutter.
- A heavy walk: stance about 60% of the cycle, a high knee in the swing (thigh about 40 degrees forward, knee bent about 70 degrees), heel first at contact, hips turning and leaning toward the stance leg, chest turning against them and jolting forward at each footfall, the free arm swinging about 22 degrees, cloth following with a little lag. Feet that only shuffle and a still torso look static.
- Cloth over the legs: every frame, take the leg points in the cloth's own frame and open each panel to the smallest angle that clears the most forward point.
- A treadmill loop: the floor moves the stride per cycle; make the floor texture periodic over the loop's total shift and loop several cycles so the repeat sits in the fog.
- Before rendering, print per frame the hip height, the head height, the stance foot's position and anything solved (a sword tip on the ground). A stutter shows as one jump in these numbers.
- Make the GIF with ffmpeg (`palettegen` and `paletteuse=dither=none`); a palette taken from a few sample frames bands dark gradients into blotches. Show a small preview first and render full size after the user agrees.
- A four-legged walk: lateral sequence (right hind, right front, left hind, left front at phases 0, 0.25, 0.5, 0.75), stance about 68%. The stance foot slides back at a constant speed; the swing is a cubic Hermite whose end speeds match the treadmill, plus a lift of `sin(pi * u)`, a bent ankle and a paw that tips toe down. Solve each leg with a numeric two-angle IK on its end point (last segment angle fixed), started from the rest pose or the last frame's answer, whichever is closer, so the knee never flips.
- Center the walking feet under the shoulder and the hip, not at the feet of a crouched rest pose, and lower the body a little while walking; otherwise the leg cannot reach when the foot goes back. Print the IK error inside the frame loop (reading it after all frames are built shows only the last frame); any frame over 0.05 is a sliding foot.
- To nod a head or swing a group without touching its transforms, build the group, mirror its sides, then append one outer rotation to every part's `tr`. Mirroring after the rotation flips the sign of the yaw.

## 12. Winged dragons

- A hovering dragon: torso upright and leaning a little forward, head forward on a short neck, front arms tucked against the upper chest with the fingers hanging down over it, hind legs hanging beside the tail with the toes pointing straight down, a long thick tail hanging below the feet. Raised forearms with the hands held out in front read as dancing.
- Wing layout from the reference: a short arm with the wrist close to the shoulder and three very long fingers fanning out from the wrist (up and out, level, down and out). Half the span was about 1.6 times the height from head to tail tip; the user asked twice for bigger wings. Sweep the finger tips back a little so the side view has depth; a wing in one flat plane is a line from the side.
- A membrane is a triangle card per pair of fingers (wrist, tip A, tip B) with the triangle cut out in alpha, extended one texel under the bones so no seam shows. The free edge between two finger tips is two concave arcs meeting at a point (`sag` about 0.42 of half the edge); the panel from the lowest finger to the body is one arc with small scallops. One arc per panel read as plain; scallops at each strut read as a bat.
- Struts radiating from the wrist read as a feather fan; narrow strips hanging from each finger with gaps read as a hand fan. Fill the whole space between the fingers.
- A glowing membrane has no black lines on it: no dark struts and no dark band along the bones. Its pattern is flame veins that start near the leading bone and flow toward the edge inside each segment, wide and bright in the middle, pointed at the end, with a side branch. Thin wandering one-pixel lines read as circuitry.
- A wedge head: tall at the back, its top line falling about 20 degrees to a pointed snout, built from many rods along its length that converge toward the tip (a center snout rod, side rods, cheek blocks, a brow ridge, rods sweeping back over the neck). Horns on the snout bridge are spaced apart and lean back about 25 degrees; side by side and upright they read as a fence.
- Head texture: a few big tone regions per face divided by stepped dark contour lines (`terrace_tex`), a tone lighter than the body. Small pebble plates on the head made it read as a different model. Glow on the head stays on a few points near the horn tips and on one or two long bars; dashed stripes on each rod read as ladders.
- Bloom (`glow.py`): render the model, render again with only the bright unlit texels (luminance over about 0.42, the rest black but still blocking), blur that pass at three radii and add it. Treating the whole glowing membrane as a light source turned the wings into pink fog. Use a dark gradient background and lift the base a little (about 1.2) so a near-black body still shows.
- A wing flap is a chain, not a hinge: shoulder elevation, elbow and wrist bend, fingers that lag about a tenth of the cycle behind the arm, and a light fold of the fingers on the upstroke. The downstroke takes about 55 percent of the cycle and goes deep (from about +35 to -50 degrees); a shallow downstroke did not read as real. Keep the forward and back sweep under about 2 degrees; more read as rowing a boat. A strong fold made the wing vanish edge-on from the front.
- The body rides the flap: lowest when the wings are at the top, highest just after the downstroke ends, about 6 units each way on a giant. A small bob out of step reads as unrelated motion.
- Frame a flying idle close on the chest and let the wing tips leave the frame; framed for the whole span the dragon is a small figure in empty space.
