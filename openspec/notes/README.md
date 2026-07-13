# openspec/notes

Working notes that feed the OpenSpec `specs/`. **Not specs themselves** — no `SHALL`
statements or scenarios here. This is the raw material (current-state description,
design rationale, and the original design conversations) from which the capability
specs under `openspec/specs/` are authored.

## Contents

- **`build-requirements-and-decisions.md`** — my synthesis of what jobjob currently
  *is* and the decisions behind it, organized by capability. The primary seed for
  `specs/`. Accurate to the shipped 2.8.0 codebase as of 2026-07-02.
- **`original/`** — the design/requirements docs extracted from the earlier
  `rym-jobjob` project, where the original design conversations happened. Each carries
  a **migration note** at the top calling out what has since changed. Kept verbatim
  below that note for provenance.

## Two authoring conventions (agreed 2026-07-02)

These govern how notes become specs:

1. **Mechanism-agnostic requirements.** A spec states the *behavior* (`SHALL`), never
   *how* it is enforced. "Open with a company-specific hook" is a requirement whether
   it is realized by a prompt, post-processing, or a fine-tune. Do not write "enforced
   by the prompt" into a requirement — that couples the spec to an implementation and
   reintroduces drift.
2. **Requirement → realization traceability, recorded separately.** Capture *where* a
   requirement is realized (e.g. a prompt template + a validator) in the change's
   `design.md` or a `<!-- realized-by: … -->` comment, so the trace exists without
   polluting the `SHALL`. This matters because much of jobjob's behavior lives in
   committed prompt templates (`jobjob/prompts/*.txt`) rather than imperative code.

## The point of this (anti-drift)

The reason existing features are being spec'd — against the usual "only spec changes"
advice — is to freeze current behavior as a durable, reviewable reference so future
work can't silently drift it. The process rule that makes it real:

> **No behavior change without an OpenSpec change that MODIFIES the affected
> requirement.** A prompt edit that weakens a rule is a spec-affecting change.

LLM-enforced requirements are only weakly testable, so where a rule has a mechanical
core (en-dash substitution, word-count, a fixed block format), extract it into a
validator with real tests; use eval/golden checks for the judgment parts.
