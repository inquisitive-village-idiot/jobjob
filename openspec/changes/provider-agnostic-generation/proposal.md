# Provider-Agnostic Generation

> Proposal only (not implemented in `application-identity` / item 6). Split out
> during phase-2 scoping (2026-07-12): the storage adapter can *place and
> archive* whatever artifacts a mode produces, but résumé/cover/README
> **generation** itself is still Google-Docs-coupled, so a local build produces
> no résumé. Decoupling generation is its own change. Release inclusion is the
> user's call and does **not** block the 3.0.0 release.

## Why

Document generation is bound to Google Docs. `tailor_resume`
(`jobjob/apply/generate/resume.py`) edits a *copied Google Doc* in place:
it reads the doc via `gapi.docs`, locates each editable region by heading
(`find_section`), and rewrites the objective + highlights with
heading-anchored `replace_paragraph_text_requests` batch updates. The résumé
only ever exists as a Doc; the résumé path runs inside `_run_drive_resume_steps`
(`jobjob/apply/workflow.py`). The cover letter and README each already have a
local python-docx renderer (`jobjob/apply/output/cover_letter_docx.py`,
`readme_docx.py`) **and** a Drive path — but the résumé has no local renderer
at all.

Consequence: **local mode (no Drive credentials) cannot produce a résumé.**
The storage-adapter work in `application-identity` unifies *where* artifacts
land and *how* they archive, but it cannot conjure a résumé the local pipeline
never generates. The generation step needs the same "adapter, dispatched per
backend" treatment the storage layer is getting — otherwise "one output dir,
local or Drive per file type" is only half true.

## What Changes

- **Generation adapter seam.** Introduce a `GenerationAdapter` (or
  `DocumentRenderer`) Protocol mirroring the `AIAdapter` / `StorageAdapter`
  idiom: one concrete Drive-backed impl (today's `tailor_resume` + the
  gdoc cover/README paths) and one **local** impl. The workflow selects the
  impl the same way it selects the storage backend — the content strategy
  (which section, what text) stays shared; only the rendering mechanism differs.
- **Local résumé renderer** via python-docx, mirroring the existing
  `cover_letter_docx.py` / `readme_docx.py` renderers. It must reproduce
  `tailor_resume`'s **heading-anchored section replacement** against a local
  `.docx` template: locate each configured `ResumeSection` by heading, replace
  the objective (model-written) and the Key Career Highlights bullets
  (selected highlights verbatim, bullet formatting retained), swap the
  `PLACEHOLDER` role token, and surface unfound sections as README issues —
  same contract, local substrate.
- **Content/rendering split.** Factor the model-call + selection logic
  (objective prompt, highlight selection) out of the Docs I/O so both adapters
  call one strategy and differ only in how they apply edits. The Docs layer
  (`gapi.docs`) becomes the Drive renderer's backend; python-docx the local
  renderer's.
- **PDF is deferred.** No local PDF requirement now (the cover letter already
  has `cover_letter_pdf.py`; résumé PDF export from `.docx` is out of scope
  here). A LaTeX-based path is noted as a *later* option, not part of this
  change.

Explicitly **not** in scope: changing the résumé *content* strategy or prompts;
a local PDF résumé; new templates beyond a local `.docx` equivalent of the
current Doc template; anything in the storage/archive layer
(`application-identity` owns that).

## Capabilities

### New Capabilities

- `provider-agnostic-generation`: a generation-adapter seam with Drive and
  local (python-docx) renderers, and a local résumé renderer reproducing the
  heading-anchored section replacement.

### Modified Capabilities

- None yet — deltas at spec time. The workflow's résumé step
  (`_run_drive_resume_steps`) is generalized to renderer selection.

## Impact

- `jobjob/apply/generate/resume.py`: split content strategy from Docs I/O.
- `jobjob/apply/output/`: new local résumé renderer (python-docx), sibling to
  `cover_letter_docx.py` / `readme_docx.py`.
- `jobjob/apply/workflow.py`: `_run_drive_resume_steps` → renderer-agnostic
  résumé step selecting Drive vs. local.
- `jobjob/generation/` (or similar, new): `GenerationAdapter` Protocol + the
  two concrete renderers.
- `tests/`: local renderer unit tests (heading-anchored replacement on a
  fixture `.docx`), adapter selection.

## Sequencing

Independent of `application-identity` item 6 and of the 3.0.0 release. It
*complements* the storage adapter — once both land, a fully local build both
generates and places a résumé — but neither blocks the other. Slot after the
3.0.0 release unless the user pulls it forward.
