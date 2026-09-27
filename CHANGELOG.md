# Changelog

## v12

From this release on, each release is numbered with a single whole number: the NewGRF and the Game Script both report it as their version. v12 comes after the v0.1 and v0.2 pre-releases, which already shipped a NewGRF with version 11. Numbering carries on from there so OpenTTD always treats a new release as newer.

This release contains everything from the v0.2 pre-release.

### Changes since v0.1

- **New industry art.** Every industry now has its own drawn tiles at normal and 2x zoom, replacing the placeholder graphics. The Coal Power Station has its own art instead of reusing the substation's.
- **Wind farms spread out.** Turbines are smaller and never sit on neighbouring tiles, so their blades don't overlap. Wind farms use one of four layouts.
- **Fixed: default cargos replaced.** Power and Uranium used the same cargo slots as Passengers and Coal and replaced them. They now use slots of their own (#1).
- **Fixed: Uranium Mine overwritten.** The Coal Power Station change shared an industry ID with the Uranium Mine. It now has its own ID (#2).
- **Fixed: industries closing without workers.** Generators and power stations that got no passengers were being closed. They now stay open at their lowest output.
- **Game Script** now reports version 12 (it was 1).

### Compatibility

- Probably doesn't work with FIRS. See the README.
- Industry tile IDs changed since v0.1, so start a new game rather than loading a v0.1 save.

## v0.1

First public release of **Energy Transition Industries** for OpenTTD. It adds cleaner power generation, from hydro and nuclear through to wind and solar, and ties town growth to how much electricity reaches each town.

### What's included

- **`energy_transition.grf`**: a NewGRF with 7 new industries and 2 new cargos (Power and Uranium)
- **`energy_transition_gs/`**: a Game Script ("Energy Transition Power Grid") that runs a hidden power grid and sets how fast towns grow

### Highlights

#### New industries, arriving over time

| Industry | Default year | Placement |
|---|---|---|
| Hydroelectric Dam | 1950 | Near water |
| Electrical Substation | 1950 | Near towns; makes towns grow faster |
| Uranium Mine | 1953 | Remote areas |
| Nuclear Power Plant | 1956 | Needs uranium deliveries |
| Tidal Power Station | 1966 | Coast only |
| Wind Farm | 1980 | High ground only |
| Solar Farm | 1990 | Flat land only |

#### Hidden power grid

Every 30 days the Game Script adds up the power output of generators near each town and sets that town's growth rate. You don't need to transport power. Towns with no power stop growing. Towns with plenty of power grow quickly, and a nearby substation makes them grow faster still.

#### Workers

Every generator accepts Passengers as workers. A new generator starts at low output and increases as workers arrive. If deliveries stop, output slowly falls.

#### Coal phase-out

The standard Coal Power Station now also needs workers. No new coal plants appear after 1970, and existing plants start closing at random from 1990, faster from 2010. Both years can be changed.

#### Configurable

- **NewGRF parameters:** the start year for each type of power, the coal stop and close years, placement rules (distance to water, minimum height for wind, how often substations appear), how often each generator type appears, and whether workers are needed.
- **Game Script settings:** how far a generator's power reaches, how far a substation's boost reaches, how much power a town needs to grow at all and to grow at full speed, whether towns with no power can grow, and how often the grid updates.

### Installation

1. Copy `energy_transition.grf` into your OpenTTD `newgrf/` folder and enable it under **NewGRF Settings**.
2. Copy the `energy_transition_gs/` folder into your OpenTTD `game/` folder and select **Energy Transition Power Grid** under **AI/Game Script Settings → Game Script**.
3. Start a **new game**. Both parts must be turned on before the game begins.

See `README.md` and `INSTALL.txt` for the folder locations on each operating system and for how to rebuild from source (`nmlc`).

### Known limitations

- This is an early release, so the balance numbers (power thresholds, growth rates, how often industries appear) may change.
- The README at this release mentions an `energy_transition_gs.tar` package, but the release doesn't include one. Use the folder install (option A) instead.
- It hasn't been tested with saves from earlier games. Start a new game.

Feedback and bug reports are welcome in Issues.
