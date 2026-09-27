# Energy Transition Industries — OpenTTD Mod

<p align="center">
  <img src="docs/industries/hydro_dam.png" alt="Hydroelectric Dam" height="90">
  <img src="docs/industries/uranium_mine.png" alt="Uranium Mine" height="90">
  <img src="docs/industries/nuclear_plant.png" alt="Nuclear Power Plant" height="90">
  <img src="docs/industries/tidal_station.png" alt="Tidal Power Station" height="90">
  <img src="docs/industries/wind_farm_single.png" alt="Wind Farm" height="90">
  <img src="docs/industries/solar_farm.png" alt="Solar Farm" height="90">
  <img src="docs/industries/substation.png" alt="Electrical Substation" height="90">
</p>

<p align="center">
  <a href="https://github.com/nathanpitman/Open-TTD-Renewable-Energy-Mod/releases/latest"><strong>⬇️ Download the latest release</strong></a>
</p>

Two components work together:
- `energy_transition.grf` — NewGRF adding 7 new industries and 2 custom cargos
- `energy_transition_gs/` — Game Script simulating an invisible power grid

## Compatibility

This mod is **likely incompatible with FIRS** (and other industry sets that replace the whole cargo and industry economy). FIRS defines its own set of cargos and industries, which can clash with the cargos and industries this mod adds or overrides. Expect missing or mislabelled cargos if both are active.

---

## Installation

### NewGRF
Copy `energy_transition.grf` to your OpenTTD `newgrf/` folder:
- **Windows**: `Documents\OpenTTD\newgrf\`
- **Mac**: `~/Documents/OpenTTD/newgrf/`
- **Linux**: `~/.local/share/openttd/newgrf/`

Enable in: **Main Menu → NewGRF Settings → Add**

### Game Script
Copy the `energy_transition_gs/` folder into your OpenTTD `game/` folder so the path is:
`game/energy_transition_gs/info.nut`

`game/` locations:
- **Windows**: `Documents\OpenTTD\game\`
- **Mac**: `~/Documents/OpenTTD/game/`
- **Linux**: `~/.local/share/openttd/game/`

Enable in: **Main Menu → AI/Game Script Settings → Game Script → select "Energy Transition Power Grid"**

> ⚠️ Do NOT place files in `content_download/` — that folder is managed by OpenTTD.
> Both the NewGRF and Game Script must be active **before starting a new game**.

---

## How it works

### Cargo chain
```
Towns → Passengers (workers) → Energy Generators → [invisible grid] → Town growth
                                                  → Electrical Substation → (amplifies growth)
