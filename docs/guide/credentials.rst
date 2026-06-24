Credentials
===========

jobjob needs one credential to run: an **Anthropic API key**. A **Google** connection is
optional and only needed for Drive/Docs output or :doc:`enrichment <usage-enrichment>`.

You collect the credentials here, then hand them to jobjob during
:doc:`configuration`.

Anthropic API key (required)
----------------------------

jobjob uses **Claude** (Anthropic's AI) to read the job description, write the cover
letter, and more. It calls Claude through Anthropic's **API**, which is pay-as-you-go —
roughly **$0.20–0.50 per application**, billed to a card on your Anthropic account.

.. note::

   **A paid key is required.** There is no free Anthropic tier, and the free Claude.ai
   *chat* plan does **not** include API access. jobjob currently supports the Anthropic
   API only.

#. Sign up at https://console.anthropic.com/ and verify your email.
#. Add a payment method under **Settings → Billing**
   (https://console.anthropic.com/settings/billing) — a card or a small prepaid balance.
#. Create the key under **Settings → API keys**
   (https://console.anthropic.com/settings/keys): click **Create Key**, name it
   ``jobjob``, and **copy it now** — it starts with ``sk-ant-`` and is shown only once.
   Store it somewhere safe (a password manager is ideal).

You'll paste this key into jobjob during :doc:`configuration`.

Google credentials (optional)
-----------------------------

Connect Google only if you want either of these:

- Finished applications saved to **Google Drive/Docs** as editable documents.
- :doc:`Enrichment <usage-enrichment>`, which writes contacts to a Google **Sheet**.

This needs a one-time **Google Cloud project** that produces a ``credentials.json`` file.
Full walkthrough: :doc:`google-project`. You'll upload that file during
:doc:`configuration`.

Next
----

→ :doc:`install`
