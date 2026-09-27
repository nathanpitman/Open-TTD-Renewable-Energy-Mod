/*
 * Test-only Game Script for tools/ingame_check.py.
 *
 * Checks what a player would see in the industry chain window and the
 * industry windows, straight from the running game:
 *   - the NewGRF is loaded and the POWR and URAN cargos exist
 *   - each industry type accepts and produces exactly the expected cargos
 *   - a Hydroelectric Dam can be built across a river on this map: the
 *     script tries each dry tile beside a river until one takes
 *   - every Hydroelectric Dam on the map (that one and any the map generator
 *     placed) has its wall across a river and its ends on dry bank
 *   - after a couple of months, every generator on the map is producing
 *     power, the Uranium Mine produces uranium, and the Nuclear Power
 *     Plant (no uranium delivered) produces none
 *
 * Every result is logged as a line starting "ETCHECK", which the runner
 * parses: "ETCHECK PASS ...", "ETCHECK FAIL ...", "ETCHECK WARN ...", and
 * a final "ETCHECK DONE".
 */

/* name → [accepted labels, produced labels]; names are the NewGRF's English strings */
EXPECTED <- {
    ["Uranium Mine"]          = [[],       ["URAN"]],
    ["Nuclear Power Plant"]   = [["URAN"], ["POWR"]],
    ["Hydroelectric Dam"]     = [[],       ["POWR"]],
    ["Tidal Power Station"]   = [[],       ["POWR"]],
    ["Wind Farm"]             = [[],       ["POWR"]],
    ["Solar Farm"]            = [[],       ["POWR"]],
    ["Electrical Substation"] = [["POWR"], []],
    ["Coal Power Station"]    = [["COAL"], []],
};
GENERATORS <- {["Hydroelectric Dam"] = 1, ["Tidal Power Station"] = 1, ["Wind Farm"] = 1, ["Solar Farm"] = 1};

class IngameCheck extends GSController {
    failures = 0;

    function Save() { return {}; }
    function Load(version, data) {}

    function Pass(msg) { GSLog.Info("ETCHECK PASS " + msg); }
    function Fail(msg) { GSLog.Error("ETCHECK FAIL " + msg); this.failures++; }
    function Warn(msg) { GSLog.Warning("ETCHECK WARN " + msg); }

    function Labels(list) {
        local out = [];
        foreach (c, _ in list) out.append(GSCargo.GetCargoLabel(c));
        out.sort();
        return out;
    }

    function Same(a, b) {
        if (a.len() != b.len()) return false;
        local x = clone a, y = clone b;
        x.sort(); y.sort();
        foreach (i, v in x) if (v != y[i]) return false;
        return true;
    }

    function Show(a) {
        local s = "";
        foreach (v in a) s += (s == "" ? "" : ",") + v;
        return "[" + s + "]";
    }

    function FindCargo(label) {
        foreach (c, _ in GSCargoList()) if (GSCargo.GetCargoLabel(c) == label) return c;
        return -1;
    }

    function Start() {
        this.Sleep(1);
        this.CheckGRF();
        local powr = this.FindCargo("POWR"), uran = this.FindCargo("URAN");
        if (powr == -1) this.Fail("cargo POWR missing"); else this.Pass("cargo POWR exists: " + GSCargo.GetName(powr));
        if (uran == -1) this.Fail("cargo URAN missing"); else this.Pass("cargo URAN exists: " + GSCargo.GetName(uran));
        local types = this.CheckChains();
        if ("Hydroelectric Dam" in types) this.BuildHydroAcrossRiver(types["Hydroelectric Dam"]);

        /* Let a couple of months pass so every industry has a full month of history. */
        local start = GSDate.GetCurrentDate();
        while (GSDate.GetCurrentDate() - start < 65) this.Sleep(74);
        this.CheckProduction(types, powr, uran);

        GSLog.Info("ETCHECK DONE failures=" + this.failures);
        while (true) this.Sleep(1000);
    }

    function CheckGRF() {
        local found = false;
        foreach (g, _ in GSNewGRFList()) {
            if (GSNewGRF.GetName(g).find("Energy Transition") != null) found = true;
        }
        if (found) this.Pass("NewGRF loaded"); else this.Fail("NewGRF not loaded");
    }

    function CheckChains() {
        local types = {};
        foreach (t, _ in GSIndustryTypeList()) {
            local name = GSIndustryType.GetName(t);
            if (!(name in EXPECTED)) continue;
            types[name] <- t;
            local acc = this.Labels(GSIndustryType.GetAcceptedCargo(t));
            local prod = this.Labels(GSIndustryType.GetProducedCargo(t));
            local want = EXPECTED[name];
            if (this.Same(acc, want[0]) && this.Same(prod, want[1])) {
                this.Pass("chain " + name + ": accepts " + this.Show(acc) + ", produces " + this.Show(prod));
            } else {
                this.Fail("chain " + name + ": accepts " + this.Show(acc) + " (want " + this.Show(want[0]) +
                          "), produces " + this.Show(prod) + " (want " + this.Show(want[1]) + ")");
            }
        }
        foreach (name, _ in EXPECTED) if (!(name in types)) this.Fail("industry type missing: " + name);
        return types;
    }

