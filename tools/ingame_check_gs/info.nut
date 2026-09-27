/* Test-only Game Script used by tools/ingame_check.py. Not shipped to players. */
class IngameCheckInfo extends GSInfo {
    function GetAuthor()      { return "Energy Transition"; }
    function GetName()        { return "Energy Transition In-game Check"; }
    function GetDescription() { return "Test harness for tools/ingame_check.py: checks cargos, industry chains and production, then logs ETCHECK lines."; }
    function GetVersion()     { return 1; }
    function GetDate()        { return "2026-09-27"; }
    function GetShortName()   { return "ETCK"; }
    function GetAPIVersion()  { return "13"; }
    function CreateInstance() { return "IngameCheck"; }
}

RegisterGS(IngameCheckInfo());
