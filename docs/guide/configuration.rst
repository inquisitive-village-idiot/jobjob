Configuration
=============

Launch
------

In a terminal, run::

   jobjob-app

The first run creates your **jobjob folder** at ``~/Documents/jobjob`` (settings,
content, and finished applications) and opens the dashboard in your browser. Leave the
terminal open while you use jobjob; press ``Ctrl`` + ``C`` there to stop it.

A **Setup** window opens automatically and walks you through everything you need:

#. **Anthropic API key** — paste the key from :doc:`credentials`.
#. **Google (optional)** — upload ``credentials.json`` and connect (see
   :doc:`google-project`). Skip this for local-only output.
#. **Your details** — name, email, phone, LinkedIn (used on your cover-letter header).

The wizard contains all the guidance you need, so it isn't repeated here. Reopen it
anytime from the **account menu → Run setup**, and change any setting later under
**Settings**.

.. tip::

   Prefer to configure by editing files instead of the wizard? Everything the wizard
   writes is plain text. The rest of this page is that reference — most people can stop
   reading here.

----

Advanced: editing config files
------------------------------

jobjob has **two** config files, validated as *disjoint* — no key may appear in both:

- **App config** — ``<jobjob folder>/config/.env`` (machine-local; default folder
  ``~/Documents/jobjob``). Your API key, Google paths, output locations, and the profile
  registry.
- **Profile config** — ``<profile>/config/.profile``, inside each profile directory (see
  :doc:`profiles`). The active profile's applicant identity and résumé template.

Open the app config in any plain-text editor:

- **macOS** — ``open -e ~/Documents/jobjob/config/.env``
- **Linux** — ``nano ~/Documents/jobjob/config/.env``
- **Windows (PowerShell)** — ``notepad $env:USERPROFILE\Documents\jobjob\config\.env``

Each line is ``KEY="value"`` — keep the quotes and put no spaces around ``=``.

App config keys (``config/.env``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. rubric:: AI (required)

.. list-table::
   :header-rows: 1
   :widths: 34 50 16

   * - Variable
     - Purpose
     - Required
   * - ``ANTHROPIC_API_KEY``
     - Anthropic API key. A secret — never displayed by the wizard or Settings.
     - Yes
   * - ``CLAUDE_MODEL``
     - Model id (default: ``claude-sonnet-4-6``).
     - No
   * - ``CLAUDE_CACHE_ENABLED`` / ``CACHE_DIR``
     - Response-cache toggle / directory.
     - No

.. rubric:: Google (for Drive/Docs output)

.. list-table::
   :header-rows: 1
   :widths: 34 50 16

   * - Variable
     - Purpose
     - Required
   * - ``GOOGLE_CREDENTIALS_FILE``
     - Path to the OAuth client-secrets JSON (default: ``~/.config/jobjob/credentials.json``).
     - Drive/Sheets
   * - ``GOOGLE_TOKEN_FILE``
     - Path to the saved OAuth token (default: ``~/.config/jobjob/token.pickle``).
     - Drive/Sheets

.. rubric:: Applications (``apply``)

.. list-table::
   :header-rows: 1
   :widths: 34 50 16

   * - Variable
     - Purpose
     - Required
   * - ``APPLICATIONS_INPUT_DIR``
     - Input/working root holding ``jobs/``, ``profiles/``, ``completed/`` (default: ``data``).
     - No
   * - ``APPLICATIONS_OUTPUT_DIR``
     - Local mirror of the Drive output folder.
     - No
   * - ``APPLICATIONS_OUTPUT_DRIVE_ID``
     - Google Drive folder id for output.
     - Drive only

.. rubric:: Enrichment (``enrich``)

.. list-table::
   :header-rows: 1
   :widths: 34 50 16

   * - Variable
     - Purpose
     - Required
   * - ``ENRICHMENT_INPUT_DIR``
     - Enrich input root; blank ⇒ use ``APPLICATIONS_INPUT_DIR``.
     - No
   * - ``ENRICHMENT_OUTPUT_SHEET_ID``
     - Contacts spreadsheet id.
     - ``enrich`` only

.. rubric:: Profile registry

.. list-table::
   :header-rows: 1
   :widths: 34 50 16

   * - Variable
     - Purpose
     - Required
   * - ``JOBJOB_PROFILE_<NAME>``
     - Path to a profile directory (one line per profile).
     - Yes
   * - ``JOBJOB_ACTIVE_PROFILE``
     - Name of the active profile.
     - Yes

See :doc:`profiles` for what a profile contains and how the registry works.

Profile config keys (``<profile>/config/.profile``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 50 16

   * - Variable
     - Purpose
     - Required
   * - ``APPLICANT_NAME`` / ``_PHONE`` / ``_EMAIL`` / ``_LINKEDIN``
     - Cover-letter header details.
     - No
   * - ``RESUME_TEMPLATE_ID``
     - Résumé-template Google Doc id for this profile.
     - Drive only
   * - ``INDUSTRY``
     - Optional domain hint (e.g. "science journalism") injected into the résumé-objective prompt.
     - No

This file holds **no local paths and no secrets**.

Precedence and deprecated keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Highest priority first: **CLI flag → environment variable → config file → built-in
default.** An environment variable overrides the config file; within one source, a new
key name wins over its deprecated alias.

Older key names are still read and auto-rewritten in ``config/.env`` on launch — no
action needed:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Deprecated
     - New name
   * - ``DATA_DIR``
     - ``APPLICATIONS_INPUT_DIR``
   * - ``APPLICATIONS_LOCAL_DIR``
     - ``APPLICATIONS_OUTPUT_DIR``
   * - ``APPLICATIONS_FOLDER_ID``
     - ``APPLICATIONS_OUTPUT_DRIVE_ID``
   * - ``LINKEDIN_SHEET_ID``
     - ``ENRICHMENT_OUTPUT_SHEET_ID``

Placing the Google credentials file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The wizard's **upload** button does this for you. To place it by hand instead (or to
point ``GOOGLE_CREDENTIALS_FILE`` at a custom path):

- **macOS / Linux**::

     mkdir -p ~/.config/jobjob
     cp ~/Downloads/client_secret_*.json ~/.config/jobjob/credentials.json

- **Windows (PowerShell)**::

     mkdir $env:USERPROFILE\.config\jobjob -Force
     copy $env:USERPROFILE\Downloads\client_secret_*.json $env:USERPROFILE\.config\jobjob\credentials.json

The first Drive/Docs run opens a browser to authorize and writes the token to
``GOOGLE_TOKEN_FILE``. To re-authorize later, delete that token file (for example
``rm ~/.config/jobjob/token.pickle``).

Where your files live
---------------------

::

   ~/Documents/jobjob/
     config/.env          your settings (wizard/Settings, or edit by hand)
     data/jobs/           job-description PDFs you add
     data/profiles/       LinkedIn screenshots for enrichment
     data/completed/      finished applications
     profiles/local/      your content + reference documents

Next
----

→ :doc:`profiles`
