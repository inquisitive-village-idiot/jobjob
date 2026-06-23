# Credentials Setup

This guide covers the two sets of credentials jobjob needs: an **Anthropic API key**
(required for AI calls) and **Google OAuth credentials** (optional, only needed if you
want to save output to Google Drive/Docs).

Both are one-time setups. Once done you will not need to repeat them unless you revoke
access or switch computers.

> **Using the app (most people)?** The in-app **Setup wizard** is the easiest way to
> enter these — it opens automatically on first launch (see [Quick-Start](quickstart.md),
> Step 3). You paste the Anthropic key and **upload** the Google `credentials.json` right
> in your browser; no file editing or terminal commands needed. You still follow the
> account-creation and Google Cloud steps below to *obtain* the key and `credentials.json`
> — but the steps that edit `config/.env` or copy files by hand are the **manual /
> command-line alternative**, marked below, and you can skip them.

---

## Part 1 — Anthropic API key

The Anthropic API key is what authorizes jobjob to call Claude. You are billed per
use by Anthropic, directly to a credit card you add to your account.

### 1.1 Create an Anthropic account

1. Go to **https://console.anthropic.com/** in your browser.
2. Click **"Sign up"** and create an account with your email address.
3. Verify your email when prompted.

### 1.2 Add a payment method

Before you can make API calls, Anthropic requires a payment method on file.

1. Once signed in, click your account or the **"Billing"** section in the left sidebar.
2. Click **"Add payment method"** and enter a credit or debit card.
3. A typical jobjob run costs under $0.50, so your charges will be small.

> **TODO (maintainer):** Add a screenshot of the Anthropic console Billing page.

### 1.3 Create an API key

1. In the Anthropic console, look for **"API Keys"** in the left sidebar (it may be
   under **"Settings"**).
