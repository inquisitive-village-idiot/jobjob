# Applications — generate a résumé + cover letter

The core feature: give jobjob a job posting and it tailors a résumé summary and cover
letter from your [profile](profiles.md), saving them locally and (optionally) to Google
Drive.

**Before you start:** [install](install-software.md) and
[set up](setup-wizard.md) jobjob, and add some background content (Static Content tab, or
import a résumé). Configuration keys for this feature live under **Applications** in
[Local configuration](setup-local-config.md#app-config-configenv).

## In the app

1. **Add a job posting** — use **Add JD** to *paste the text*, *fetch a URL*, or *upload
   a PDF*. (You can also drop a PDF into `<jobjob folder>/data/jobs/`.)
2. In the **Queue** tab, find the posting and click **Apply**.
3. Watch progress; the finished application appears on the **Dashboard**.

> The cover letter starts with a **⚠️ GAPS / FLAGS – DELETE BEFORE SENDING** section
> listing anything the AI couldn't match to your documented background. Review and delete
> it before sending — jobjob flags gaps rather than inventing qualifications.

## On the command line

```
jobjob apply <job_description.pdf> [options]
```

| Flag | Description |
|---|---|
| `-o / --output <dir>` | Output directory (default: `./out/<date> - <Company> - <Role>/`) |
| `--skip-drive` | Local artifacts only; no Google Drive/Docs |
| `--template <name>` | Force a résumé archetype (else the model classifies the JD) |
| `--no-cache` / `--clear-cache` | Disable / purge the response cache |
| `--reprocess` | Re-run a previous application in place (point at the JD inside its output dir) |

## Where output lands

**Locally**, under `<jobjob folder>/data/completed/` (or `--output`):

```
YYYY-MM-DD - Company - Role/
  JD_Company_Role.pdf   Resume.pdf   CoverLetter.pdf / .docx
  skills_analysis.json  README.docx  summary.json
```

**On Google Drive** (if connected): a folder `YYYY-MM-DD - Company - Role` under your
`APPLICATIONS_OUTPUT_DRIVE_ID`, holding the README, JD copy, Résumé, and CoverLetter as
editable Google Docs.

## See also

→ [Configuration](setup-local-config.md#app-config-configenv) · [Profiles](profiles.md)
· [Enrichment](usage-enrichment.md)
