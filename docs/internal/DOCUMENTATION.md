# Documentation policy and feedback

## Standing policy

The README and linked user guides explain the product: what it does, how to use
it, and its concrete limitations. Write short, confident statements. Keep the
pixel-art party, backend characters and tasteful emojis. Personality is welcome;
meandering explanations and process narration are not.

Evidence remains public in `docs/internal/`, but outside the user documentation
path. Store runbooks, dated validation, release close-outs, investigation details
and this feedback here. Do not link them from the README or user guides.

State known limits directly. Keep version requirements and experimental labels
when they affect users. Never replace uncertainty with an unsupported claim;
resolve it through evidence or narrow the claim. Avoid ritual disclaimers about
how the work was checked and repeated explanations of what a comparison is not.

## Feedback ledger — 2026-09-11

The maintainer praised the README banner and its character classes for giving
the project personality. They rejected verbose, hesitant prose and prominent
links to exact run dates, verification logs and internal deliberation. The same
standard applies to every document directly linked from the README. They asked
for concise, assertive, useful writing with emojis, and authorized keeping this
feedback publicly in a tucked-away maintainer folder.

This policy belongs in project instructions and the release runbook so future
maintenance preserves the editorial standard. Historical evidence is retained;
public guides carry the conclusions and user actions.

## Documentation refresh validation

- Full suite with basedpyright: 251 passed, 1 existing expected failure (ty hover).
- Microsoft Pyright suite: 35 passed.
- Pyright type check: zero errors, warnings or information; Ruff lint passed.
- Wheel and source distribution built successfully with the revised README.
- Local documentation links and heading anchors passed; README links and artwork
  use absolute URLs for GitHub and PyPI.
- Parallel reviews covered backend claims, API guidance and publication steps.
- The low-level stdio example returned the expected assignment diagnostic; the
  normalized ty example returned token data and shut down successfully.

No library behavior, dependency versions or playground code changed.
