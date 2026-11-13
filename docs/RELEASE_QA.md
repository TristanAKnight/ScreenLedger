# Release QA — observed evidence and unresolved items

**Observed in this execution environment:** 30 local pytest tests passed on Linux; `init`, `validate`, and `handoff` ran successfully after editable installation with preinstalled dependencies. All included PNGs are newly generated synthetic examples. No private user art or documents are included.

**Not yet observed:** Remote GitHub Actions execution on Windows/macOS/Linux; external audit; user-study results; accessibility testing of a GUI (none exists).

**Known limits:** Only static PNGs, one viewport, uniform-fit scaling, two component kinds, no responsive reflow, no visual preview. Windows symlink/race protection is best effort. A user with write access can change both the requirements and the handoff. No code signing or package distribution is claimed.

**Release gate:** Before declaring production readiness, run the included CI matrix, check dependency licenses and advisories, review all test fixtures, complete a human security review, and conduct a small observed user study.
