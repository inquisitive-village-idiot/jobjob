# `jobjob`

[![CI](https://github.com/inquisitive-village-idiot/jobjob/actions/workflows/ci.yml/badge.svg)](https://github.com/inquisitive-village-idiot/jobjob/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/jobjob.svg)](https://pypi.org/project/jobjob/)
[![Python](https://img.shields.io/pypi/pyversions/jobjob.svg)](https://pypi.org/project/jobjob/)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue.svg)](https://inquisitive-village-idiot.github.io/jobjob/)
[![License: MIT](https://img.shields.io/pypi/l/jobjob.svg)](LICENSE)

Generate tailored resumes and cover letters at scale. Given a job description (PDF, a
URL, or pasted text), `jobjob` runs five sequential Claude calls — sharing one cached
context prefix — to parse the role, select credential highlights, tailor the resume,
draft a cover letter, and produce a skills gap analysis. It writes local artifacts and
(optionally) uploads to Google Drive.

> **New here?** Start with the
> [User Guide](https://inquisitive-village-idiot.github.io/jobjob/guide/index.html) — it
> walks through every step, no terminal experience assumed. Full docs:
> **<https://inquisitive-village-idiot.github.io/jobjob/>**

## Install

The simplest path is the bundled local app (a browser dashboard):

```sh
pipx install jobjob      # isolated install (recommended)
jobjob-app               # scaffolds a working dir, opens the dashboard
```

Or use the CLI directly:

```sh
pip install jobjob       # or, from a checkout: pip install -e .
```

Requires Python ≥ 3.12.

## How it works

`jobjob` tailors your application from a **profile** — a self-contained directory of
your content (`content/`), reference docs (`reference/`), and applicant identity
(`config/.profile`). The app ships with a read-only **example** profile (the fictional
*Tila Mer*) you can switch to or duplicate; you create your own profile blank and fill
it in (by hand or by importing an existing résumé).

Configuration is split into two **disjoint** tiers:

- **App config** (`config/.env`, machine-local) — your API key, Google credentials,
  output locations, and the profile registry.
- **Profile config** (`<profile>/config/.profile`) — the active profile's applicant
  identity and resume template.

See the
**[configuration reference](https://inquisitive-village-idiot.github.io/jobjob/guide/configuration.html)**
and the
**[profile model](https://inquisitive-village-idiot.github.io/jobjob/guide/profiles.html)**.

## Usage

```sh
# Generate a resume + cover letter from a job description:
jobjob apply path/to/job_description.pdf            # full run (Drive + local)
jobjob apply path/to/job_description.pdf --skip-drive -o ./out   # local only

# Import a LinkedIn profile screenshot into the contacts sheet:
jobjob enrich path/to/profile.pdf
```

See **[Applications](https://inquisitive-village-idiot.github.io/jobjob/guide/usage-applications.html)**
and **[Enrichment](https://inquisitive-village-idiot.github.io/jobjob/guide/usage-enrichment.html)**
for the full flag reference and examples.

## Documentation

All guides live on the published docs site:
**<https://inquisitive-village-idiot.github.io/jobjob/>**

- [User Guide](https://inquisitive-village-idiot.github.io/jobjob/guide/index.html) — first run, start to finish
- [Credentials](https://inquisitive-village-idiot.github.io/jobjob/guide/credentials.html) — API keys and Google OAuth
- [Configuration](https://inquisitive-village-idiot.github.io/jobjob/guide/configuration.html) · [Profiles](https://inquisitive-village-idiot.github.io/jobjob/guide/profiles.html)
- [Library Reference](https://inquisitive-village-idiot.github.io/jobjob/library/index.html) — architecture + Python API
- [REST API Reference](https://inquisitive-village-idiot.github.io/jobjob/restapi/index.html) — the local dashboard's HTTP API
- [Local dashboard](webapp/README.md) — the `webapp/` setup
- The docs source is under [`docs/`](docs/) (Sphinx + reStructuredText)

## Development

```sh
uv run --group test pytest          # run the test suite
cd webapp/frontend && npm run build # build the dashboard frontend
```

Released under the [MIT License](LICENSE).
