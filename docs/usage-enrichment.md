# Enrichment — import contacts into a Google Sheet

Enrichment reads a **LinkedIn profile screenshot** and appends the parsed contact to a
Google **Sheet** — handy for tracking recruiters and hiring managers alongside your
applications.

**Before you start:** [install](quickstart.md) and [set up](setup.md)
jobjob, including Google access with the **Sheets API** enabled (see
[the Google project step](install-google-project.md)). Configuration keys live under
**Enrichment** in [Local configuration](setup.md#app-config-keys-configenv) —
notably `ENRICHMENT_OUTPUT_SHEET_ID` (the target spreadsheet) and, optionally,
`ENRICHMENT_INPUT_DIR` (defaults to the applications input).

## In the app

1. Add a LinkedIn profile screenshot (PDF/image) to the enrichment input — drop it in
   `<jobjob folder>/data/profiles/`.
2. In the **Queue** tab, find it and run **Enrich**.
3. The parsed contact is appended to your contacts Sheet; the item moves to completed.

## On the command line

```
jobjob enrich <profile> [options]
```

| Flag | Description |
|---|---|
| `--sheet-id <id>` | Spreadsheet id (overrides `ENRICHMENT_OUTPUT_SHEET_ID`) |
| `--sheet-name <name>` | Worksheet tab name (default: `Contacts`) |
| `--dry-run` | Parse only; don't write to the Sheet |
| `--no-cache` | Disable the response cache for this run |

**Show it's working:** run with `--dry-run` first to confirm the profile parses, then run
for real and check the new row in your Sheet.

## Finding your Sheet id

Open the Sheet in your browser; the id is the long string in the URL between
`/d/` and `/edit`. Put it in `ENRICHMENT_OUTPUT_SHEET_ID`
([Local configuration](setup.md#app-config-keys-configenv)) or pass `--sheet-id`.

## See also

→ [Configuration](setup.md#app-config-keys-configenv) · [Applications](usage-applications.md)
