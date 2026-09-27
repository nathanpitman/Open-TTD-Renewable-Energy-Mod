ENERGY TRANSITION INDUSTRIES — OPENTTD MOD
===========================================

Two components work together:
  - energy_transition.grf   NewGRF adding 7 new industries and 2 custom cargos
  - energy_transition_gs/   Game Script simulating an invisible power grid

Download the latest release from GitHub:
  https://github.com/nathanpitman/Open-TTD-Renewable-Energy-Mod/releases/latest


COMPATIBILITY
-------------
This mod is likely incompatible with FIRS (and other industry sets that
replace the whole cargo and industry economy). FIRS defines its own set of
cargos and industries, which can clash with the cargos and industries this
mod adds or overrides. Expect missing or mislabelled cargos if both are
active.


INSTALLATION
------------
See INSTALL.txt for full step-by-step instructions, including OS-specific
folder locations and troubleshooting.

Short version:
  1. Copy energy_transition.grf into your OpenTTD newgrf/ folder and enable
     it under NewGRF Settings.
  2. Copy the energy_transition_gs/ folder into your OpenTTD game/ folder
     and select "Energy Transition Power Grid" under AI/Game Script
     Settings.
  3. Start a NEW game. Both parts must be active before generating the map.


HOW IT WORKS
------------

Cargo chain:
  Energy Generators -> [invisible grid] -> Town growth
  Energy Generators -> Electrical Substation -> (amplifies growth)
  Uranium Mine -> Uranium -> Nuclear Power Plant -> [invisible grid]
    -> Town growth

Invisible power grid (Game Script):
  Every 30 days the script scans every town and finds all energy generators
  within the generator radius. It sums their POWR production and sets the
  town's growth rate directly — no cargo transport needed.

    Power situation                  Growth rate
    --------------------------------------------------------------
    No nearby power                  Growth halted (configurable)
    Low power                        Very slow  — 150 days/growth
    Medium power                     Moderate   — 60 days/growth
    Full power, no substation        Good       — 30 days/growth
    Full power + nearby substation   Fast       — 12 days/growth

No deliveries needed:
  Hydro, tidal, wind and solar generators need nothing delivered: they make
  power as soon as they're built. Only the Nuclear Power Plant needs a
  supply chain. It makes exactly as much power as the uranium delivered
  to it.

Energy timeline (all dates configurable):

    Industry                  Default era   Placement rule
    --------------------------------------------------------------------
    Hydroelectric Dam         1950          Dam wall directly against water
                                             (river, lake or canal), facing
                                             whichever way the water is
    Uranium Mine              1953          Remote
    Nuclear Power Plant       1956          Requires Uranium delivery
    Tidal Power Station       1966          Coast only
    Wind Farm                 1980          High ground only
    Solar Farm                1990          Flat land only
    Electrical Substation     1950          Near towns, amplifies growth

Coal phaseout:
  The vanilla Coal Power Station still needs coal deliveries. No new coal
  plants spawn after param_coal_stop_year (default 1970). Existing plants
  begin closing stochastically after param_coal_close_year (default 1990),
  accelerating 20 years later.


NEWGRF PARAMETERS
------------------
Configure in NewGRF Settings -> select mod -> Parameters, before starting a
game.

  Era dates:    Hydro (1930-1960), Nuclear (1950-1975), Tidal (1960-1985),
                Wind (1970-1995), Solar (1980-2005), Coal stop (1960-1990),
                Coal close (1980-2020)
  Placement:    Wind min height (0-8), Substation spawn rate (1-10)
  Spawn rates:  Individual sliders for each generator type (0 = disabled)


GAME SCRIPT PARAMETERS
-----------------------
Configure in AI/Game Script Settings -> select script -> Configure.

    Setting                   Default    Description
    --------------------------------------------------------------------
    Generator radius          30 tiles   How far a generator powers
                                          nearby towns
    Substation radius         15 tiles   How far a substation amplifies
                                          growth
    Min power threshold       6          POWR units/month needed for any
                                          growth
    Full power threshold      25         POWR units/month for maximum
                                          growth
    No power blocks growth    On         Towns with zero power cannot grow
    Update interval           30 days    How often the grid recalculates
