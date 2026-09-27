# CLAUDE.md

## Versioning

Each release has one whole number. The GitHub release tag, the NewGRF and the Game Script all use it, so players, bug reports and saves refer to the same thing.

OpenTTD only accepts whole numbers for versions, and they must go up with every release. Releases are therefore numbered `v12`, `v13`, `v14`, and so on. Don't use dotted versions like `v1.2`.

Numbering starts at 12 because the old v0.1 and v0.2 pre-releases shipped a NewGRF with version 11. A lower number would make OpenTTD treat those older builds as newer.

### Source of truth

- `VERSION` at the repo root holds the current release number (for example `12`). It must match the latest GitHub release tag without the `v` (tag `v12` means `12`).
- Don't type a version number anywhere else by hand. Copy it from `VERSION`.

### Where the version appears

Keep all of these in step with `VERSION`:

| File | Field | Value |
|---|---|---|
| `energy_transition.nml` | `grf { version: … }` | `N` |
| `energy_transition.nml` | header comment (`NewGRF v…`) | `vN` |
| `energy_transition_gs/info.nut` | `GetVersion()` | `N` |
| `energy_transition_gs/info.nut` | `GetDate()` | release date, `YYYY-MM-DD` |
| `CHANGELOG.md` | newest heading | `## vN` |
| `energy_transition.grf` | built from the NML | rebuild after changing the NML |

Leave `min_compatible_version` (NML) and `MinVersionToLoad()` (GS) alone unless a change breaks existing saves. If it does, set them to the new `N` and say so in the changelog.

### When cutting a release

1. Add 1 to the number in `VERSION`.
2. Update every place in the table above.
3. Rebuild the GRF: `nmlc --grf=energy_transition.grf energy_transition.nml`.
4. Commit, then tag the commit `vN` and publish the GitHub release from that tag.

Only move to a new number when you're cutting a release, not for each change in between.

If you notice the files don't match `VERSION` or the latest release, point it out. Don't quietly change the numbers as part of an unrelated change.

## readme.txt must track README.md

OpenTTD's in-game UI (NewGRF Settings, AI/Game Script Settings, and the
BaNaNaS content window) shows bundled `.txt` files as plain text — it
cannot render Markdown or HTML. `README.md` is GitHub-facing and uses
Markdown/HTML (image banners, tables, links); `readme.txt` is the
plain-text mirror players see in-game, and `INSTALL.txt` is its
already-existing installation-only counterpart.

Whenever `README.md`'s player-facing content changes (mod description,
compatibility, how it works, NewGRF/Game Script parameters, energy
timeline), update `readme.txt` to match in plain text: no Markdown syntax
(`**bold**`, `` `code` ``, `[text](url)`) and no HTML (`<img>`, `<p
align="center">`, tables). Reflow Markdown tables as simple aligned text,
and images as their `alt` text or omit them.

`readme.txt` does not need repo-only sections like "Rebuilding from
source" — only what a player would want to read in-game.

If you notice `readme.txt` has drifted from `README.md`, point it out.
Don't quietly change one without the other.

## Verify changes in the game

A change isn't fixed until it has been seen working in OpenTTD. A clean
`nmlc` build, a read of the compiled NFO or a `tools/preview.py` image
only shows the GRF compiles and the art renders. None of them shows the
game does what was intended.

For every change to the NML, the GRF, the sprites or the Game Script:

1. **Run the headless check:** `python3 tools/ingame_check.py`. It loads the
   GRF and Game Script in a real OpenTTD with no screen, generates a map,
   runs a few game months, and fails if:
   - the GRF doesn't load, or the Power or Uranium cargo is missing;
   - an industry doesn't accept or produce exactly the cargos listed in
     `tools/ingame_check_gs/main.nut`;
   - a generator or the Uranium Mine produces nothing, or the Nuclear
     Power Plant produces power with no uranium delivered;
   - either Game Script errors, or the real one doesn't find Power.

   It needs `openttd` and `openttd-opengfx` (`apt install openttd
   openttd-opengfx`). When you change an industry's cargos or add an
   industry, update the `EXPECTED` table in
   `tools/ingame_check_gs/main.nut` in the same change. Paste the result
   into the PR under Testing.
2. **Check it by eye in a local game.** The headless check can't see art,
   cargo icons, animation, windows or text. List what a person needs to
   look at in the PR's Testing section. For example:
   - which window to open (industry chain, station, cargo payment graph);
   - which zoom levels;
   - a new game and an existing save.

Until both have been done, say so plainly. Write "not yet verified
in-game" in the PR, don't close an issue as fixed, and don't describe
the change as working. If the headless check can't run (for example
OpenTTD can't be installed), say that too, rather than skipping it
silently.

## Sprite design spec

`docs/sprite_design_spec.md` sets out how every sprite should look.
Follow its **Decided** rules for any new or changed sprite.

Sprites are refined one at a time, with one issue per sprite under
issue #34. When a refinement should apply to every sprite (an outline
rule, a texture level, a palette choice, a zoom-level decision),
update the spec and its decision log in the same change. Put the rule
in `tools/make_sprites.py` as shared code, not in one draw function.
If a change only affects one sprite, leave the spec alone.
