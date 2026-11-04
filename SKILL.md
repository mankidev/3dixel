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

`core/` holds everything a model needs. Start every model from an example, not from an empty file: `examples/rabbit/model.py` for animals, `examples/crimson-sword/model.py` for weapons and props, `examples/ember-knight/` for armored humanoids, poses, a walk cycle and a block scene, `examples/pale-stalker/` for a hairy spider-like creature with lying hair cards, sunken eyes and an IK idle in a dark scene, `examples/flesh-hound/` for a hairless four-legged creature with quill cards, a hunched creature stance, a posable head and tail and a four-leg IK walk. The sword example also holds helpers you can copy: `rod(p0, p1, th, ...)` (a box between two points with tube shading), `chain_rods` (a curved horn or tentacle from a list of points), `line_sprite` (a pixel-perfect line card), `crystal` (chevron facets with lit edges), `glow` (top tones drawn unlit), a shine pose, and `anim_turn.py` (tilted 360 turntable).

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
- A creature that only resembles an animal does not stand like it. For a dog-like monster: the head hangs below the shoulder line and reaches forward, the back peaks where the chest box meets the rear box (the chest tilted front down around its back top edge, the rear tilted back down around its front top edge), the front legs splay out from the shoulder and the hind legs crouch. An upright dog stance reads as a pet.
- A monster's body is big next to its head: the user grew it three times, to a chest about twice the head width and a body three times the head length, with a clear gap between the front and hind legs. Legs grow with it (thick upper segments, legs about half the shoulder height); legs left at the old size read as weak and short.
- Paws are about as wide as the leg above them. A wide flat paw block reads as an elephant foot or a slipper.
- A tail on a heavy body starts inside the rear box with a root about two thirds of the rear box height and tapers from there. A thin tail stuck on the back face reads as a stick.
- A box that does not read as a body part goes. A shoulder blade box sticking out of the chest read as a stray plank on the leg.

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

## 4. Face and expression

- An angry face is a brow slanting down toward the nose over a dark eye.
- A brow painted in the texture disappears on dark fur. Use geometry: a hair card (`tip_fur`, dark root, lighter tips, leaning out from the face) on a bristly animal, a slanted 1-unit cube on a smooth one.
- Keep the eye black unless the user asks for a color.
- Sunken eyes: cut holes in the face texture (alpha 0), put the eye cube one unit behind the face and build the socket walls as separate double-sided planes. A double-sided box does not draw its inner walls when the opposite face has a texture. Eyes that stick out of the face read as buttons.
- A realistic eye is a glass dome: black center, a soft window highlight of 2 or 3 pixels with a gray halo in the upper corner on the light side, a dark red glow in the lower half and a dark rim. Highlight and glow are unlit, so they still read in the dark.
- Hair over the eyes stays short (a brow fringe of 1 or 2 units). A long fringe hides the focal point.
- Some creatures have no eyes (worms, many deep or void monsters). Do not add eyes the reference does not show.

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
- Pulsing glow only when the user asks for it. Then it is soft, never fully off, with the phase shifted along the body so the light travels.
- A shine is a diagonal band that slides once from the base of the blade to the tip, then the prop rests for the rest of the loop. The band center goes to the lightest tone and its halo two tones up, both unlit. Adding a fixed amount (+3) to every tone is invisible on small frames. Check the frame sheet: the band must be clear in at least three frames.
- A turntable loops without a jump when the yaw is `start + 360 * i / N` for `i` from 0 to N - 1. Tilt the prop around its lowest point so nothing sinks into the ground, and use the same pose keys over the same N so the shine loops too.
- Do not call the time parameter `t` in a function that also builds boxes with `f, t = ...`; the box corner overwrites the time.
- Rendering an animation takes over a minute on a phone. Run it in the background, never two renders at once, and stop a render that a newer request has made obsolete.

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
