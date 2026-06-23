# Setup with the wizard

Once the [software is installed](install-software.md), the easiest way to configure
jobjob is the in-app **Setup wizard** — no files to edit. Prefer to edit config files by
hand? See [Local configuration (advanced)](setup-local-config.md) instead; the two are
interchangeable.

## Launch jobjob

In a terminal (macOS/Linux) or PowerShell (Windows):

```
jobjob-app
```

The first run creates your **jobjob folder** at `~/Documents/jobjob` (settings, content,
finished applications) and opens the dashboard in your browser. Leave the terminal open
while you use jobjob; **Ctrl+C** stops it.

> Want the folder elsewhere? `jobjob-app --dir "/path/you/prefer"`.

## The wizard steps

A **Setup** window opens automatically on first run (reopen it anytime from the
**account menu → Run setup**):

1. **Anthropic API key** — paste the key from
   [Create your accounts](install-accounts.md). Stored only on your computer.
   *Working when:* it shows "✓ A key is configured."
2. **Google (optional)** — **upload** the `credentials.json` from
   [the Google project step](install-google-project.md), then click **Connect Google**
   and approve in the tab that opens (the "hasn't verified this app" notice is normal).
   Skip for local-only output. *Working when:* it shows "✓ Google is connected."
3. **Profile** — optionally register an existing profile folder, or bootstrap one by
   importing a résumé. Skippable. See [Profiles](profiles.md).
4. **Your details** — name, email, phone, LinkedIn (these appear on your cover-letter
   header).

You can change anything later under **Settings**.

## Next

→ [Run an application](usage-applications.md) · [Enrich contacts](usage-enrichment.md)
· [Local configuration (advanced)](setup-local-config.md)