    /* Dry tiles with river on the next tile in +x or +y: where a dam's north
       (start) bank tile would be. The GRF's own checks decide the rest. */
    function RiverBankTiles() {
        local out = [];
        local mx = GSMap.GetMapSizeX(), my = GSMap.GetMapSizeY();
        for (local y = 1; y < my - 2; y++) {
            for (local x = 1; x < mx - 2; x++) {
                local t = GSMap.GetTileIndex(x, y);
                if (GSTile.IsWaterTile(t)) continue;
                if (GSTile.IsRiverTile(GSMap.GetTileIndex(x + 1, y)) || GSTile.IsRiverTile(GSMap.GetTileIndex(x, y + 1))) out.append(t);
            }
        }
        return out;
    }

    function BuildHydroAcrossRiver(type) {
        local before = {};
        foreach (i, _ in GSIndustryList()) before[i] <- 1;
        local banks = this.RiverBankTiles();
        if (banks.len() == 0) { this.Warn("hydro build: no rivers on this map, dam across a river not tested"); return; }
        local tried = 0;
        foreach (t in banks) {
            tried++;
            if (!GSIndustryType.BuildIndustry(type, t)) continue;
            local id = -1;
            foreach (i, _ in GSIndustryList()) if (!(i in before) && GSIndustry.GetIndustryType(i) == type) id = i;
            if (id == -1) { this.Fail("hydro build: BuildIndustry succeeded but no new dam found"); return; }
            this.Pass("hydro build: built at bank tile " + tried + " of " + banks.len());
            return;
        }
        this.Fail("hydro build: no dam could be built across a river (" + banks.len() + " river bank tiles tried)");
    }

    /* The dam runs from its start bank tile t along x or y: dry bank, wall,
       dry bank. The wall tiles are industry tiles now, so check the river
       still runs past them upstream and downstream, and that neither end is
       on water. */
    function CheckRiverDam(id) {
        local t = GSIndustry.GetLocation(id);
        local x = GSMap.GetTileX(t), y = GSMap.GetTileY(t);
        local dx = GSIndustry.GetIndustryID(GSMap.GetTileIndex(x + 1, y)) == id ? 1 : 0;
        local dy = 1 - dx;
        local n = 0;
        while (GSIndustry.GetIndustryID(GSMap.GetTileIndex(x + dx * n, y + dy * n)) == id) n++;
        local width = n - 2;
        local ok = width >= 1 && width <= 3;
        for (local k = 1; k <= width; k++) {
            local up = GSMap.GetTileIndex(x + dx * k - dy, y + dy * k - dx);
            local down = GSMap.GetTileIndex(x + dx * k + dy, y + dy * k + dx);
            if (!GSTile.IsRiverTile(up) || !GSTile.IsRiverTile(down)) ok = false;
        }
        foreach (k in [0, n - 1]) {
            local b = GSMap.GetTileIndex(x + dx * k, y + dy * k);
            if (GSTile.IsWaterTile(b) || GSTile.IsRiverTile(b)) ok = false;
        }
        local where = GSIndustry.GetName(id) + " at " + x + "," + y + " along " + (dx ? "x" : "y") + ", "
                      + width + " wall tile(s)";
        if (ok) this.Pass("hydro placement: across a river: " + where);
        else this.Fail("hydro placement: not across a river: " + where);
    }

    function CheckProduction(types, powr, uran) {
        local counts = {};
        foreach (name, _ in types) counts[name] <- 0;
        foreach (i, _ in GSIndustryList()) {
            local t = GSIndustry.GetIndustryType(i);
            foreach (name, tt in types) {
                if (tt != t) continue;
                counts[name]++;
                local label = GSIndustry.GetName(i);
                if (name == "Hydroelectric Dam") this.CheckRiverDam(i);
                if (name in GENERATORS) {
                    local p = GSIndustry.GetLastMonthProduction(i, powr);
                    if (p > 0) this.Pass("production " + label + ": " + p + " POWR last month");
                    else this.Fail("production " + label + ": no POWR last month");
                } else if (name == "Nuclear Power Plant") {
                    local p = GSIndustry.GetLastMonthProduction(i, powr);
                    if (p == 0) this.Pass("production " + label + ": no POWR without uranium");
                    else this.Fail("production " + label + ": " + p + " POWR last month with no uranium delivered");
                } else if (name == "Uranium Mine") {
                    local p = GSIndustry.GetLastMonthProduction(i, uran);
                    if (p > 0) this.Pass("production " + label + ": " + p + " URAN last month");
                    else this.Fail("production " + label + ": no URAN last month");
                }
            }
        }
        foreach (name, n in counts) {
            if (n > 0) this.Pass("on map: " + n + " x " + name);
            else this.Warn("on map: no " + name + " was generated, so its production was not checked");
        }
    }
}
