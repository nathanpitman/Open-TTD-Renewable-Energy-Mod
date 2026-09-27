/*
 * Energy Transition Power Grid — main.nut
 *
 * Every update_interval_days game-days, for each town:
 *   1. Sum POWR production from all generators within generator_radius
 *   2. Check for any substation within substation_radius
 *   3. Set town growth rate accordingly
 *
 * Growth rates (days between growth events — lower = faster):
 *   No power + blocks_growth on  -> TOWN_GROWTH_NONE
 *   No power + blocks_growth off -> 200 days (very slow)
 *   Low power                    -> 150 days
 *   Medium power                 -> 60 days
 *   Full power, no substation    -> 30 days
 *   Full power + substation      -> 12 days (fast city growth)
 */

class EnergyTransition extends GSController {

    _generator_radius  = null;
    _substation_radius = null;
    _min_power         = null;
    _full_power        = null;
    _blocks_growth     = null;
    _update_interval   = null;
    _powr_cargo        = -1;

    constructor() {}

    function Start() {
        this.Sleep(100);

        _generator_radius  = this.GetSetting("generator_radius");
        _substation_radius = this.GetSetting("substation_radius");
        _min_power         = this.GetSetting("min_power_threshold");
        _full_power        = this.GetSetting("full_power_threshold");
        _blocks_growth     = this.GetSetting("no_power_blocks_growth");
        _update_interval   = this.GetSetting("update_interval_days");

        _powr_cargo = this._FindPOWRCargo();

        GSLog.Info("Energy Transition GS started.");
        GSLog.Info("  Generator radius:  " + _generator_radius + " tiles");
        GSLog.Info("  Substation radius: " + _substation_radius + " tiles");
        GSLog.Info("  Min power:         " + _min_power);
        GSLog.Info("  Full power:        " + _full_power);
        GSLog.Info("  POWR cargo id:     " + _powr_cargo);

        while (true) {
            /* Sleep() counts ticks; a game day is 74 ticks */
            this.Sleep(_update_interval * 74);
            this._UpdateGrid();
        }
    }

    /* Find the POWR cargo type by scanning cargo labels */
    function _FindPOWRCargo() {
        local list = GSCargoList();
        local c = list.Begin();
        while (!list.IsEnd()) {
            /* GSCargo.GetCargoLabel returns the label as a 4-character string */
            if (GSCargo.GetCargoLabel(c) == "POWR") {
                GSLog.Info("Found POWR cargo at id: " + c);
                return c;
            }
            c = list.Next();
        }
        GSLog.Warning("POWR cargo not found. Is the Energy Transition NewGRF active?");
        return -1;
    }

    /* Identify industries by cargo, not name: GSIndustry.GetName returns
       the town-prefixed name (e.g. "Smallbridge Wind Farm"), and names
       change with the game language. */

    /* Generators produce POWR */
    function _IsGenerator(ind_id) {
        local type = GSIndustry.GetIndustryType(ind_id);
        return GSIndustryType.GetProducedCargo(type).HasItem(_powr_cargo);
    }

    /* Substations accept POWR */
    function _IsSubstation(ind_id) {
        local type = GSIndustry.GetIndustryType(ind_id);
        return GSIndustryType.GetAcceptedCargo(type).HasItem(_powr_cargo);
    }

    function _UpdateGrid() {
        if (_powr_cargo == -1) return;

        /* Collect generators and substations */
        local gen_ids  = [];
        local sub_ids  = [];

        local ind_list = GSIndustryList();
        local ind = ind_list.Begin();
        while (!ind_list.IsEnd()) {
            if (GSIndustry.IsValidIndustry(ind)) {
                if (this._IsGenerator(ind)) {
                    gen_ids.push(ind);
                } else if (this._IsSubstation(ind)) {
                    sub_ids.push(ind);
                }
            }
            ind = ind_list.Next();
        }

        /* For each town, calculate power and set growth rate */
        local town_list = GSTownList();
        local town = town_list.Begin();
        while (!town_list.IsEnd()) {
            if (GSTown.IsValidTown(town)) {
                local town_tile = GSTown.GetLocation(town);
                local total_power = 0;
                local has_sub = false;

                /* Sum power from generators in radius */
                local i = 0;
                while (i < gen_ids.len()) {
                    local g = gen_ids[i];
                    local dist = GSIndustry.GetDistanceManhattanToTile(g, town_tile);
                    if (dist <= _generator_radius) {
                        local prod = GSIndustry.GetLastMonthProduction(g, _powr_cargo);
                        if (prod > 0) total_power += prod;
                    }
                    i++;
                }

                /* Check for substation in radius */
                local j = 0;
                while (j < sub_ids.len()) {
                    local s = sub_ids[j];
                    local dist = GSIndustry.GetDistanceManhattanToTile(s, town_tile);
                    if (dist <= _substation_radius) {
                        has_sub = true;
                        break;
                    }
                    j++;
                }

                local rate = this._GrowthRate(total_power, has_sub);
                GSTown.SetGrowthRate(town, rate);
            }
            town = town_list.Next();
        }
    }

    function _GrowthRate(power, has_sub) {
        if (power < _min_power) {
            if (_blocks_growth == 1) return GSTown.TOWN_GROWTH_NONE;
            return 200;
        }

        if (power >= _full_power) {
            if (has_sub) return 12;
            return 30;
        }

        /* Linear interpolation between min and full thresholds */
        local range = _full_power - _min_power;
        local above_min = power - _min_power;
        /* Rate goes from 150 (at min) down to 60 (at full) */
        local rate = 150 - (90 * above_min / range);
        if (has_sub) rate = rate / 2;
        if (rate < 10) rate = 10;
        return rate;
    }
}
