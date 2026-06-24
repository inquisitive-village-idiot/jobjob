Free option (experimental)
==========================

.. warning::

   **Experimental.** This routes jobjob's AI calls to a **free Google AI Studio** key
   through a community proxy instead of a paid Anthropic key. It has a real limitation
   (see the caveat). For the simplest reliable path, use a paid Anthropic key — about
   **$0.20–0.50 per application** (see :doc:`credentials`).

**How it works:** jobjob talks to Claude through the official ``anthropic`` library,
which supports a configurable base URL. jobjob reads ``ANTHROPIC_BASE_URL`` from your app
config and points the client at it. Aim that at a local **proxy** that speaks Claude's
API format but forwards to Google's free Gemini models, and jobjob runs on the free key.

**Cost:** free, within Google AI Studio's free-tier limits.

.. warning::

   **PDF job descriptions won't work.** jobjob normally reads a posting from a **PDF**
   using Claude's document support. The Gemini proxy does not forward PDFs, so with this
   setup add job postings with **Paste text** or a **URL** instead of a PDF. Quality and
   behavior differ from real Claude.

1. Get a free Google AI Studio key
----------------------------------

#. Go to https://aistudio.google.com/ and sign in with any Google account.
#. Click **Get API key → Create API key**, and copy the key string.

2. Install Node.js and a proxy
------------------------------

The proxy needs **Node.js** (https://nodejs.org/ — install the LTS build for your OS).
Then, in a terminal (macOS/Linux) or PowerShell (Windows)::

   npm install -g @musistudio/claude-code-router

(On macOS/Linux, prefix with ``sudo`` if you hit a permission error.) Configure the
router to use your Google AI Studio key and a Gemini model per its README.

3. Point jobjob at the proxy
----------------------------

Add these to your ``config/.env`` (see :doc:`configuration` for where that file lives and
how to edit it). The key can be any placeholder — the proxy uses your Google key, not
this one::

   ANTHROPIC_API_KEY="local-proxy"
   ANTHROPIC_BASE_URL="http://localhost:3000"

Match the host/port your proxy prints when it starts.

4. Run
------

#. Start the proxy (e.g. ``claude-code-router``) and leave it running.
#. In another terminal, start jobjob: ``jobjob-app``.

**Confirm it works:** open the app, add a job posting with **Paste text** (not a PDF —
see the caveat), and run it. If it completes, the proxy is wired up. If you see
connection errors, confirm the proxy is running and ``ANTHROPIC_BASE_URL`` matches its
address.

See also
--------

→ :doc:`credentials` · :doc:`configuration`
