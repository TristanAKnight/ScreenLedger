# ScreenLedger 1.0 — Game UI Handoff Validator

**Status:** Installable, functional command-line release candidate. Not a published PyPI package or externally audited security product.

ScreenLedger checks a designer's screen/layout/asset manifest against a separate reviewed requirements file. It finds missing screens, missing components, missing button states, unsafe or corrupt PNG references, layout safe-area problems, conflicting z-order, and interaction mismatches. It never edits source artwork. Everything runs offline.

## Install

Requires Python 3.10+.

```bash
python -m pip install -e .
```

## Run

```bash
screenledger validate --project examples/demo
screenledger handoff --project examples/demo
screenledger init my-first-project
screenledger validate --project my-first-project --output ../report.json
screenledger handoff --project my-first-project --output ../handoff.md
```

`init` creates a synthetic example in an empty directory; it does not infer a real game's requirements. **Replace both files with your own reviewed requirements and screen specs.** `validate` emits deterministic JSON, and `handoff` emits Markdown. `--output` refuses overwriting files and writes outside the project root.

## Two-file approval contract

`requirements.json` is an independent requirements inventory maintained/reviewed by a design lead. It specifies all required screens, components, their types, and button action IDs. The built-in `mobile_touch_v1` profile independently requires `default` and `pressed` PNG states for buttons and `default` for decorative images. Waivers for pressed states require a recorded reviewer and reason. This prevents an artist from accidentally omitting a state from both their asset list and the requirements they wrote in `screens.json`.

`screens.json` describes the implementation handoff: reference viewport, safe-area insets, `uniform_fit_center` scaling, letterbox color, per-component pixel rectangles, fit modes (`contain`, `cover`, `stretch`), z-index, button hitboxes, action events and behavior notes, and PNG paths.

**Layout semantics:** Coordinates are integer pixels in the declared reference viewport. `uniform_fit_center` scales all coordinates uniformly to fit the target viewport, centers the result, and letterboxes the remainder with the declared color. It does not dynamically reflow components or guarantee good results at every aspect ratio. Safe-area insets are in reference pixels. The reference layout should be reviewed on target devices; a single reference viewport is a deliberate v1 limitation.

**`handoffReady` means the declared requirements and supported technical constraints passed validation.** It is not proof the game was implemented, the layout is artistically correct, the asset matches an approved visual reference, or the UI is accessible.

## Results and exit codes

- `0` — validation completed and no blocking findings.
- `1` — validation completed with blocking findings.
- `2` — malformed project or invalid command output target.
- `3` — filesystem/operational failure.

Findings are sorted by path and code. JSON uses sorted keys, UTF-8 and LF line endings. No timestamps, personal paths, or image data are embedded in reports. The validator may read files and update filesystem access times depending on the filesystem, but never intentionally writes source images.

## Supported asset policy

Static PNGs only; filenames are relative to `assets/`. No symlinks, traversal paths, device files, or absolute paths. Maximum file size: 16 MB. Maximum decoded dimensions: 8192 per side and 16 million pixels. Windows fallback symlink checks are best effort, **not** safe against malicious concurrent filesystem replacement; do not run on untrusted mutable directory trees. Image validation is not a substitute for sandboxing arbitrary hostile files.

## Tests

```bash
python -m pip install -e '.[dev]'
pytest -q
```

CI workflow is included for Linux, Windows and macOS. Its success must be verified on GitHub after publication; a local Linux test run is not evidence that remote CI already passed.

## Licensing and publication

MIT-licensed original code and synthetic demo assets. No proprietary game artwork, private files, user credentials, or third-party character assets are included. This project is not connected to AssetLock and does not verify SHA-256 approval baselines.

## Limitations

No graphical interface, automatic art generation, automatic screenshot measurements, layout previews, game-engine adapters, image repair, GitHub deployment, or host integration. JSON manifests are intended for technically comfortable users. Requirements can be edited by someone with filesystem access: review and version-control the requirements separately for accountable handoffs. For strict security use a protected repository and human review.
