# Local configuration (advanced)

Everything the [Setup wizard](setup-wizard.md) does, you can also do by editing two text
files. Use this if you prefer the command line, run the CLI without the dashboard, or
need a setting the wizard doesn't expose.

jobjob has **two config files** (validated as disjoint — no key may appear in both):

- **App config** — `<jobjob folder>/config/.env` (machine-local; the default jobjob
  folder is `~/Documents/jobjob`).
- **Profile config** — `<profile>/config/.profile`, inside each profile directory (see
  [Profiles](profiles.md)).

## Opening a config file

Open the file in any plain-text editor:

- **macOS:** `open -e ~/Documents/jobjob/config/.env` (TextEdit), or use VS Code, etc.
- **Linux:** `xdg-open ~/Documents/jobjob/config/.env` or `nano ~/Documents/jobjob/config/.env`.
- **Windows (PowerShell):** `notepad $env:USERPROFILE\Documents\jobjob\config\.env`.

Lines are `KEY="value"`. Keep the quotes and avoid spaces around `=`.

## App config (`config/.env`)

Grouped by feature:

**AI (required)**

| Variable | Purpose | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (a secret — the wizard/Settings won't display it) | Yes |
| `CLAUDE_MODEL` | Model id (default: `claude-sonnet-4-6`) | No |
| `CLAUDE_CACHE_ENABLED` / `CACHE_DIR` | Response-cache toggle / directory | No |

**Google (for Drive/Docs output)**

| Variable | Purpose | Required |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | Path to the OAuth client-secrets JSON (default: `~/.config/jobjob/credentials.json`) | Drive/Sheets |
| `GOOGLE_TOKEN_FILE` | Path to the pickled OAuth token (default: `~/.config/jobjob/token.pickle`) | Drive/Sheets |

**[Applications](usage-applications.md) (apply)**

| Variable | Purpose | Required |
|---|---|---|
| `APPLICATIONS_INPUT_DIR` | Input/working root holding `jobs/`, `profiles/`, `completed/` (default: `data`) | No |
| `APPLICATIONS_OUTPUT_DIR` | Local synced Google Drive mirror (output) | No |
| `APPLICATIONS_OUTPUT_DRIVE_ID` | Drive folder id for output | No |

**[Enrichment](usage-enrichment.md) (enrich)**

| Variable | Purpose | Required |
|---|---|---|
| `ENRICHMENT_INPUT_DIR` | Enrich input root; blank ⇒ use `APPLICATIONS_INPUT_DIR` | No |
| `ENRICHMENT_OUTPUT_SHEET_ID` | Contacts spreadsheet id | `enrich` only |

**Profile registry**

| Variable | Purpose | Required |
|---|---|---|
| `JOBJOB_PROFILE_<NAME>` | Path to a profile directory | Yes |
| `JOBJOB_ACTIVE_PROFILE` | Name of the active profile | Yes |

### Resolution precedence & deprecated keys

Highest first: **CLI flag → environment variable → config file → built-in default**. An
environment variable overrides the config file, even across the rename below; within one
source, the new name wins over its deprecated alias.

Pre-2.4 names are still read and auto-rewritten in `config/.env` on launch — no action
needed:

| Deprecated | New name |
|---|---|
| `DATA_DIR` | `APPLICATIONS_INPUT_DIR` |
| `APPLICATIONS_LOCAL_DIR` | `APPLICATIONS_OUTPUT_DIR` |
| `APPLICATIONS_FOLDER_ID` | `APPLICATIONS_OUTPUT_DRIVE_ID` |
| `LINKEDIN_SHEET_ID` | `ENRICHMENT_OUTPUT_SHEET_ID` |

## Profile config (`<profile>/config/.profile`)

| Variable | Purpose | Required |
|---|---|---|
| `APPLICANT_NAME` / `_PHONE` / `_EMAIL` / `_LINKEDIN` | Cover-letter header details | No |
| `RESUME_TEMPLATE_ID` | Resume-template Google Doc id for this profile | Drive only |
| `INDUSTRY` | Optional domain (e.g. "science journalism") used to describe the target company accurately | No |

## Place the Google credentials file

If you set up the [Google project](install-google-project.md), put the downloaded JSON
where jobjob expects it (or point `GOOGLE_CREDENTIALS_FILE` at its full path):

- **macOS/Linux:**
  ```sh
  mkdir -p ~/.config/jobjob
  cp ~/Downloads/client_secret_*.json ~/.config/jobjob/credentials.json
  ```
- **Windows (PowerShell):**
  ```powershell
  mkdir $env:USERPROFILE\.config\jobjob -Force
  copy $env:USERPROFILE\Downloads\client_secret_*.json $env:USERPROFILE\.config\jobjob\credentials.json
  ```

The first Drive/Docs run opens a browser to authorize and writes the token to
`GOOGLE_TOKEN_FILE`. If you ever need to re-authorize, delete that token file
(`rm ~/.config/jobjob/token.pickle`, or `del %USERPROFILE%\.config\jobjob\token.pickle`).

## Show it's working

Run `jobjob-app` (or a CLI command) — a misplaced key or cross-tier key trips a clear
validation error at startup. With Google configured, the first non-`--skip-drive` run
completes the browser auth and writes the token file.

## See also

→ [Setup with the wizard](setup-wizard.md) · [Profiles](profiles.md) ·
[Developer reference](setup.md)
