Google Drive/Docs setup
=======================

**Optional.** Only needed if you want jobjob to save finished applications to **Google
Drive/Docs** (and, for :doc:`enrichment <usage-enrichment>`, a Google **Sheet**). Skip
this for local-only output.

**Why a project?** Google only lets an app touch *your* Drive after you create a small
**Google Cloud project**, enable the APIs jobjob uses, and download a **credentials
file**. That file lets jobjob ask *your* permission at run time — it gives no one else
access. It's free, and every step is in the browser, so it's the same on every operating
system.

This produces a ``credentials.json`` file you hand to jobjob during
:doc:`configuration`.

1. Create a project
-------------------

#. Go to https://console.cloud.google.com/ and sign in with the Google account you want
   output saved to. Accept the terms if prompted.
#. Click the project drop-down (top bar) → **New Project**.
#. Name it (e.g. ``jobjob-personal``), leave organization blank, click **Create**, then
   make sure it's selected in the top drop-down.

2. Enable the APIs
------------------

In the left sidebar: **APIs & Services → Library**. Search for, open, and **Enable** each:

- **Google Drive API**
- **Google Docs API**
- **Google Sheets API** — only if you'll use :doc:`enrichment <usage-enrichment>`.

3. Configure the consent screen
-------------------------------

**APIs & Services → OAuth consent screen**:

#. Choose **External**, click **Create**.
#. Fill in **App name** (``jobjob``), **User support email**, and **Developer contact
   email** (all your own email). Click **Save and Continue** through the Scopes and Test
   Users screens — you don't need to add scopes; jobjob requests them at run time.
#. On **Summary**, click **Back to Dashboard**.

4. Create the credentials file
------------------------------

**APIs & Services → Credentials**:

#. **+ Create Credentials → OAuth client ID**.
#. **Application type: Desktop app** (this matters — see Troubleshooting), name it
   ``jobjob-desktop``, click **Create**.
#. In the dialog, click **Download JSON** and save the file (named something like
   ``client_secret_….json``).

You now have a credentials file. The real test comes during :doc:`configuration`, when
you upload it and click **Connect Google** — Google shows a *"hasn't verified this app"*
notice, which is **normal** for personal projects (click **Advanced → Continue**).

Next
----

→ Hand the file to jobjob during :doc:`configuration` (upload it in the wizard, or place
it by hand).

Troubleshooting
---------------

- **redirect_uri_mismatch** — you likely chose *Web application* instead of **Desktop
  app**. Delete that credential and redo step 4.
- **"This app isn't verified"** — expected for personal use: **Advanced → Go to jobjob
  (unsafe) → Continue**. No Google review is needed for your own account.
- **"API has not been used / disabled"** — re-check step 2; the Drive, Docs (and Sheets,
  if used) APIs must be enabled **on the same project** whose credentials you downloaded.
