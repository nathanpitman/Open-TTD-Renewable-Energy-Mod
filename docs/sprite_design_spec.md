# Sprite design specification

This is the visual standard for every sprite in the mod: industry tiles, ground tiles and cargo icons. Use it when you add a sprite, regenerate the sheets, or change `tools/make_sprites.py`.

The technical side is in README.md → "Sprites": file layout, palette format, offsets and how the NML is generated. This document covers how the sprites should **look**.

## How this document is used

Sprites are reviewed one at a time, with one GitHub issue per sprite, all under issue #34. When you ask for a change, refer to parts by the names in that sprite's annotated reference (section 12). Refining a sprite gives one of two kinds of change:

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

**Decided.** From the OpenTTD wiki, [Recommended Standards](https://wiki.openttd.org/en/Development/NewGRF/Recommended%20Standards):

> Most original TTD graphics are drawn with the light source in the lower right of the screen (about "4.30 o'clock"). The light source is best imagined as 'high up in the sky'. Shadows fall towards the top-left of the screen. There are places which incorrectly state that light comes from the top-right. If you want your graphics to be compatible with original TTD style, don't be mistaken about the lighting.

For our sprites, that means:

- The light is high in the sky, towards the lower right of the screen. Roofs and other upward-facing surfaces are the brightest.
- Walls facing the lower right (south-east, the +y faces in `tools/make_sprites.py`) face the light. They are the brightest walls.
- Walls facing the lower left (south-west, the +x faces) are turned away from the light, so they are darker.
- Shadows fall towards the upper left.

**Current:** the generator follows this since #76. `LIGHT = (-0.15, 0.55, 0.82)` in `tools/make_sprites.py` gives:

| Face | Brightness |
|---|---|
| Roof | 0.87 |
| Walls facing lower-right (+y) | 0.66 |
| Walls facing lower-left (+x) | 0.25 |

Brightness = `0.25 + 0.75 × max(0, N·L)`, mapped onto the material's ramp. Windowed walls use the lighter glass colour on the lit, lower-right walls. `tools/compare_vanilla.py` draws our tiles next to OpenGFX buildings so the lighting can be checked against the base game.

**Still to check after the light change:**

- **Solar panels:** fixed. They now tilt to face the lower right (south-east), into the light. Because they are lit, they come out paler than before. Check that they still read as solar panels (#61–#63).
- **Turbine blades:** they use fixed colours (`blade` and `edge` in `wind_turbine`), not the light. Check that they sit well next to the newly lit tower (#58).
- **Cargo icons:** these are flat menu icons and keep their own shading. The Power icon's docstring still says "lit from the upper left" (#73).

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

## 12. Annotated references

**Decided.** Every sprite has an annotated reference image that names each visible part. We use those names when asking for changes ("make the turbine blades thicker", "add a ladder to the intake tower"), and Claude uses them to find the right part in the sprite and in the code.

The references are in [`docs/sprites/`](sprites/), and [`docs/sprites/index.md`](sprites/index.md) lists every sprite's part names.

**What each reference shows:**

- One PNG per sprite, at the same level as the review issues: one per distinct tile design, ground tile and cargo icon.
  - The four hydro facings share the reference for their base tile.
  - The wind turbine is annotated on frame 0 only.
- A header with the sprite's name, its industry, its tile key, the function that draws it, and its review issue.
- The 1x sprite drawn on its ground tile and enlarged with nearest-neighbour scaling (8× for tiles, 32× for cargo icons), so each pixel stays sharp.
- A label for every visible part, with a leader line and a dot on a pixel of that part. The labels sit outside the sprite so they don't cover the art.
- Below that:
  - a **part map**: the sprite with each part filled in its label colour, showing exactly which pixels belong to which part;
  - the 1x and 2x sprites at actual size.

**Part names:**

- Plain words that a player would use, such as "solar panels", "turbine blades", "nacelle", "intake tower" or "parked cars". Don't use code names like `beam` or `box`.
- Unique within a sprite. If there are several of the same part, number them from back to front ("tank 1", "tank 2"), or label the group once ("yellowcake drums").
- The same name everywhere for parts drawn by a shared helper: "transformer", "gantry", "insulators", "fence", "lattice pylon", "cooling tower", "service track", "solar panels".
- Special names:
  - A pitched roof drawn with `gable()` is named after its building plus "roof" ("powerhouse roof").
  - The ground under an industry tile is labelled "ground (<kind>)".
- Stable. Renaming a part changes the vocabulary we use in requests, so record the rename in the decision log.
- Only parts visible in the 1x sprite get a label. A part that is hidden, or too small to show at 1x (for example the rims on the Uranium icon), isn't listed.

**How they're made:**

- The build writes them. After writing the sprite sheets, `python3 tools/make_sprites.py` runs `tools/sprite_refs.py`, so the references can't drift from the art. To redo only the references, run `python3 tools/sprite_refs.py [industry…]`.
- The labels come from the drawing code. Every drawing call in `tools/make_sprites.py` sits inside `with cv.part("name"):`, and the canvas records which part drew each pixel. The innermost name wins, so shared helpers keep their own names. The names are never typed separately from the art.
- A visible pixel with no part name stops the build with an error, so no part goes unnamed.
- Files are `docs/sprites/<tile_key>.png` for industry tiles (for example `solar_panels.png`), `ground_<kind>.png` for ground tiles and `cargo_<cargo>.png` for icons. They are committed with the sheets.
- A new sprite also needs an entry in `REFS` in `tools/sprite_refs.py`, which gives its title and its review issue.

**When a sprite changes:** regenerate its reference in the same change. A new part needs a name. A removed part's label disappears by itself.

## 13. Reference material

Existing OpenTTD guidance to read before drawing or changing sprites. These links were collected in #3. The lighting text from Recommended Standards is quoted in section 4. The other summaries come from #3 and haven't been re-checked, because the wiki sites can't be reached from the environment this spec was written in.

- **[Recommended Standards](https://wiki.openttd.org/en/Development/NewGRF/Recommended%20Standards)** (OpenTTD wiki): light source direction, quoted in section 4, and general drawing conventions. Issue #3 also summarises it as recommending drawing against consistent templates and keeping graphics sources in version control.
- **[Alignment](https://wiki.openttd.org/en/Development/NewGRF/Alignment)** and **[Debugging](https://wiki.openttd.org/en/Development/NewGRF/Debugging)** (OpenTTD wiki): standard sprite-offset templates, and the in-game sprite alignment tool for checking bounding boxes by eye.
- **[PalettesAndCoordinates](https://newgrf-specs.tt-wiki.net/wiki/PalettesAndCoordinates)** (NewGRF Specs wiki): the authoritative spec for the DOS and Windows 8bpp palettes and for the coordinate and bounding-box system. It backs section 3.
- **[NML: List of default colour translation palettes](https://newgrf-specs.tt-wiki.net/wiki/NML:List_of_default_colour_translation_palettes)** (NewGRF Specs wiki): recolour sprites, for if we ever add company-colour remapping.
- **[RealSprites](https://newgrf-specs.tt-wiki.net/wiki/RealSprites)** (NewGRF Specs wiki): sprite positioning (`xrel`/`yrel`), which is where the offsets in the generated `spriteset` blocks come from.
- **[GraphicsTutorial hub](https://www.tt-wiki.net/wiki/GraphicsTutorial)** (tt-wiki.net): community drawing tutorials on palettes and coordinates, saving correctly paletted files, and drawing vehicles and stations. It also covers a MagicaVoxel workflow some artists use to render 8bpp isometric sprites.

Read at least "Recommended Standards" (light and style) and "PalettesAndCoordinates" (palette) before starting.

**Light direction: settled.** Recommended Standards puts the light in the lower right of the screen, about 4:30 (see section 4). An earlier version of this spec said the base-game Oil Refinery looked lit from the left. That was a misreading, so disregard it.

## Review checklist (for each sprite issue)

- [ ] Viewed in game next to base-game industries, at 1x and 2x zoom (or 1x only, if section 2 is decided that way).
- [ ] Viewed as part of the whole industry, not just on its own.
- [ ] Follows every **Decided** rule above.
- [ ] Annotated reference in `docs/sprites/` is regenerated, and every visible part has a name (section 12).
- [ ] Any global change found during the review is recorded here and added to the decision log.
- [ ] `python3 tools/make_sprites.py` regenerated the sheets, the GRF was rebuilt, and `python3 tools/ingame_check.py` passes.

## Decision log

| Date | Decision | Section | Issue |
|---|---|---|---|
| 2026-09-27 | Sprites must look at home next to base-game industries | 1 | #34 |
| 2026-09-27 | Every sprite gets an annotated reference image, made by the build, naming its parts for use in change requests | 12 | #34 |
| 2026-09-27 | Annotated references built (`tools/sprite_refs.py`, `docs/sprites/`); part names come from `cv.part()` tags in the drawing code | 12 | #34 |
| 2026-09-27 | Light source is in the lower right of the screen (about 4:30), high in the sky, per the OpenTTD wiki Recommended Standards. The generator was changed to match in #76 | 4 | #34, #76 |
