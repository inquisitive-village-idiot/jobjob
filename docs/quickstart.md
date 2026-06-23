# Getting started

**jobjob** reads a job posting (PDF, URL, or pasted text) and writes a tailored résumé
summary and cover letter from your background — saved on your computer and, optionally,
to Google Drive as editable Docs. It runs as a small local website you open in your
browser.

It calls **Claude** (Anthropic's AI); you pay Anthropic about **$0.20–0.50 per
application** — there is no jobjob subscription. (A [free, experimental
option](install-free-option.md) exists too.)

**Time:** about 30–60 minutes the first time (mostly the one-time account setup); a
couple of minutes per application after that. The steps cover **Windows, macOS, and
Linux**.

Work through the three sections in order:

## Installation

1. [**Create your accounts**](install-accounts.md) — Anthropic API key (required) and a
   Google account (optional, for Drive/Docs). Costs and a free option are called out
   here.
2. [**Set up the Google project**](install-google-project.md) — *optional*; needed only
   for Google Drive/Docs output. Produces a `credentials.json`.
3. [**Install the software**](install-software.md) — get the `jobjob-app` command via
   `uv` (recommended), `pipx`, or `pip`.

## Setup

- [**Setup with the wizard**](setup-wizard.md) — the easy path: enter your key, connect
  Google, and add your details in the browser.
- [**Local configuration (advanced)**](setup-local-config.md) — the same settings by
  editing config files, plus the full key reference.

## Usage

- [**Applications**](usage-applications.md) — generate a tailored résumé + cover letter.
- [**Enrichment**](usage-enrichment.md) — import LinkedIn contacts into a Google Sheet.

---

## Where your files live

Everything is under your jobjob folder (default `~/Documents/jobjob`):

```
~/Documents/jobjob/
  config/.env          ← your settings (wizard/Settings, or edit by hand)
  data/jobs/           ← job-description PDFs
  data/completed/      ← finished applications
  profiles/local/      ← your content + reference documents
```

See [Profiles](profiles.md) for the content/profile model, and
[Architecture](architecture.md) for how the package is laid out. Contributing or running
from source? See the [Developer reference](setup.md).
