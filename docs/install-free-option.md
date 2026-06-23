# Free option (experimental)

> ⚠️ **Experimental and unsupported.** This routes jobjob's AI calls to a **free Google
> AI Studio** key through a community proxy instead of a paid Anthropic key. It is not
> tested as part of jobjob and has a real limitation (see the caveat below). If you just
> want the simplest reliable path, use a paid Anthropic key — it's only about
> **$0.20–0.50 per application** (see [Create your accounts](install-accounts.md)).

**Why this works:** jobjob talks to Claude through the official `anthropic` library,
which honors an `ANTHROPIC_BASE_URL` setting. Point that at a local **proxy** that speaks
Claude's API format but forwards to Google's free Gemini models, and jobjob will use the
free key. No change to jobjob itself is required.

**Cost:** free, within Google AI Studio's free-tier limits.

> ⚠️ **Key caveat — PDF job descriptions won't work.** jobjob normally reads a job
> posting from a **PDF** using Claude's document support. The Gemini proxy does not
> forward PDFs, so through this setup you must add job postings with **Paste text** or a
> **URL** instead of a PDF. Quality and behavior will differ from real Claude.

## 1. Get a free Google AI Studio key

1. Go to <https://aistudio.google.com/> and sign in with any Google account.
2. Click **Get API key** → **Create API key**, and copy the key string.

## 2. Install Node.js and a proxy

The proxy needs **Node.js** (<https://nodejs.org/> — install the LTS build for your OS).
Then, in a terminal (macOS/Linux) or **PowerShell** (Windows):

```
npm install -g @musistudio/claude-code-router
```

(On macOS/Linux, prefix with `sudo` if you hit a permission error.) Configure the router
to use your Google AI Studio key and a Gemini model per its README.

## 3. Point jobjob at the proxy

Add these to your `config/.env` (see [Local configuration](setup-local-config.md) for
where that file lives). The key can be any placeholder — the proxy uses your Google key,
not this one:

```
ANTHROPIC_API_KEY="local-proxy"
ANTHROPIC_BASE_URL="http://localhost:3000"
```

> `ANTHROPIC_BASE_URL` is read directly by the underlying library; jobjob does not need
> to know about it. Match the host/port your proxy prints when it starts.

## 4. Run

1. Start the proxy (e.g. `claude-code-router`) and leave it running.
2. In another terminal, start jobjob: `jobjob-app`.

**Show it's working:** open the app, add a job posting with **Paste text** (not a PDF —
see the caveat), and run it. If it completes, the proxy is wired up. If you see
connection errors, confirm the proxy is running and `ANTHROPIC_BASE_URL` matches its
address.

## Next

→ [Install the software](install-software.md) · [Set up with the wizard](setup-wizard.md)
