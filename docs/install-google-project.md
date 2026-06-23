# Set up the Google project (for Drive/Docs)

**Optional** — only needed if you want jobjob to save finished applications to **Google
Drive/Docs** (and, for `enrich`, a Google **Sheet**). Skip this for local-only output.

**Why a project?** Google only lets an app touch *your* Drive after you create a small
**Google Cloud project**, turn on the APIs jobjob uses, and download a **credentials
file**. That file lets jobjob ask *your* permission at run time — it does not give anyone
else access. **Cost:** free. All steps are in the browser, so they're the same on every
operating system.

> This is step 2 of [Installation](quickstart.md#installation). It produces a
> `credentials.json` file; you'll hand that to jobjob during
> [setup](setup-wizard.md).

## 1. Create a project

1. Go to <https://console.cloud.google.com/> and sign in with the Google account you want
   output saved to. Accept the terms if prompted.
2. Click the project drop-down (top bar) → **New Project**.
3. Name it e.g. `jobjob-personal`, leave organization blank, click **Create**, and make
   sure it's selected in the top drop-down afterward.

## 2. Enable the APIs

In the left sidebar: **APIs & Services → Library**. Search for, open, and **Enable** each:

- **Google Drive API**
- **Google Docs API**
- **Google Sheets API** — only if you'll use [enrichment](usage-enrichment.md).

## 3. Configure the consent screen

**APIs & Services → OAuth consent screen**:

1. Choose **External**, click **Create**.
2. Fill in **App name** (`jobjob`), **User support email**, and **Developer contact
   email** (all your own email). Click **Save and Continue** through the Scopes and Test
   Users screens — you don't need to add scopes; jobjob requests them at run time.
3. On **Summary**, click **Back to Dashboard**.

## 4. Create the credentials file

**APIs & Services → Credentials**:

1. **+ Create Credentials → OAuth client ID**.
2. **Application type: Desktop app** (this matters — see troubleshooting), name it
   `jobjob-desktop`, click **Create**.
3. In the dialog, click **Download JSON** and save the file (named something like
   `client_secret_….json`).

**Show it's working:** you now have a `credentials.json`-style file. The real test comes
during setup, when you upload it and click **Connect Google** — Google will show a
*"hasn't verified this app"* notice, which is **normal** for personal projects (click
**Advanced → Continue**).

## Next

→ Give the file to jobjob: [Set up with the wizard](setup-wizard.md) (upload it), or
[Local configuration](setup-local-config.md) (place it by hand).

## Troubleshooting

- **`redirect_uri_mismatch`:** you likely chose *Web application* instead of **Desktop
  app**. Delete that credential and redo step 4.
- **"This app isn't verified":** expected for personal use — **Advanced → Go to jobjob
  (unsafe) → Continue**. No Google review is needed for your own account.
- **"API has not been used / disabled":** re-check step 2 — the Drive, Docs (and Sheets,
  if used) APIs must be enabled **on the same project** whose credentials you downloaded.
