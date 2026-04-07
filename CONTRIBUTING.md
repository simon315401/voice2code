# Contributing to Voice2Code

Thanks for contributing.

This project is currently in a **stabilization / closeout** phase, so the best contributions are the ones that improve:

- install reliability
- Quick Action usability
- provider-neutral execution quality
- bilingual prompt behavior
- regression / smoke / quality tooling
- documentation consistency

## Before You Start

Please read these first:

- [README](README.md)
- [PRD](docs/Voice2Code_PRD.md)
- [Architecture](docs/Voice2Code_Architecture.md)
- [Implementation Checklist](docs/Voice2Code_Implementation_Checklist.md)
- [Project Closeout Checklist](docs/Voice2Code_Project_Closeout_Checklist.md)

## Good Contribution Targets

Contributions are most helpful when they focus on one of these areas:

- install flow simplification and reliability
- Quick Action registration and runtime behavior
- provider support and provider-specific compatibility fixes
- regression fixtures and quality evaluation assets
- prompt / contract improvements that are coherent and testable
- documentation cleanup and consistency

## Things To Avoid

Please avoid opening large changes that:

- redesign the whole product shape
- reintroduce long prompt-rule stacks into stage 1 routing
- add local semantic over-correction layers
- expand plugin productization into the current mainline
- claim stronger security guarantees than the code currently provides

## Development Notes

Core repository areas:

- [`config/`](config/)
- [`docs/`](docs/)
- [`scripts/`](scripts/)
- [`tests/`](tests/)

Common local checks:

```bash
python3 scripts/build_dist.py
python3 tests/run_voice2code_regression.py
python3 tests/run_voice2code_token_smoke.py
python3 tests/run_voice2code_quality_eval.py
swiftc -typecheck -framework AppKit -framework Security scripts/installer_ui.swift
```

If your change touches installer logic, please also verify:

- install flow still opens correctly
- Quick Action workflow files are still generated
- initialization flow still works

## Pull Request Guidance

Please keep pull requests focused.

A good PR should explain:

- what changed
- why it changed
- whether user-facing behavior changed
- how it was validated

Prefer small, reviewable PRs over broad refactors.

## Security

If you find a security-sensitive issue, please read [SECURITY.md](SECURITY.md) and report it privately first instead of opening a public exploit report.
