# ScreenLedger — Engineering and Product Proposal (Implemented v1 Scope)

**Version:** 1.0 | **Status:** Working local CLI release candidate, pending independent user study and external cross-platform CI. | **Prepared:** November 2026

## Executive decision

ScreenLedger addresses the failure of ad-hoc game UI asset handoffs: an artist can deliver PNGs without the screen inventory, component geometry, safe areas, interaction semantics, and mandatory button states required by a developer. The deliverable is a deterministic offline validator and text handoff, not a game editor or a visual renderer. An earlier design allowed missing state requirements to disappear from the same manifest and omitted implementation-grade layout contracts. The current design closes those conceptual gaps and supplies executable evidence.

## User and product

The primary user is a technically comfortable indie developer or UI artist collaborating with a programmer. A separate reviewed `requirements.json` specifies screens, components, kinds, and button events. `screens.json` contains the actual design handoff. A fixed touch profile requires default and pressed button assets even when the artist omits both from their declared state list. Only an explicit reviewer waiver with a reason can exempt pressed state. The report flags missing screens/components, action mismatches, incomplete geometry, PNG failures, unsafe paths, and z-order ambiguity.

## Implementation boundary

The supported v1 contract covers one reference viewport per screen, `uniform_fit_center` scaling, reference-pixel safe area, image/button components, pixel rectangles, hitboxes, `contain/cover/stretch` image fit, z-index, action identifiers and behavior notes, and static PNGs. All coordinates are declared in reference pixels. Scaling uses a single uniform factor to fit the target viewport, centers the result, and letterboxes unused space. No runtime responsive reflow or actual game engine code is generated. Validation can prove specification completeness under the declared contract, not final rendered visual quality or accessibility.

## Architecture

Python 3.10+, Pillow for bounded image decoding, stdlib JSON and CLI. The validator is separate from the CLI and returns structured, deterministic findings. Input JSON is capped at 2 MB per file; PNGs at 16 MB, 8192 pixels per dimension and 16 million decoded pixels. POSIX asset paths are opened using `O_NOFOLLOW` and directory descriptors to reject symlink traversal; Windows path validation is best effort and does not guarantee safety against concurrent hostile directory replacement. Source PNGs are never rewritten. Reports contain only project-relative paths and do not embed images.

## Independent contract and error behavior

`requirements.json` is owned by the reviewer; `screens.json` is supplied by the artist. The required-state profile is implemented in the tool, not derived from `screens.json`. Waivers are explicit records. `handoffReady` is true only if all independent requirements, assets, layout, and interaction checks pass. JSON reports use stable finding codes and deterministic ordering. CLI exit 0 means valid, 1 means blocking findings, 2 means invalid input or output destination, and 3 means operational error.

## Security and privacy

No account, network calls, telemetry, image uploads, arbitrary code execution, or credentials. The included assets are synthetic examples made specifically for the repository. The tool rejects unsafe asset paths, symlinks and non-PNG content. Report destinations are explicitly chosen outside the project root and refuse overwrite. The project is not a sandbox for hostile images or a tamper-proof approval system. Requirements and waivers remain editable local files and must be reviewed and version-controlled externally.

## Demonstrated acceptance

The supplied automated test suite checks an unchanged valid handoff; missing required screens, components and button states; omitted layout; bad interaction; safe-area and hitbox violations; duplicate components/states/z-index; absent/corrupt/unsafe PNGs; case collisions; valid and conflicting waivers; CLI exit codes; deterministic reports; and unchanged original PNG checksums. The suite passed locally on Linux. The package was installed in editable mode without dependency downloading using preinstalled dependencies, and the `init`, `validate`, and `handoff` commands were smoke-tested. The GitHub Actions matrix is included but has not run remotely. No independent usability research or third-party security audit has been performed.

## Deployment and governance

The source is packaged with `pyproject.toml`, MIT license, contributing and security policies, synthetic sample, automated tests, and GitHub Actions matrix. Dependency updates, cross-platform testing, user trials, and maintenance ownership are prerequisites to claiming a stable public release.

## Roadmap

1. **Complete now:** deterministic CLI, independent requirements, fixed touch profile, geometry contract, synthetic examples, test suite, installation docs, and text reports.
2. **Pre-release QA:** verify CI on Windows/macOS/Linux, add stronger Windows filesystem protection, expand image-format edge cases, and run 6–10 independent user tests against a manual checklist.
3. **Future only if justified:** a no-code UI, responsive multi-viewport specifications, visual diff or preview, engine-specific adapters, and optional AssetLock integration. These are not claimed as delivered.

## Public evidence standard

The repository should be judged on the runnable code, deterministic tests, documented limitations, cross-platform CI results, and independent review evidence rather than on a self-assigned numerical score.
