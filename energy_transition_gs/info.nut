class EnergyTransitionInfo extends GSInfo {
    function GetAuthor()      { return "Energy Transition"; }
    function GetName()        { return "Energy Transition Power Grid"; }
    function GetDescription() { return "Invisible power grid. Generators power nearby towns based on proximity. Substations amplify growth. No power = no growth. Use with Energy Transition Industries NewGRF."; }
    function GetVersion()     { return 13; }
    function GetDate()        { return "2026-09-27"; }
    function GetShortName()   { return "ETPG"; }
    function GetAPIVersion()  { return "13"; }
    function CreateInstance() { return "EnergyTransition"; }
    function MinVersionToLoad() { return 1; }

    function GetSettings() {
        AddSetting({
            name = "generator_radius",
            description = "Generator radius (tiles): how far a generator powers nearby towns",
            easy_value = 40, medium_value = 30, hard_value = 20, custom_value = 30,
            min_value = 10, max_value = 80, flags = 4
        });
        AddSetting({
            name = "substation_radius",
            description = "Substation radius (tiles): how far a substation amplifies town growth",
            easy_value = 20, medium_value = 15, hard_value = 10, custom_value = 15,
            min_value = 5, max_value = 40, flags = 4
        });
        AddSetting({
            name = "min_power_threshold",
            description = "Min POWR units/month for a town to grow at all",
            easy_value = 3, medium_value = 6, hard_value = 10, custom_value = 6,
            min_value = 1, max_value = 30, flags = 4
        });
        AddSetting({
            name = "full_power_threshold",
            description = "POWR units/month for maximum growth rate",
            easy_value = 15, medium_value = 25, hard_value = 40, custom_value = 25,
            min_value = 10, max_value = 100, flags = 4
        });
        AddSetting({
            name = "no_power_blocks_growth",
            description = "No nearby power halts town growth entirely (0=off 1=on)",
            easy_value = 0, medium_value = 1, hard_value = 1, custom_value = 1,
            min_value = 0, max_value = 1, flags = 4
        });
        AddSetting({
            name = "update_interval_days",
            description = "How often (game-days) the power grid recalculates",
            easy_value = 30, medium_value = 30, hard_value = 30, custom_value = 30,
            min_value = 7, max_value = 90, flags = 4
        });
    }
}

RegisterGS(EnergyTransitionInfo());
