# Usage

## `jobjob apply` — generate a resume + cover letter

```
jobjob apply <job_description> [options]
```

| Argument / Flag | Description |
|---|---|
| `job_description` | Path to the job-description PDF |
| `-o / --output <dir>` | Output directory (default: `./out/<date> - <Company> - <Role>/`) |
| `--skip-drive` | Skip all Google Drive/Docs operations; write local artifacts only |
| `--template <name>` | Force a specific resume archetype (e.g. `features_writer`). If omitted the model classifies the JD against the active profile's `content/templates.toml`. |
| `--no-cache` | Disable the response cache for this run |
| `--clear-cache` | Purge the response cache before running |
| `--reprocess` | Re-process a previously generated application: point at the JD copy inside its output directory; local files and the original Drive folder are updated in place |

### Examples

```sh
# Full run — Drive folder + local artifacts:
jobjob apply ~/Downloads/acme_science_correspondent.pdf

# Local only, explicit output dir:
jobjob apply ~/Downloads/acme_science_correspondent.pdf --skip-drive -o ./out

# Force a specific resume template:
jobjob apply ~/Downloads/acme_science_correspondent.pdf --template features_writer

# Update an existing application in place:
jobjob apply out/Acme\ -\ Science\ Correspondent/JD_Acme_ScienceCorrespondent.pdf --reprocess
```

### Local output layout

```
out/
  YYYY-MM-DD - Company - Role/
    JD_Company_Role.pdf          # copy of the input JD
    Resume.pdf       # customized resume PDF
    CoverLetter.pdf  # cover letter PDF
    CoverLetter.docx # cover letter DOCX
    skills_analysis.json         # gap analysis (also folded into README.docx)
    README.docx                  # per-application summary document
    summary.json                 # metadata (folder_id, job_info, token usage)
```

### Google Drive layout

A folder named `YYYY-MM-DD - Company - Role` is created under `APPLICATIONS_FOLDER_ID`
and contains exactly four artifacts:

- `README` (Google Doc) — per-application summary
- `JD_Company_Role.pdf` — copy of the job description
- `Resume` (Google Doc) — customized resume
- `CoverLetter` (Google Doc) — cover letter

---

## `jobjob enrich` — import a LinkedIn profile into the contacts sheet

```
jobjob enrich <profile> [options]
```

| Argument / Flag | Description |
|---|---|
| `profile` | Path to the LinkedIn profile screenshot PDF |
| `--sheet-id <id>` | Spreadsheet id (overrides `LINKEDIN_SHEET_ID` in env) |
| `--sheet-name <name>` | Worksheet tab name (default: `Contacts`) |
| `--dry-run` | Parse the profile without writing to the sheet |
| `--no-cache` | Disable the response cache for this run |

### Examples

```sh
# Standard run — parse and append to the contacts sheet:
jobjob enrich ~/Downloads/jane_doe_linkedin.pdf

# Parse only (verify extraction without touching the sheet):
jobjob enrich ~/Downloads/jane_doe_linkedin.pdf --dry-run

# Write to a specific sheet:
jobjob enrich ~/Downloads/jane_doe_linkedin.pdf --sheet-id 1BxiMVs0XRA...
```

---

## Webapp

A local dashboard wraps both sub-commands in a browser UI with live progress streaming.
See [webapp/README.md](../webapp/README.md) for setup and launch instructions.
