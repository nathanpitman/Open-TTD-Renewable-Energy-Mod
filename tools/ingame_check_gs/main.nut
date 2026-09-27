/*
 * Test-only Game Script for tools/ingame_check.py.
 *
 * Checks what a player would see in the industry chain window and the
 * industry windows, straight from the running game:
 *   - the NewGRF is loaded and the POWR and URAN cargos exist
 *   - each industry type accepts and produces exactly the expected cargos
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

    function CheckProduction(types, powr, uran) {
        local counts = {};
        foreach (name, _ in types) counts[name] <- 0;
        foreach (i, _ in GSIndustryList()) {
            local t = GSIndustry.GetIndustryType(i);
            foreach (name, tt in types) {
                if (tt != t) continue;
                counts[name]++;
                local label = GSIndustry.GetName(i);
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
