# Quick-Start Guide

This guide gets **jobjob** running on your computer. It is written for someone
comfortable using a computer but new to programming tools — every step is spelled out.

**Time:** about 30–60 minutes the first time (mostly the one-time Anthropic + Google
setup). After that, each application takes a couple of minutes.

---

## What this tool does

You give jobjob a job-description PDF. It reads the posting, picks the most relevant
parts of your background, and writes a tailored cover letter and resume summary —
saving them on your computer and (optionally) to Google Drive as editable Docs.

It runs entirely on your machine as a small local website you open in your browser.
Under the hood it calls the Claude AI (by Anthropic); you pay Anthropic a few cents per
application — there is no jobjob subscription.

---

## What you will need

| What | Why |
|------|-----|
| macOS or Windows 10/11 | Runs the tool |
| Python 3.12+ **or** `uv` | jobjob is a Python program (`uv` installs Python for you) |
| An Anthropic API key | Powers the AI (the wizard links you to it) |
| A Google account (optional) | Save outputs to Google Drive/Docs |
| A job-description PDF | The posting you are applying to |

You do **not** need Git, Node, or a code checkout — everything is bundled.

---

## Step 1 — Install jobjob

Open a terminal (macOS: **Cmd+Space** → "Terminal"; Windows: Start → "PowerShell").

**Easiest — with `uv`** (it installs Python for you if needed):

```
uv tool install jobjob
```

> **Don't have `uv` yet?** `uv` is a small, free tool that installs and runs Python
> programs. You install it by **pasting one command into the terminal** (the same window
> you just opened) and pressing **Enter** — there's nothing to download from a website.
> Copy the line for your system:
>
> - **macOS:**
>   ```
>   curl -LsSf https://astral.sh/uv/install.sh | sh
>   ```
> - **Windows** (use **PowerShell**: Start → "PowerShell"):
>   ```
>   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
>   ```
>
> When it finishes, **close the terminal window and open a new one** so it knows about
> `uv`, then run the `uv tool install jobjob` command above. (Full instructions and other
> systems: <https://docs.astral.sh/uv/getting-started/installation/>.)

**Or — with `pipx`** (if you already have Python 3.12+):

```
pipx install jobjob
```

Both install jobjob in its own isolated environment, so it never interferes with other
software. (Plain `pip install jobjob` into a virtual environment also works.)

---

## Step 2 — Launch it

```
jobjob-app
```

The first time, this creates a folder at **`~/Documents/jobjob`** (your "jobjob folder")
to hold your settings, content, and finished applications — then opens the dashboard in
your browser. Leave the terminal window open while you use jobjob; closing it stops the
app. To stop it, press **Ctrl+C** in the terminal.

> Want the folder elsewhere? `jobjob-app --dir "/path/you/prefer"`.

---

## Step 3 — Finish setup in the browser

The first time, a **Setup** window opens automatically and walks you through:

1. **Anthropic API key** — paste your key (the window links to where to get one). It is
   stored only on your computer.
2. **Google (optional)** — upload the `credentials.json` you get from Google, then click
   **Connect Google** and approve in the tab that opens. Skip this for local-only output.
   See the [Credentials Setup guide](credentials-setup.md) for getting `credentials.json`.
3. **Your details** — name, email, phone, LinkedIn. These appear on your cover-letter
   header.

You can reopen this anytime from the **account menu (top-right) → Run setup**, and change
anything later under **Settings**.

---

## Step 4 — Add your background

jobjob tailors output from documents that describe *you*. Open the **Static Content** tab
in the app to edit them in the browser:

| Content | What it holds |
|---------|---------------|
| Highlights | Your key achievements / credential blocks |
| Skills | Your skills with keywords |
| Background | Career narrative, relocation preferences |
| Writing style | Voice and tone guidance |
| Cover letters | Example letters (style reference) |
| STARs | STAR-format stories of your experience |

Your profile starts **empty** so none of the bundled example persona's content sneaks
into your applications. Two shortcuts to fill it faster:

- **Import a résumé** — on the Static Content tab, import an existing résumé to
  pre-fill highlights, skills, and background, then review before saving.
- **Borrow from the example** — the app includes a read-only **example** profile (the
  fictional *Tila Mer*). Switch to it from **account menu → Profiles** to see how a
  complete profile looks, or **Duplicate** it and edit your copy.

(Your content lives in `~/Documents/jobjob/profiles/local/` if you prefer to edit the
files directly. See the [Profiles guide](profiles.md).)

---

## Step 5 — Run your first application

1. **Add a job posting.** In the app, use **Add JD** to paste the posting text, fetch it
   from a URL, or upload a PDF. (You can also drop a PDF straight into
   **`~/Documents/jobjob/data/jobs/`**.)
2. In the **Queue** tab, find the posting and click **Apply**.
3. Watch the progress; when it finishes it appears on the **Dashboard**.

Your tailored cover letter, resume, skills analysis, and a per-application README are
saved under **`~/Documents/jobjob/data/completed/`** — and, if you connected Google, as
editable Google Docs in your Drive.

> The cover letter starts with a **⚠️ GAPS / FLAGS – DELETE BEFORE SENDING** section
> listing anything the AI could not match to your documented background. Review and
> delete that section before sending. The AI flags gaps rather than inventing
> qualifications.

---

## Where your files live

Everything is under your jobjob folder (default `~/Documents/jobjob`):

```
~/Documents/jobjob/
  config/.env          ← your settings (managed by the wizard/Settings)
  data/jobs/           ← drop job-description PDFs here
  data/completed/      ← finished applications
  profiles/local/      ← your content + reference documents
  profiles/<name>/     ← any additional profiles you create
```

---

## Updating

The app checks for updates on launch and shows them under **Settings** — click
**Update** there to upgrade in place. Or from the terminal:

```
uv tool upgrade jobjob      # or: pipx upgrade jobjob
```

Your jobjob folder (settings, content, applications) is untouched by updates.

> The in-app update check and **Update** button are available in **2.0.0 and later**.
> On 1.x, upgrade once from the terminal; after that you can update from Settings.

### Upgrading from 1.x

Upgrade the normal way (above). The first launch on 2.0.0+ automatically moves your old
`profile/` folder to `profiles/local/` — nothing to do, and nothing is lost. See the
[Profiles guide](profiles.md) for the profile model.

---

## Power users / developers

Prefer the command line, or want to contribute? jobjob also has a CLI (`jobjob apply`,
`jobjob enrich`) and a from-source workflow — see [docs/setup.md](setup.md) and
[docs/usage.md](usage.md).