Uranium Mine → Uranium → Nuclear Power Plant → [invisible grid] → Town growth
```

### Invisible power grid (Game Script)
Every 30 days the script scans every town and finds all energy generators within `generator_radius` tiles. It sums their POWR production and sets the town's growth rate directly — no cargo transport needed.

| Power situation | Growth rate |
|---|---|
| No nearby power | Growth halted (configurable) |
| Low power | Very slow — 150 days/growth |
| Medium power | Moderate — 60 days/growth |
| Full power, no substation | Good — 30 days/growth |
| Full power + nearby substation | Fast — 12 days/growth |

### Worker mechanic
Power stations and the Uranium Mine accept Passengers (workers). No other industry needs workers. Without regular worker deliveries, production slowly declines until it reaches the minimum level. A lack of workers never closes an industry. Generators start at minimum output and ramp up as workers arrive. The Nuclear Power Plant is the exception for now: it makes exactly as much power as the uranium delivered to it, and workers don't change that yet.

### Energy timeline (all dates configurable)
| | Industry | Default era | Placement rule |
|---|---|---|---|
| <img src="docs/industries/hydro_dam.png" alt="Hydroelectric Dam" width="160"> | Hydroelectric Dam | 1950 | Dam wall directly against water (river, lake or canal), facing whichever way the water is |
| <img src="docs/industries/uranium_mine.png" alt="Uranium Mine" width="160"> | Uranium Mine | 1953 | Remote |
| <img src="docs/industries/nuclear_plant.png" alt="Nuclear Power Plant" width="160"> | Nuclear Power Plant | 1956 | Requires Uranium delivery |
| <img src="docs/industries/tidal_station.png" alt="Tidal Power Station" width="160"> | Tidal Power Station | 1966 | Coast only |
| <img src="docs/industries/wind_farm.png" alt="Wind Farm" width="160"> | Wind Farm | 1980 | High ground only |
| <img src="docs/industries/solar_farm.png" alt="Solar Farm" width="160"> | Solar Farm | 1990 | Flat land only |
| <img src="docs/industries/substation.png" alt="Electrical Substation" width="160"> | Electrical Substation | 1950 | Near towns, amplifies growth |

### Coal phaseout
<img src="docs/industries/coal_power_plant.png" alt="Coal Power Station" width="160">

The vanilla Coal Power Station is overridden to also require workers. No new coal plants spawn after `param_coal_stop_year` (default 1970). Existing plants begin closing stochastically after `param_coal_close_year` (default 1990), accelerating 20 years later.

---

## NewGRF Parameters
Configure in **NewGRF Settings → select mod → Parameters** before starting a game.

**Era dates:** Hydro (1930–1960), Nuclear (1950–1975), Tidal (1960–1985), Wind (1970–1995), Solar (1980–2005), Coal stop (1960–1990), Coal close (1980–2020)

**Placement:** Wind min height (0–8), Substation spawn rate (1–10)

**Spawn rates:** Individual sliders for each generator type (0 = disabled)

**Gameplay:** Workers required toggle (on/off)

## Game Script Parameters
Configure in **AI/Game Script Settings → select script → Configure**.

| Setting | Default | Description |
|---|---|---|
| Generator radius | 30 tiles | How far a generator powers nearby towns |
| Substation radius | 15 tiles | How far a substation amplifies growth |
| Min power threshold | 6 | POWR units/month needed for any growth |
| Full power threshold | 25 | POWR units/month for maximum growth |
| No power blocks growth | On | Towns with zero power cannot grow |
| Update interval | 30 days | How often the grid recalculates |

---

## Rebuilding from source
```bash
pip install nml pillow
python3 tools/make_sprites.py      # regenerate sprites/*.png and the NML spritesets
nmlc --grf=energy_transition.grf energy_transition.nml
```

### Sprites
All industry art is generated by `tools/make_sprites.py`, which renders each tile from simple 3D shapes. Edit the script, not the PNGs.

- **Format:** 8bpp indexed PNG using OpenTTD's DOS palette, taken verbatim from `nml`. nmlc rejects any other palette, and in that palette index 0 (transparent) is stored as `(0,0,255)`.
- **Zoom:** 1x sheets are `sprites/<industry>.png` and 2x sheets are `sprites/<industry>_2x.png`. Both come from the same geometry and are wired up with `alternative_sprites(…, ZOOM_LEVEL_IN_2X, …)`.
- **One sprite per tile:** each sheet holds one sprite per distinct industry tile, so multi-tile industries read as a single site. Ground tiles are drawn separately in `sprites/ground.png` (grass, dirt, concrete, water, shore).
- **Lighting:** roofs are brightest, walls facing lower-left are lit and walls facing lower-right are shaded, matching the base game.
- **Animated colours:** water uses the palette-animated sea colours. The script sets the `ANIM` flag on any sprite that contains them.
- **Offsets:** the script rewrites the block between `BEGIN/END GENERATED SPRITESETS` in `energy_transition.nml`, so sprite sizes and offsets always match the art.
- **Preview:** `python3 tools/preview.py preview.png [--scale 2]` assembles every industry the way the game lays it out, so you can check the art without starting OpenTTD. `python3 tools/preview.py --each docs/industries --scale 2 --zoom 1` writes the per-industry images used in this README. The single-turbine banner image (`docs/industries/wind_farm_single.png`) is the `wind_farm/single` layout in `tools/preview.py`, generated the same way via `compose("wind_farm/single", 2, bg=(0, 0, 0, 0))`.
