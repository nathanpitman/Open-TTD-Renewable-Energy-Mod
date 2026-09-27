# CLAUDE.md

## Versioning

The GitHub release tag is the version. The NewGRF and the Game Script must both report that version so players, bug reports and saves all refer to the same number.

### Source of truth

- `VERSION` at the repo root holds the current release as `MAJOR.MINOR.PATCH` (for example `0.2.0`). It must match the latest GitHub release tag without the `v` (tag `v0.2` means `0.2.0`).
- Do not type a version number anywhere else by hand. Work it out from `VERSION`.

### Converting to the integers OpenTTD expects

OpenTTD needs whole numbers that always go up. Use:

```
version_int = MAJOR * 10000 + MINOR * 100 + PATCH
```

`0.2.0` → `200`, `0.2.1` → `201`, `1.0.0` → `10000`. Keep MINOR and PATCH below 100.

### Where the version appears

Keep all of these in step with `VERSION`:

| File | Field | Value |
|---|---|---|
| `energy_transition.nml` | `grf { version: … }` | `version_int` |
| `energy_transition.nml` | header comment (`NewGRF v…`) | `vMAJOR.MINOR.PATCH` |
| `energy_transition_gs/info.nut` | `GetVersion()` | `version_int` |
| `energy_transition_gs/info.nut` | `GetDate()` | release date, `YYYY-MM-DD` |
| `CHANGELOG.md` | newest heading | `## vMAJOR.MINOR[.PATCH]` |

Leave `min_compatible_version` (NML) and `MinVersionToLoad()` (GS) alone unless a change breaks existing saves. If it does, set them to the new `version_int` and say so in the changelog.

### When cutting a release

1. Update `VERSION`.
2. Update every place in the table above.
3. Rebuild `energy_transition.grf` so the compiled file carries the new version.
4. Commit, then tag the commit `vMAJOR.MINOR` (or `vMAJOR.MINOR.PATCH` for a patch) and publish the GitHub release from that tag.

If you notice the files don't match `VERSION` or the latest release, point it out. Don't quietly change the numbers as part of an unrelated change.
