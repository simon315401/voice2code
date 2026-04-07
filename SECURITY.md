# Security Policy

## Scope

This repository contains a local macOS developer tool that refines user-selected text through external LLM providers.

Current security priorities are:

- prevent accidental plaintext credential exposure in repository files
- avoid shipping embedded provider keys
- keep runtime behavior explicit about current credential and persistence boundaries
- avoid over-claiming system-level secure storage guarantees that are not yet a release gate

## Supported Security Posture

Current public releases should be evaluated with these assumptions:

- provider API keys are **user-provided**
- provider API keys are **not embedded** in source code or release artifacts
- plaintext provider API keys should not be committed into:
  - source files
  - config files
  - logs
  - installer result files
- environment variables may be used as an explicit runtime credential source
- current app-shell persistence behavior is environment-dependent and should not be described as a guaranteed system-level secure storage solution

## Reporting a Vulnerability

If you find a security issue, please do **not** open a public issue with exploit details first.

Please report it privately with:

- affected version
- reproduction steps
- impact assessment
- whether it affects source only, release artifacts, or both

Current contact path:

- open a private security report through GitHub if available
- or contact the maintainer directly before publishing details

If you are unsure whether something is security-sensitive, report it privately first.

## What Counts as a Security Issue Here

Examples that should be reported:

- embedded live provider keys in source or release artifacts
- plaintext API key leakage into logs, temp files, installer outputs, or command-line arguments
- unintended credential persistence in world-readable files
- Quick Action or app-shell behaviors that expose selected user text beyond the documented provider request path
- release packaging that includes sensitive local development artifacts

## What Is Not Currently Claimed

The project does **not** currently claim:

- notarized macOS app distribution
- fully completed system-level seamless secure storage as a release guarantee
- hardened protection against local machine compromise or runtime memory inspection

Please evaluate disclosures and usage expectations with those current boundaries in mind.
