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
