Prerequisites
=============

jobjob is a small Python program. You need **one** of the following to install it. If
you're not sure, choose ``uv`` — it brings its own Python, so there is nothing else to
install.

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Tool
     - Use it if…
     - Install page
   * - **uv** (recommended)
     - You want the simplest path. No separate Python needed.
     - https://docs.astral.sh/uv/getting-started/installation/
   * - **pipx**
     - You already have Python 3.12+ and prefer isolated app installs.
     - https://pipx.pypa.io/stable/installation/
   * - **pip**
     - You already have Python 3.12+ and a virtual environment.
     - https://pip.pypa.io/en/stable/installation/

jobjob requires **Python ≥ 3.12** (only relevant for the ``pip``/``pipx`` paths; ``uv``
handles this for you).

Opening a terminal
------------------

A few steps use a **terminal** (also called a command line). You only paste a line or
two — you don't need to know how it works.

- **macOS** — press ``Cmd`` + ``Space``, type ``Terminal``, press ``Enter``.
- **Windows** — press the ``Start`` key, type ``PowerShell``, press ``Enter``.
- **Linux** — open your *Terminal* application.

Optional: Google account
------------------------

jobjob works fully **without Google** — output is saved to your computer. Connect Google
only if you want finished applications saved to **Google Drive/Docs** as editable
documents, or if you'll use :doc:`enrichment <usage-enrichment>` (which writes to a
Google Sheet). That setup is covered later in :doc:`google-project`.

Next
----

→ :doc:`credentials`
