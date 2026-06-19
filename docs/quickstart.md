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

Open a terminal (macOS: **Cmd+Space** → "Terminal"; Windows: Start → "Command Prompt").

**Easiest — with `uv`** (it installs Python for you if needed):

```
uv tool install jobjob
```

To install `uv` first, see <https://docs.astral.sh/uv/getting-started/installation/>.

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

The app ships with example content to start from — replace it with your own. (These files
live in `~/Documents/jobjob/profile/` if you prefer to edit them directly.)

---

## Step 5 — Run your first application

1. Put a job-description PDF in **`~/Documents/jobjob/data/jobs/`** (or use the app's
   upload, if available).
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
  config/.env        ← your settings (managed by the wizard/Settings)
  data/jobs/         ← drop job-description PDFs here
  data/completed/    ← finished applications
  profile/           ← your content + reference documents
```

---

## Updating

```
uv tool upgrade jobjob      # or: pipx upgrade jobjob
```

Your jobjob folder (settings, content, applications) is untouched by updates.

---

## Power users / developers

Prefer the command line, or want to contribute? jobjob also has a CLI (`jobjob apply`,
`jobjob enrich`) and a from-source workflow — see [docs/setup.md](setup.md) and
[docs/usage.md](usage.md).
