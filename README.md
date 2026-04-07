# Voice2Code

Voice2Code is a macOS-focused voice-to-instruction refiner for developer workflows. It keeps the current product shape intentionally small:

- `AI提纯指令.workflow` provides the cross-app Quick Action entry point
- `Voice2Code.app` acts as the minimal settings and runtime control shell
- the local Python refiner core handles intent routing, dynamic prompt assembly, bilingual contracts, and provider-neutral LLM execution

The current release goal is **stable local delivery**, not a fully packaged notarized macOS app.

## What It Does

Voice2Code is designed for the common workflow:

1. dictate or paste rough text into any macOS text field
2. select the text
3. trigger the Quick Action
4. replace the selection with a cleaner, structured instruction

Typical use cases:

- refining spoken engineering tasks into implementation-ready text
- turning rough notes into clearer issue / PR / TODO language
- normalizing bilingual Chinese / English developer input

## Current Architecture

Current delivery shape:

- `Quick Action + Voice2Code.app`

Core behavior:

- two-stage refinement pipeline
  - stage 1: minimal routing (`main_scene`, `structure_mode`)
  - stage 2: resolved contract generation
- bilingual contracts
  - Chinese input -> `zh-CN`
  - English input -> `en-US`
- provider-neutral AI service layer
  - `gemini`
  - `openai`
  - `doubao`

Current baseline:

- Gemini is the primary release baseline
- OpenAI is integrated and minimally validated
- Doubao is integrated in code but still needs real-key validation

## Project Status

This repository is in **closeout / stabilization** phase.

What is intentionally in scope:

- stable install flow
- Quick Action registration
- initialization flow
- provider selection / network config / connectivity test
- regression, token smoke, and quality evaluation assets

What is intentionally *not* a current release gate:

- full macOS app notarization
- complete `SecItem* + codesign + entitlement` delivery
- stronger system-level secret persistence guarantees
- plugin productization

## Install Shape

The current installer flow is intentionally simplified into two stages:

1. install confirmation
2. initialization window
   - provider selection
   - direct / proxy choice
   - API key input
   - connectivity test
   - automatic refinement smoke test
   - in-window completion state

The successful path no longer opens a third standalone completion dialog.

## Repository Layout

Top-level folders:

- [`config/`](config/) runtime configuration
- [`docs/`](docs/) architecture, PRD, implementation and closeout docs
- [`scripts/`](scripts/) build, installer, app shell, and refiner code
- [`tests/`](tests/) regression, smoke, and evaluation tooling

Recommended starting points:

- [PRD](docs/Voice2Code_PRD.md)
- [Architecture](docs/Voice2Code_Architecture.md)
- [Implementation Checklist](docs/Voice2Code_Implementation_Checklist.md)
- [Project Closeout Checklist](docs/Voice2Code_Project_Closeout_Checklist.md)

## Build and Validation

Common local commands:

```bash
python3 scripts/build_dist.py
python3 tests/run_voice2code_regression.py
python3 tests/run_voice2code_token_smoke.py
python3 tests/run_voice2code_quality_eval.py
```

The build produces versioned installer artifacts under `dist/`.

## Security / Credentials

Voice2Code does **not** ship with embedded provider keys.

Current behavior:

- environment variables can explicitly provide provider API keys
- the app shell may persist configuration when the current environment supports it
- plaintext API keys are not written into repo config files

Important boundary:

- this repository does **not** currently claim that system-level seamless secure storage is fully solved as a release guarantee

## License

This project is licensed under the Apache License 2.0. See [`LICENSE`](LICENSE).
