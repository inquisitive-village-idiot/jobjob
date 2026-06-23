# Install the jobjob software

**Why:** jobjob is a small Python program that runs on your own computer (as a local
website you open in your browser). Installing it puts the `jobjob-app` command on your
system. **Cost:** free.

> This is step 3 of [Installation](quickstart.md#installation). You can install the
> software before or after [creating your accounts](install-accounts.md) — but you'll
> need an API key (or the [free option](install-free-option.md)) before jobjob can do
> anything.

You do **not** need Git, Node, or a code checkout — everything is bundled.

## 1. Open a terminal

- **macOS:** press **Cmd+Space**, type "Terminal", press Enter.
- **Windows:** Start menu → type "PowerShell" → open **Windows PowerShell**.
- **Linux:** open your distribution's **Terminal** app.

## 2. Install with `uv` (recommended)

`uv` installs the right Python for you and keeps jobjob isolated from other software.

```
uv tool install jobjob
```

> **Don't have `uv` yet?** `uv` is a small, free tool you install by **pasting one
> command into the terminal** (the window you just opened) and pressing **Enter** —
> there's nothing to download from a website.
>
> - **macOS / Linux:**
>   ```
>   curl -LsSf https://astral.sh/uv/install.sh | sh
>   ```
> - **Windows** (PowerShell):
>   ```
>   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
>   ```
>
> When it finishes, **close the terminal and open a new one** so it knows about `uv`,
> then run `uv tool install jobjob`. (Full / other-system instructions:
> <https://docs.astral.sh/uv/getting-started/installation/>.)

### Alternatives

If you already have Python 3.12+:

```
pipx install jobjob          # isolated install (like uv tool)
# — or —
pip install jobjob           # into a virtual environment you manage
```

## 3. Check it worked

Run:

```
jobjob-app --help
```

You should see usage text (options like `--dir`, `--port`). If instead you see
"command not found", open a **new** terminal window (so it picks up the freshly
installed command) and try again.

## Next

→ [Set up jobjob with the wizard](setup-wizard.md)

---

**Updating later:** `uv tool upgrade jobjob` (or `pipx upgrade jobjob`), or from the
app's **Settings → Update**. Your jobjob folder (settings, content, applications) is
untouched by updates.
