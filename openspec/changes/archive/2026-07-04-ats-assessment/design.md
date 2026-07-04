# Design: ATS Assessment

## Context

The apply workflow updates a Google Doc resume from a template and exports a PDF.
`gapi/docs.py` already exposes `get_document_text()` (plain text) and
`get_document()` (full structural JSON — paragraphs, tables, heading styles). The
`skill-cloud` change (prerequisite) canonicalizes JD requirements; the skills
analysis classifies evidence. Fit scoring (sibling change) scores documented
experience; this change scores the *rendered resume*.

## Goals / Non-Goals

**Goals:**
- Deterministic coverage score: JD canonical skills vs generated resume text.
- Parseability heuristics over the doc structure we already fetch.
- Recommendations bounded by evidence — never suggest an unevidenced skill.
- All weights/thresholds tunable in one obvious place, pending calibration.

**Non-Goals:**
- Vendor-specific ATS emulation (proprietary; the cloud mimics the class, not a
  brand).
- Auto-applying recommendations to the resume (human reviews; future change at
  most).
- Cover-letter ATS scoring (letters are read by humans when read at all).

## Decisions

### Decision 1: Match against the rendered doc text, not the template or PDF

Coverage runs on `get_document_text()` of the *updated* resume doc — after
`replaceAllText` edits — so it scores what a recruiter's ATS would ingest.
Structural checks use `get_document()` on the same fetch (one Docs read serves
both). PDF text extraction is avoided: the Doc is the source the PDF derives from,
and its structure is machine-readable without OCR-ish parsing.

### Decision 2: Coverage is deterministic; three buckets per JD skill

For each canonical JD requirement: **present** (canonical name or alias found in
resume text, case-insensitive, word-boundary), **missing-evidenced** (absent from
resume but supported in the skills analysis — the actionable bucket),
**missing-unevidenced** (absent and unsupported — a fit gap, not an ATS fix).
Coverage score = weighted presence over canonical requirements (criticality
weights reuse the fit-scoring constants). UNMAPPED requirements are listed but
unscored, consistent with fit scoring.

### Decision 3: Recommendations require evidence AND skills-file membership

`content/skills.toml` is the user's declared skill set and acts as the allowlist:
a recommendation requires the skill to be both evidenced (skills analysis) and
declared (resolves to a skills-file entry). Each recommendation cites its evidence
source (which STAR/highlight supports the skill). This is the honesty layer
applied to keyword optimization: the tool may surface skills the applicant
demonstrably has, declared, and simply failed to render; it must never propose
bridging. Phrasing suggestions stay factual ("X is supported by <evidence> but
absent from the resume text"), not generated resume copy.

Two informational side-channels fall out of the gate (README-only, never fed to
generation):
- **Skills-file candidates**: evidenced but undeclared — the manual seam a future
  auto-update-skills-file feature would automate.
- **Up-skill targets**: missing-unevidenced JD skills — things the user could
  learn, listed for the human, excluded from resume/cover-letter generation
  entirely.

### Decision 4: Parseability as a small, named heuristic set

Initial checks over the doc structure: content inside tables (many parsers drop
table cells), non-standard section headings (vs a recognized set: Experience,
Education, Skills, etc.), images/text boxes, multi-column layouts. Each check
returns pass/warn with a one-line reason. Checks are template-dominated, so
results will be stable across applications using the same template — reported per
application anyway (cheap, and template edits get caught).

### Decision 5: Provisional constants, calibration in-scope

All weights and thresholds live as module-level constants in one place, documented
as provisional. A calibration task compares output against prior LLM-based ATS
assessments and expert feedback; expect the parseability set and recommendation
thresholds to change. Do not spread tuning knobs across modules.

## Open Questions

- Alias matching in prose: word-boundary matching of multi-word aliases is mostly
  fine; abbreviation collisions (e.g., "R") may need per-entry match rules in the
  cloud. Defer until a real false positive appears.
- Whether parseability warnings should also surface at template-selection time
  (earlier signal) rather than only in the README. Defer.
