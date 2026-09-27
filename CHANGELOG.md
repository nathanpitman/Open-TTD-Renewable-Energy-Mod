# Changelog

## Unreleased

- **Fixed: grass under wind farms, solar farms and hydro power stations didn't match the land around them.** These tiles drew their own brighter green grass, so the farm showed up as a lighter square. They now use the game's own ground, so they match whatever base graphics you use, and they show snow above the sub-arctic snowline and sand in sub-tropical desert. ([#29](https://github.com/nathanpitman/Open-TTD-Renewable-Energy-Mod/issues/29))

## v13

- **Fixed: the Game Script never changed town growth.** It looked for the Power cargo by comparing its label to a number, but OpenTTD gives the label as text, so it never found Power and did nothing. It also looked for generators by an exact name, but each industry's name starts with its town ("Smallbridge Wind Farm"), so it never found any. It now finds generators as the industries that produce Power, and substations as the ones that accept it, which also works in any language.
- **Fixed: the power grid updated far too often.** The "update interval" setting is in game days, but the script treated it as ticks, so it recalculated about every half day instead of every 30 days. It now uses days.
- **Added a debug override to bypass all start-year limits.** A new "Debug: ignore all start-year limits" NewGRF parameter (off by default) makes every generator and the uranium mine available from the start of the game, for testing without needing to relax or wait out the individual era-date settings.
- **Fixed: coal mines drawn as hydro dams.** Every industry tile in the NewGRF replaced base-game industry tile 0, which belongs to the coal mine, so coal mines showed dam art. The tiles no longer replace any base-game tile.
- **Hydroelectric dams sit on water.** A dam used to be allowed anywhere within a few tiles of water, so it could appear in the middle of a field. Each tile of the dam wall now needs a water tile directly next to it, so the dam always meets a real river, lake or canal.
- **Hydroelectric dams face any direction.** The dam comes in four orientations, so it can be built with the water on any side. The raised reservoir behind the wall is gone: the wall now stands in the river itself, which looks right from every side.
- **Fixed: Power and Uranium missing from the game.** Both cargos were defined without the setting that tells OpenTTD they exist, so the game dropped them. The Uranium Mine produced nothing, the Nuclear Power Plant didn't accept uranium, and no generator produced power. Both cargos now appear, with their own names.
- **Nuclear power needs uranium.** The Nuclear Power Plant used to make power even with no uranium delivered. It now makes power only from uranium: each tonne delivered becomes 1 MWh.
- **Fixed: generators and the Uranium Mine produced twice.** Each one produced from two separate sources that were added together. They now produce from one source: Hydro 12, Tidal 10, Wind 8, Solar 6 MWh and Uranium Mine 6 tonnes per production cycle.
- **Removed workers.** Generators and the Coal Power Station no longer accept Passengers, and the "Workers required" setting is gone. Hydro, tidal, wind and solar make power without any deliveries. The Nuclear Power Plant still needs uranium, and the Coal Power Station still needs coal. The other settings keep their numbers, so values saved in existing games still apply to the right setting.
- **Removed the "max water distance" setting.** It no longer did anything. The other settings keep their numbers, so values saved in existing games still apply to the right setting.

### Compatibility

- Games saved with v12 still load, but power stations built before the upgrade don't produce Power or take part in the power grid. They were created when the Power cargo didn't exist, and OpenTTD keeps an industry's cargos from when it was built. Power stations built after the upgrade work normally. For the full power grid, start a new game.
- Probably doesn't work with FIRS. See the README.

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
