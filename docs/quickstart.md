# Getting started

**jobjob** runs entirely on your machine as a small local website you open in your
browser. It does two things:

1. **Application Builder** — give it a job posting (PDF, URL, or pasted text). It reads
   the posting, picks the most relevant parts of your background, and writes a tailored
   cover letter and résumé summary — saved on your computer and, optionally, to Google
   Drive as editable Docs.
2. **Contact Enrichment** — give it a PDF or screenshot of a LinkedIn profile. It parses
   out the details and writes them to a Google spreadsheet.

These steps work on **Windows, macOS, and Linux**. Plan on 30–60 minutes the first time
(mostly the one-time account setup); after that, each application takes a couple of
minutes.

Follow the steps below in order. Optional and advanced topics are linked at the end.

---

## Step 1 — Get an Anthropic API key

jobjob uses **Claude** (Anthropic's AI) to parse the job description, write the cover
letter, and more. It calls Claude through Anthropic's **API**, which is **pay-as-you-go —
about $0.20–0.50 per application**, billed to a card on your Anthropic account.

> **NOTE — a paid key is required.** There is no free Anthropic tier, and the free
> Claude.ai *chat* plan does **not** include API access. You *may* be able to run jobjob
> for free using Google AI Studio instead — see the [free option](install-free-option.md)
> — but that path is experimental and untested.
>
> **NOTE — Claude only.** jobjob currently supports the Anthropic API only; other
> providers could be added later.

1. Go to <https://console.anthropic.com/> and **sign up** (verify your email).
2. **Add a payment method.** Open **Settings → Billing**
   (<https://console.anthropic.com/settings/billing>) and add a card or a small prepaid
   balance.
3. **Create the key.** Open **Settings → API keys**
   (<https://console.anthropic.com/settings/keys>), click **Create Key**, name it
   `jobjob`, and **copy the key now** — it starts with `sk-ant-` and is shown only once.
   Keep it somewhere safe (a password manager is ideal).

You'll paste this key into jobjob in Step 3.

---

## Step 2 — Install jobjob

jobjob is a small Python program. The easiest installer is **`uv`** (it brings its own
Python). You don't need Git, Node, or a code checkout.

**Open a terminal:** macOS — Cmd+Space → "Terminal"; Windows — Start → "PowerShell";
Linux — your Terminal app. Then:

```
uv tool install jobjob
```

> **Don't have `uv`?** Install it by **pasting one command into the terminal** (nothing to
> download from a website):
>
> - **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
> - **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
>
> Then **close the terminal, open a new one**, and run `uv tool install jobjob`. Already
> have Python 3.12+? `pipx install jobjob` or `pip install jobjob` work too.

**Check it worked:** run `jobjob-app --help` — you should see usage text. ("Command not
found"? Open a fresh terminal so it picks up the new command.)

---

## Step 3 — Launch and finish setup

```
jobjob-app
```

The first run creates your **jobjob folder** at `~/Documents/jobjob` (settings, content,
finished applications) and opens the dashboard in your browser. Leave the terminal open
while you use jobjob; **Ctrl+C** stops it.

A **Setup** window opens automatically and walks you through:

1. **Anthropic API key** — paste the key from Step 1 ("✓ A key is configured").
2. **Google (optional)** — connect Google Drive/Docs for editable-document output. This
   needs a one-time Google project setup → [Set up Google Drive/Docs](install-google-project.md).
   Skip it for local-only output.
3. **Your details** — name, email, phone, LinkedIn (used on your cover-letter header).

Prefer to configure by editing files instead of the wizard? See
[Setup & configuration](setup.md).

---

## Step 4 — Run your first application

Add some background about yourself (the **Static Content** tab, or import a résumé),
then generate an application — full walkthrough here:

→ **[Applications](usage-applications.md)** · also: [Enrichment](usage-enrichment.md)
(import LinkedIn contacts into a Google Sheet)

> The cover letter starts with a **⚠️ GAPS / FLAGS – DELETE BEFORE SENDING** section
> listing anything the AI couldn't match to your documented background — review and delete
> it before sending. jobjob flags gaps rather than inventing qualifications.

---

## Where your files live

```
~/Documents/jobjob/
  config/.env          your settings (wizard/Settings, or edit by hand)
  data/jobs/           job-description PDFs
  data/completed/      finished applications
  profiles/local/      your content + reference documents
```

**More:** [Setup & configuration](setup.md) · [Profiles](profiles.md) ·
[Architecture](architecture.md) · contributing/from-source? [Developer reference](developer.md).
