# Sprite design specification

This is the visual standard for every sprite in the mod: industry tiles, ground tiles and cargo icons. Use it when you add a sprite, regenerate the sheets, or change `tools/make_sprites.py`.

The technical side is in README.md → "Sprites": file layout, palette format, offsets and how the NML is generated. This document covers how the sprites should **look**.

## How this document is used

Sprites are reviewed with one GitHub issue per industry (plus one for ground tiles and one for cargo icons), all under issue #34. Each issue has a section for every sprite in that industry. When you ask for a change, refer to parts by the names in that sprite's annotated reference (section 12). Refining a sprite gives one of two kinds of change:

- **Specific to that sprite** (for example, "add a ladder to the intake tower"): track it in that sprite's section of its industry issue, and change only that sprite's draw function.
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

**Decided** (#34): ship **1x sprites only**, like almost all NewGRFs. OpenTTD enlarges them when zoomed in, just as it does the base graphics (OpenGFX and the original TTD set), so the mod's art is exactly as chunky as the map around it at every zoom level.

- `tools/make_sprites.py` writes only `sprites/<name>.png`. The NML has no `alternative_sprites` blocks.
- Don't add pixel-doubled 2x files: OpenTTD already does that, so they would gain nothing.
- Only bring back 2x/4x sprites if we deliberately target high-res base sets (zBase, OpenGFX2), and then draw them to those sets' standard, probably in 32bpp.
- Players who zoom in see the 1x art enlarged. `tools/preview.py --scale 2` and the "in game at 2x zoom" panel of each annotated reference (section 12) show exactly that.

Review every sprite at 1x zoom, and check it at 2x zoom too, where it should look like base-game art at the same zoom.

## 3. Palette

**Current:**

- 8bpp, OpenTTD DOS palette, taken verbatim from `nml`. Index 0 is transparent.
- Don't use palette-animated indices (227–254), except the sea-water cycle (245–249) on water surfaces. The sprite then needs the `ANIM` flag, which the generator sets.
- Don't use index 255 (pure white). Use 15 (almost white) instead. PalettesAndCoordinates reserves pure white for the background of a sprite sheet, and `nmlc` warns when a sprite contains it. The `WHITE` ramp stops at 15.
- Colours come from the named ramps at the top of `tools/make_sprites.py` (`GREY`, `WHITE`, `STEEL`, `CONCRETE`, `BEIGE`, `SAND`, `BRICK`, `RED`, `YELLOW`, `GRASS`, `DIRT`, `TAILINGS`, `COAL`, `TOWER`, `PANEL`, `GLASS`, `WATER`, `GREEN_ROOF`, `BLUE_ROOF`). Add a new ramp there rather than using raw indices in a draw function.

**Decided: company colours stay, and sprites are never recoloured.** Two of our ramps sit on OpenTTD's company-colour ranges (RecolorSprites):

- `GLASS` (198–205) is exactly the first company-colour range, 0xC6–0xCD.
- `GRASS` (80–87) is exactly the second company-colour range, 0x50–0x57.

The base game does the same. In OpenGFX, 50–60% of the grass ground's pixels are 80–87, and 198–205 make up about 13% of the vanilla buildings in `tools/compare_vanilla.py`, mostly as windows. There is no close green outside 80–87, so moving `GRASS` would make our ground clash with the base-game grass next to it (section 9). The nearest blues outside 198–205 are more saturated than base-game windows.

So both ramps stay, and no sprite is ever drawn with recolouring on. If one were, OpenTTD would use the industry's random colour for industry tiles (NML: List of default colour translation palettes), and every window and patch of grass on that sprite would change colour. `tools/make_sprites.py` stops with an error if `energy_transition.nml` has a `recolour_mode:` or `palette:` line. If we ever want recoloured parts, decide here first what happens to `GLASS` and `GRASS`.

**Open question:** accent colours. Base-game industries use rust, orange, brick, hazard yellow and red widely. Ours are mostly `GREY`, `WHITE` and `CONCRETE`. A rule on how much of a sprite should be accent colour is still to be decided.

## 4. Lighting and shading

**Decided.** From the OpenTTD wiki, [Recommended Standards](https://wiki.openttd.org/en/Development/NewGRF/Recommended%20Standards):

> Most original TTD graphics are drawn with the light source in the lower right of the screen (about "4.30 o'clock"). The light source is best imagined as 'high up in the sky'. Shadows fall towards the top-left of the screen. There are places which incorrectly state that light comes from the top-right. If you want your graphics to be compatible with original TTD style, don't be mistaken about the lighting.

That page is marked "a draft for discussion" and is filed under the wiki's Archive category, so this is a community convention rather than an official rule. It is still the only written guidance on the light direction, and we follow it.

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
- **Turbine blades:** fixed. Every blade pixel used to share one flat normal, `(1, 1, 0.3)`. That normal is symmetric in x and y, so the blades looked the same under the old light and the new, and showed no light direction at all. They are now shaded as a rounded section (`BLADE_CURVE` in `_blades`): the edge that faces the light (up and towards the lower right) is lighter and the far edge darker. This goes through `LIGHT`, so it will follow any later change to the light (#58).
- **Cargo icons:** no change needed. They are flat menu icons with their own fixed shading, not world sprites, so they don't follow `LIGHT` (#76 left them unchanged). The `icon_power` docstring and the `_DRUM` comment now say this. Before, "lit from the upper left" read as if it contradicted this section (#73, #74).

**Open question:** contrast. The base game has a bigger jump between the lit and shaded walls than our smooth shading gives. We still need to decide the minimum number of ramp steps between lit and shaded faces.

## 5. Texture

**Current:** each material adds a little hash noise (`Material.noise`, 0.04–0.12 on buildings, higher on piles and water). Large walls and roofs come out nearly flat.

**Open question:** stronger per-pixel texture or ordered dithering on building surfaces, so that no large area is a single flat colour.

## 6. Outlines

**Current:** buildings have no outlines. Cargo icons have a near-black outline (index 1).

**Open question:** dark outlines on building silhouettes and major edges, as the base game uses.

## 7. Detail density

**Current:** detail comes from window grids (`windowed`) and a few props (`transformer`, `gantry`, `fence`, `bushing`, ladders on the tanks).

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

**Current:** 10 × 10 flat pixel art with a near-black outline, like the base game's cargo icons. 1x only, like every other sprite (section 2).

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
  - the 1x sprite at actual size, and as the game shows it at 2x zoom (the 1x sprite enlarged, since only 1x ships; section 2).

**Part names:**

- Plain words that a player would use, such as "solar panels", "turbine blades", "nacelle", "intake tower" or "parked cars". Don't use code names like `beam` or `box`.
- Unique within a sprite. If there are several of the same part, number them from back to front ("tank 1", "tank 2"), or label the group once ("yellowcake drums").
- The same name everywhere for parts drawn by a shared helper: "transformer", "gantry", "insulators", "fence", "bushings", "cooling tower", "service track", "solar panels".
- Special names:
  - A pitched roof drawn with `gable()` is named after its building plus "roof" ("powerhouse roof").
  - The ground under an industry tile is labelled "ground (<kind>)".
- Stable. Renaming a part changes the vocabulary we use in requests, so record the rename in the decision log.
- Only parts visible in the sprite get a label. A part that is hidden, or too small to show at 1x (for example the rims on the Uranium icon), isn't listed.

**How they're made:**

- The build writes them. After writing the sprite sheets, `python3 tools/make_sprites.py` runs `tools/sprite_refs.py`, so the references can't drift from the art. To redo only the references, run `python3 tools/sprite_refs.py [industry…]`.
- The labels come from the drawing code. Every drawing call in `tools/make_sprites.py` sits inside `with cv.part("name"):`, and the canvas records which part drew each pixel. The innermost name wins, so shared helpers keep their own names. The names are never typed separately from the art.
- A visible pixel with no part name stops the build with an error, so no part goes unnamed.
- Files are `docs/sprites/<tile_key>.png` for industry tiles (for example `solar_panels.png`), `ground_<kind>.png` for ground tiles and `cargo_<cargo>.png` for icons. They are committed with the sheets.
- A new sprite also needs an entry in `REFS` in `tools/sprite_refs.py`, which gives its title and its review issue.

**When a sprite changes:** regenerate its reference in the same change. A new part needs a name. A removed part's label disappears by itself.

## 13. Reference material

Existing OpenTTD guidance to read before drawing or changing sprites. These links were collected in #3. The summaries below were checked against the live pages on 2026-09-27. None of these pages says anything about accent colours, contrast, texture, outlines, detail density or scale (sections 3–8). Those have to be settled by comparing with the base-game sprites (`tools/compare_vanilla.py`).

- **[Recommended Standards](https://wiki.openttd.org/en/Development/NewGRF/Recommended%20Standards)** (OpenTTD wiki, marked as a draft): light source direction, quoted in section 4. Its only other graphics advice is to use sprite templates, and the templates it links are for trains and road vehicles, not industries. It also recommends keeping graphics sources in version control, and shipping a readme and licence with the GRF.
- **[Alignment](https://wiki.openttd.org/en/Development/NewGRF/Alignment)** (OpenTTD wiki): a standard sheet layout and offsets for **train** sprites only. Its "See also" links go to the old TTDPatch wiki. Of little use for industry tiles.
- **[Debugging](https://wiki.openttd.org/en/Development/NewGRF/Debugging)** (OpenTTD wiki): the in-game NewGRF developer tools. Turn them on with `set newgrf_developer_tools 1` in the console. Then:
  - the **sprite aligner** (Information menu) nudges a sprite's offsets and has a picker to find the sprite under the cursor. It doesn't save anything: note the new offsets and put them in the generator. The page warns of a bug where the offsets it shows are 4 times too big and must be divided by 4, so check them against the sprite;
  - the **bounding-box viewer** (Ctrl+B) shows every sprite's bounding box on the map;
  - the **tile info window** has a debug button that shows an industry's variables and persistent storage;
  - the `reload_newgrfs` console command reloads the GRF from disk, so a rebuilt `energy_transition.grf` can be checked without starting a new game. It overwrites the same file name, and it resets any offsets set in the aligner.
- **[PalettesAndCoordinates](https://newgrf-specs.tt-wiki.net/wiki/PalettesAndCoordinates)** (NewGRF Specs wiki): the authoritative spec for the DOS and Windows 8bpp palettes and for the coordinate and bounding-box system. It backs section 3 (DOS palette, no palette-animated "action colours", no pure white, the company-colour range) and section 8 (3D X runs from top-right to bottom-left of the screen, Y from top-left to bottom-right, and north is the top of the screen).
- **[RecolorSprites](https://newgrf-specs.tt-wiki.net/wiki/RecolorSprites)** (NewGRF Specs wiki): the palette indices OpenTTD recolours: 0xC6–0xCD for the first company colour and 0x50–0x57 for the second (section 3).
- **[NML: List of default colour translation palettes](https://newgrf-specs.tt-wiki.net/wiki/NML:List_of_default_colour_translation_palettes)** (NewGRF Specs wiki): the named recolour palettes. For industry tiles, the default recolour uses the industry's random colour.
- **[RealSprites](https://newgrf-specs.tt-wiki.net/wiki/RealSprites)** (NewGRF Specs wiki): sprite positioning (`xrel`/`yrel`), which is where the offsets in the generated `spriteset` blocks come from.
- **[GraphicsTutorial hub](https://www.tt-wiki.net/wiki/GraphicsTutorial)** (tt-wiki.net): community drawing tutorials on palettes and coordinates, saving correctly paletted files, and drawing vehicles and stations. It also links GraphicsTemplates (example templates with alignment) and a MagicaVoxel workflow some artists use to render 8bpp isometric sprites. Nothing on it is specific to industries.

Read at least "Recommended Standards" (light and style) and "PalettesAndCoordinates" (palette) before starting.

**Light direction: settled.** Recommended Standards puts the light in the lower right of the screen, about 4:30 (see section 4). An earlier version of this spec said the base-game Oil Refinery looked lit from the left. That was a misreading, so disregard it.

## Review checklist (for each sprite issue)

- [ ] Viewed in game next to base-game industries, at 1x zoom and at 2x zoom (where the game enlarges the 1x sprite).
- [ ] Viewed as part of the whole industry, not just on its own.
- [ ] Offsets and bounding boxes checked with the NewGRF developer tools (`set newgrf_developer_tools 1`, then the sprite aligner and Ctrl+B; section 13).
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
| 2026-09-27 | Ship 1x sprites only; the 2x sheets and `alternative_sprites` blocks are removed and OpenTTD enlarges the 1x art when zoomed in | 2 | #34 |
| 2026-09-27 | `GLASS` and `GRASS` stay on the company-colour ranges, as the base game's windows and grass do; sprites are never recoloured, and the generator fails if the NML turns recolouring on | 3 | #34 |
