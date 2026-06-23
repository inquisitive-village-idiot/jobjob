# Create your accounts

jobjob needs one account to work, and an optional second one for Google Drive/Docs.
Account creation is done in your **web browser**, so the steps are the same on Windows,
macOS, and Linux.

> This is step 1 of [Installation](quickstart.md#installation).

## Anthropic account + API key (required)

**Why:** jobjob writes your résumé and cover letters by calling **Claude**, Anthropic's
AI. An API key authorizes those calls.

**Cost:** pay-as-you-go, billed by Anthropic to a card on your account — **about
$0.20–0.50 per application**. A payment method is required; **there is no free Anthropic
tier**, and the free Claude.ai chat plan does **not** include API access. (Want to avoid
a paid key? See the [experimental free option](install-free-option.md).)

**Steps:**

1. Go to <https://console.anthropic.com/> and **sign up** (verify your email).
2. Open **Billing** and **add a payment method** (a small prepaid balance is fine).
3. Open **API Keys** → **Create Key**, name it `jobjob`, and **copy the key now** — it
   looks like `sk-ant-api03-…` and is shown only once. Paste it somewhere safe (a
   password manager is ideal).

**Show it's working:** you'll enter this key during [setup](setup-wizard.md); the wizard
reports "✓ A key is configured." If a run later fails with an authentication or credit
error, re-check the key and your Anthropic billing balance.

## Google account (optional)

**Why:** only if you want jobjob to save finished résumés and cover letters to **Google
Drive/Docs** as editable documents. Skip it for local-only output (everything still works
and is saved on your computer).

**Cost:** free — a normal Google account.

If you want Drive/Docs output, you next create a small **Google Cloud project** to get a
credentials file. That's its own page:

→ [Set up the Google project (for Drive/Docs)](install-google-project.md)

## Next

→ [Set up the Google project](install-google-project.md) (optional) ·
[Install the software](install-software.md)
