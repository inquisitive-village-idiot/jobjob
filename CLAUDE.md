# Job Application Automator

Generates tailored resumes and cover letters at scale, uploads to Google Drive, and
stores them in a consistent directory structure. Batch-processes multiple applications
in a single run with minimal manual touchup.

> The product values (cover-letter rules, voice, credentials below) are current and
> authoritative. For repo structure and configuration, **README.md / docs/ are the
> source of truth** — the package is `jobjob/` (CLI + webapp), not a single script.

## Repo Structure

```
jobjob/                   # Python package: CLI (apply/enrich), loaders, ailib, gapi
  prompts/                # Bundled default prompt templates (app behavior)
config/.env               # App config — machine-local, gitignored (template committed)
static/example/           # Bundled read-only example profile (content/reference/config);
                          #   also the fallback when no profile is active
webapp/                   # FastAPI backend + React frontend (local dashboard)
tests/                    # Tests + tests/fixtures (example JD/profile PDFs)
```

Credential content + reference docs live in **profile repos** (`content/`,
`reference/`, `config/.profile`), selected via the app config's profile registry —
see README.md and the `jobjob-config-profiles` design. The bundled example profile
(`static/example/`) doubles as the fallback (tests / fresh clone / no active profile).

## How the Script Works

Five sequential API calls per application, all sharing a single cached context prefix:

1. **JD parse** – Extracts role level, domain, required skills, location, explicit requirements
2. **Highlight selection** – Picks the most relevant credential blocks for this role
3. **Resume update** – Swaps objective; adjusts profile/mission emphasis via `replaceAllText` on the Google Doc template
4. **Cover letter generation** – Assembles from selected blocks, mirrors JD language, natural voice
5. **Skills analysis** – Gap check; flags anything not met or not honestly claimable

Output per application:
- Google Doc: `Resume` (copy of template, updated in place)
- Google Doc: `CoverLetter`
- Resume PDF uploaded to Drive
- All stored in `YYYY-MM-DD - Company Name - Role Title` directory under `APPLICATIONS_OUTPUT_DRIVE_ID`

## Caching Architecture

- **Anthropic prompt caching** – Stable context (resume, STAR examples, cover letter examples, background) sent as a cached system message prefix. All five calls reuse this. Cache is ephemeral (5 min, extended by hits).
- **Local file cache** – SHA256-keyed, stored in `~/.cache/job-apply`. Key is scoped by model, so the same prompt under different models caches separately. Skips identical prompts on re-runs. Controlled by `CLAUDE_CACHE_ENABLED`.
- **Cost implication** – Stable content should stay at the top of the cached context and not change between calls. Variable content (JD, company name) goes at the end.

## Reference Docs (active profile's `reference/`)

The active profile repo supplies reference docs (falling back to `static/example/reference`):

```
reference/
  background.*            # Career narrative, relocation intent, context
  writing_style.*         # Voice/style guidance
  cover_letters/          # *.txt/*.md/*.pdf – style anchors, voice examples
  stars/                  # STAR-format experience docs (.docx)
```

Credential content (highlights, skills, templates) lives in the profile's
`content/*.toml`. STAR documents are the honesty enforcement layer – Claude draws on
these rather than inferring credentials; a JD requirement without support is flagged,
not bridged.

## Cover Letter Rules

These apply on every generation. Do not relax them:

- **Only true statements.** If a claim isn't in `credentials.md` or a STAR doc, it does not go in the letter.
- **Gaps by omission, not disclaimer.** Do not write defensive language about what the applicant hasn't done. Emphasize what they have.
- **Geography.** Default: "open to relocation" only, or nothing. Do not assert European presence unless the role explicitly requires it and the context supports it.
- **Gap flags go at the top** of the cover letter as a deletable list – clearly marked, not inline. You will remove these before sending. Format:

  ```
  ⚠️ GAPS / FLAGS – DELETE BEFORE SENDING
  - [Requirement]: [brief note on gap or uncertainty]
  ---
  ```

