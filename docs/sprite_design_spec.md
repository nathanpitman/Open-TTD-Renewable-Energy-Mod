# Sprite design specification

This is the visual standard for every sprite in the mod: industry tiles, ground tiles and cargo icons. Use it when you add a sprite, regenerate the sheets, or change `tools/make_sprites.py`.

The technical side is in README.md → "Sprites": file layout, palette format, offsets and how the NML is generated. This document covers how the sprites should **look**.

## How this document is used

Sprites are reviewed one at a time, with one GitHub issue per sprite, all under issue #34. Refining a sprite gives one of two kinds of change:

- **Specific to that sprite** (for example, "add a ladder to the intake tower"): make the change in that sprite's issue and draw function only.
- **Global** (for example, "every building gets a dark outline", "walls use at least 4 shades"): it must apply to every sprite. In the same change:
  1. Record it in the right section below, and change the status to **Decided**.
  2. Add a row to the [decision log](#decision-log).
  3. Put it in `tools/make_sprites.py` as shared code (a material, a helper or a canvas pass), not as a one-off in a single draw function.
  4. Note on the other open sprite issues that the rule now applies to them.

If a sprite needs to break a decided rule, say why in its issue and record the exception here.

Each rule has a status:

- **Current**: how the generator works today. Not yet reviewed against the target look.
- **Proposed**: suggested but not agreed.
- **Decided**: agreed. Every sprite must follow it.

## 1. Target look

**Decided.** Sprites must look at home next to base-game industries (original TTD graphics and OpenGFX) at every zoom level. A player should not be able to pick out the mod's buildings by their art style alone.

In practice that means chunky pixel art with visible texture, strong contrast between light and shade, and lots of small detail. The reference is the base-game Oil Refinery: nearly every few pixels carry something (ladders, pipework, stripes, platforms, flares, small props). It should not look like a smooth, clean 3D render.

Known gaps today (#34): the sprites look too high-res, surfaces are too smooth and even, there are too few small details, and too much is grey.

## 2. Resolution and zoom levels

**Current:** every spriteset has a 1x sheet (`sprites/<name>.png`) and a true 2x sheet (`sprites/<name>_2x.png`), both rendered from the same geometry.

**Proposed** (#34): ship **1x only**, like almost all NewGRFs, and let OpenTTD enlarge the sprites when zoomed in, just as it does for OpenGFX. Pixel-doubling the 1x art into new 2x files gains nothing. Only bring back 2x/4x if we deliberately target high-res base sets (zBase, OpenGFX2), and then draw to their standard.

Until this is decided, review every sprite at both 1x and 2x zoom in game.

## 3. Palette

**Current:**

- 8bpp, OpenTTD DOS palette, taken verbatim from `nml`. Index 0 is transparent.
- Don't use palette-animated indices (227–254), except the sea-water cycle (245–249) on water surfaces. The sprite then needs the `ANIM` flag, which the generator sets.
- Colours come from the named ramps at the top of `tools/make_sprites.py` (`GREY`, `WHITE`, `STEEL`, `CONCRETE`, `BEIGE`, `SAND`, `BRICK`, `RED`, `YELLOW`, `GRASS`, `DIRT`, `TAILINGS`, `COAL`, `PANEL`, `GLASS`, `WATER`, `GREEN_ROOF`, `BLUE_ROOF`). Add a new ramp there rather than using raw indices in a draw function.

**Open question:** accent colours. Base-game industries use rust, orange, brick, hazard yellow and red widely. Ours are mostly `GREY`, `WHITE` and `CONCRETE`. A rule on how much of a sprite should be accent colour is still to be decided.

## 4. Lighting and shading

**Current:**

- Light comes from the upper left of the screen. Roofs are brightest, walls facing lower-left are lit, and walls facing lower-right are in shade.
- Brightness = `0.25 + 0.75 × max(0, N·L)`, mapped onto the material's ramp.

**Open question:** contrast. The base game has a bigger jump between the lit and shaded walls than our smooth shading gives. We still need to decide the minimum number of ramp steps between lit and shaded faces.

## 5. Texture

**Current:** each material adds a little hash noise (`Material.noise`, 0.04–0.12 on buildings, higher on piles and water). Large walls and roofs come out nearly flat.

**Open question:** stronger per-pixel texture or ordered dithering on building surfaces, so that no large area is a single flat colour.

## 6. Outlines

**Current:** buildings have no outlines. Cargo icons have a near-black outline (index 1).

**Open question:** dark outlines on building silhouettes and major edges, as the base game uses.

## 7. Detail density

**Current:** detail comes from window grids (`windowed`) and a few props (`transformer`, `gantry`, `fence`, `lattice_tower`, ladders on the tanks).

**Open question:** a minimum level of small detail per tile. Candidates: pipes, ladders, railings, rooftop plant and vents, hazard stripes, small vehicles, crates and drums on the ground pad. Build these as reusable helpers so every sprite can use them.

## 8. Scale and proportions

**Current** (world units, used by `tools/make_sprites.py`):

- One tile is 16 × 16 units. One height level is 8 units.
- Projection matches OpenTTD: screen X = 2(y − x), screen Y = x + y − z. +x points to the lower-left of the screen and +y to the lower-right.
- Sprite cells are 64 px wide (1x). The industry's height budget `H` sets how tall a sprite can be.
- Window grid: about one window every 2.2–3.5 units across and one storey every 3.3–6 units up.

**Open question:** matching the base game's scale for storeys, doors and vehicles, so our buildings don't look over- or under-sized next to base-game buildings and road vehicles.

## 9. Ground tiles

**Current:** grass, dirt, concrete, water and shore are drawn flat in `sprites/ground.png`, with noise and (for concrete) seams every 8 units. Each industry has a default ground, with per-tile overrides in `TILE_GROUND`.

Ground tiles should blend with the base game's own ground, especially grass and water that meet the base-game tiles next to them.

## 10. Animation

**Current:**

- Wind turbines: 8 rotor frames through 120°, looping. Frame 0 is the still image. See README.md → "Sprites".
- Water animates through the palette cycle.

Every animation frame must follow the same rules as the still frame.

## 11. Cargo icons

**Current:** 10 × 10 flat pixel art with a near-black outline, like the base game's cargo icons.

## Review checklist (for each sprite issue)

- [ ] Viewed in game next to base-game industries, at 1x and 2x zoom (or 1x only, if section 2 is decided that way).
- [ ] Viewed as part of the whole industry, not just on its own.
- [ ] Follows every **Decided** rule above.
- [ ] Any global change found during the review is recorded here and added to the decision log.
- [ ] `python3 tools/make_sprites.py` regenerated the sheets, the GRF was rebuilt, and `python3 tools/ingame_check.py` passes.

## Decision log

| Date | Decision | Section | Issue |
|---|---|---|---|
| 2026-09-27 | Sprites must look at home next to base-game industries | 1 | #34 |