2. Click **"Create Key"** (or **"+ New Key"**).
3. Give it a name like `jobjob` so you remember what it is for.
4. Click **"Create"**. Your key appears on screen — it looks like:
   `sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
5. **Copy the key immediately.** The console will not show it again after you navigate
   away. Paste it somewhere safe (a password manager is ideal).

> **TODO (maintainer):** Add a screenshot of the API Keys page showing the Create
> button and the key reveal dialog.

### 1.4 Add the key to jobjob

> **Wizard users: skip this step.** Paste the key into the Setup wizard's **Anthropic
> API key** field instead (Quick-Start Step 3). The step below is the manual alternative
> for command-line users.

Open `config/.env` in a text editor and paste your key:

```
ANTHROPIC_API_KEY="sk-ant-api03-XXXXXXXXXXXXXXXXXXXX"
```

Make sure there are no spaces before or after the key, and the quotes are there.

---

## Part 2 — Google OAuth credentials (optional)

Skip this part if you do not need Google Drive/Docs integration. jobjob works fully
without it using `--skip-drive`.

This setup involves three things:

1. Creating a **Google Cloud project** (a container for your app's credentials)
2. Enabling the **Drive and Docs APIs**
3. Downloading a **credentials file** that jobjob uses to ask for your permission

> **Wizard users:** §2.1–2.5 below are required no matter how you run jobjob — they
> produce the `credentials.json` file. Once you have that file, you're done with the
> manual steps: in the Setup wizard, **upload `credentials.json`** and click **Connect
> Google** (Quick-Start Step 3). That replaces §2.6–2.8 (copying the file and editing
> `config/.env`), which remain here for command-line users.

### 2.1 Go to the Google Cloud Console

1. In your browser, go to **https://console.cloud.google.com/**.
2. Sign in with the Google account you want to use for Drive output.
3. If prompted to select a country and agree to terms, do so.

### 2.2 Create a project

1. At the top of the page, click the project selector drop-down (it may say
   **"Select a project"** or show the name of an existing project).
2. Click **"New Project"**.
3. Name it something like `jobjob-personal`. The organization field can be left blank.
4. Click **"Create"**. Wait a few seconds for the project to be ready.
5. Make sure the new project is now selected in the top drop-down.

> **TODO (maintainer):** Add a screenshot of the project selector and New Project dialog.

### 2.3 Enable the APIs

jobjob needs two Google APIs: **Google Drive API** and **Google Docs API**.

For each API:

1. In the left sidebar, click **"APIs & Services"** → **"Library"**.
2. Search for the API name.
3. Click on it in the results.
4. Click **"Enable"**.

Repeat for both:
- `Google Drive API`
- `Google Docs API`

If you plan to use the `jobjob enrich` command (which writes to Google Sheets), also
enable:
- `Google Sheets API`

### 2.4 Set up the OAuth consent screen

Before you can download credentials, Google requires a basic description of your app.

1. In the left sidebar, click **"APIs & Services"** → **"OAuth consent screen"**.
2. Choose **"External"** and click **"Create"**.
3. Fill in:
   - **App name:** `jobjob` (or anything you like)
   - **User support email:** your email address
   - **Developer contact email:** your email address
4. Leave everything else at defaults and click **"Save and Continue"** through the
   Scopes and Test Users screens. You do not need to add any scopes here — jobjob
   requests them automatically at runtime.
5. On the **Summary** screen, click **"Back to Dashboard"**.

> **TODO (maintainer):** Add a screenshot of the OAuth consent screen form.

### 2.5 Create OAuth credentials

1. In the left sidebar, click **"APIs & Services"** → **"Credentials"**.
2. Click **"+ Create Credentials"** at the top, then **"OAuth client ID"**.
3. For **Application type**, choose **"Desktop app"**.
4. Name it `jobjob-desktop` (or anything).
5. Click **"Create"**.
6. A dialog appears with your client ID and secret. Click **"Download JSON"**.
7. Save the file. By default it is named something like
   `client_secret_XXXXXXXX.apps.googleusercontent.com.json`.

> **TODO (maintainer):** Add a screenshot of the Create OAuth Client ID dialog and
> the Download JSON button.

### 2.6 Put the credentials file where jobjob can find it

The default location jobjob looks for the file is:
`~/.config/jobjob/credentials.json`

(`~` is shorthand for your home folder — `/Users/YourName` on macOS or
`C:\Users\YourName` on Windows.)

**macOS:** Create the directory and copy the file:

```
mkdir -p ~/.config/jobjob
cp ~/Downloads/client_secret_*.json ~/.config/jobjob/credentials.json
```

**Windows:**

```
mkdir %USERPROFILE%\.config\jobjob
copy %USERPROFILE%\Downloads\client_secret_*.json %USERPROFILE%\.config\jobjob\credentials.json
```

Or you can put the file anywhere and set `GOOGLE_CREDENTIALS_FILE` in `config/.env`
to its full path.

### 2.7 Update config/.env

Make sure `config/.env` has:

```
GOOGLE_CREDENTIALS_FILE="~/.config/jobjob/credentials.json"
GOOGLE_TOKEN_FILE="~/.config/jobjob/token.pickle"
```

### 2.8 First-time authorization

> **Wizard users:** click **Connect Google** in the Setup wizard — it opens the same
> browser approval described here. The CLI flow below is the equivalent for command-line
> users.

The next time you run `jobjob apply` **without** `--skip-drive`, a browser window will
open and ask you to:

1. Choose your Google account.
2. See a warning that says **"Google hasn't verified this app"** — this is normal for
   personal projects. Click **"Continue"** (you may need to click **"Advanced"** first).
3. Grant jobjob permission to access your Google Drive and Docs.

After you approve, jobjob saves a token file (`token.pickle`) so it can act on your
behalf without asking again.

### 2.9 Find your Applications Drive folder ID (optional)

If you want jobjob to save output into a specific Google Drive folder:

1. Open Google Drive in your browser and navigate to (or create) the folder you want
   to use — for example, **"Job Applications 2026"**.
2. Click on the folder. Look at the URL in your browser's address bar:
   `https://drive.google.com/drive/folders/1ABC123defGHI456jklMNO789`
   The part after `/folders/` is the folder ID.
3. Paste it in `config/.env`:
   ```
   APPLICATIONS_OUTPUT_DRIVE_ID="1ABC123defGHI456jklMNO789"
   ```
   (In the app you can set this under **Settings → Applications** instead of editing
   the file.)

---

## Troubleshooting credentials

### "Error 400: redirect_uri_mismatch" during Google auth

You may have created a **Web application** credential instead of **Desktop app**. Go
back to Google Cloud Console → Credentials, delete the credential you created, and
redo Step 2.5 making sure to choose **"Desktop app"**.

### "This app isn't verified" warning from Google

This is expected for personal credentials. Click **"Advanced"** then
**"Go to jobjob (unsafe)"**. The warning exists because you have not submitted your app
for Google's review — which is not necessary for personal use.

### "Access denied" when granting permissions

Make sure you are signing in with the same Google account that owns the Cloud project.
If you added yourself as a test user in Step 2.4, confirm the email matches.

### Token expired or revoked

Delete the token file to force a fresh authorization:

**macOS:**
```
rm ~/.config/jobjob/token.pickle
```

**Windows:**
```
del %USERPROFILE%\.config\jobjob\token.pickle
```

Then run jobjob again and go through the browser auth flow.

### "API has not been used in project" or "API disabled"

Return to the Google Cloud Console and confirm you enabled both the Drive API and Docs
API (and Sheets if needed) for your project. They must be enabled on the same project
whose credentials you downloaded.