- **Voice rules** (see below) apply to all generated text.

## Voice and Writing Rules

- Show don't announce. If it sounds like credentials being listed, rewrite.
- Spaced en dashes ` – ` not em dashes. Capitalize after colons used to introduce or clarify a thought.
- Vary sentence structure and word choice. No corporate-speak, no performative-declarative patterns.
- No weak gerund openings ("Translating complex challenges..."). No "This is what I did at X, and it's what interests me about Y" constructions.
- Open with a company-specific insight or genuine hook, not a self-description.
- Target length: 300–400 words. One page.

## Core Credentials (Anchor These)

The applicant's verifiable credentials live in the **active profile's** content and
reference docs (`content/highlights.toml`, `reference/stars/`, `reference/background.*`) —
not in this file. Anchor every claim to those; do not invent variations or bridge a gap the
documented credentials don't support.

The bundled demo profile is a fictional persona, **Tila Mer** (a print science
correspondent — see `static/example/`), used so the tool ships with a
coherent, runnable example. Replace it with your own content via the Static Content page.

## Configuration

Two disjoint tiers (validated at load; no overlap). Full reference: README.md /
docs/guide/configuration.rst.

**App config** — `config/.env` (machine-local, gitignored; `config/.env.template`
committed):

| Variable | Description | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `CLAUDE_MODEL` | Model (default: `claude-sonnet-4-6`) | No |
| `GOOGLE_CREDENTIALS_FILE` / `GOOGLE_TOKEN_FILE` | OAuth credentials / token | Drive only |
| `APPLICATIONS_INPUT_DIR` | Apply input/working root (default: `data`) | No |
| `APPLICATIONS_OUTPUT_DIR` / `APPLICATIONS_OUTPUT_DRIVE_ID` | Local mirror / Drive output folder | No |
| `ENRICHMENT_INPUT_DIR` | Enrich input root (blank ⇒ applications input) | No |
| `ENRICHMENT_OUTPUT_SHEET_ID` | Contacts sheet (enrich) | enrich only |
| `CACHE_DIR` / `CLAUDE_CACHE_ENABLED` | Local response cache | No |
| `JOBJOB_PROFILE_<NAME>` / `JOBJOB_ACTIVE_PROFILE` | Profile registry + active | Yes |

Deprecated aliases still read (rename to the above; auto-migrated in `config/.env`):
`DATA_DIR`→`APPLICATIONS_INPUT_DIR`, `APPLICATIONS_LOCAL_DIR`→`APPLICATIONS_OUTPUT_DIR`,
`APPLICATIONS_FOLDER_ID`→`APPLICATIONS_OUTPUT_DRIVE_ID`,
`LINKEDIN_SHEET_ID`→`ENRICHMENT_OUTPUT_SHEET_ID`.

**Profile config** — `<profile-repo>/config/.profile` (committed): `RESUME_TEMPLATE_ID`,
`APPLICANT_NAME` / `_PHONE` / `_EMAIL` / `_LINKEDIN`, `INDUSTRY` (optional domain hint
injected into the resume-objective prompt). No local paths, no secrets.

(`REFERENCE_DOCS_DIR` is removed — reference docs come from the active profile's
`reference/`.)

## Code Style

- Logging via `logging` module throughout. Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- `print()` only for stdout piping use cases
- All path construction via `pathlib.Path` with `.expanduser().resolve()` chained
- No hardcoded column indices or file positions

## Planned Work

- `credentials.md` – ground truth of verifiable claims; used by gap analysis step
- `blocks/` directory – pre-written credential blocks with YAML metadata (role levels, domains, claims, JD keywords) for deterministic block selection
- `archetypes/` – role-type templates that specify which blocks to pull and what to emphasize
- Gap analysis as a discrete step between JD parse and cover letter generation, comparing parsed requirements against `credentials.md`
- Resume objective/profile/mission as a block-aware swap rather than independent `replaceAllText` calls
