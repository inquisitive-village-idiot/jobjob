Profile content in a Git/GitHub repository
==========================================

A profile is just a directory (see :doc:`profiles`), so you can keep it under **version
control** and sync it across machines with **GitHub**. jobjob then uses it as an
**external profile** — registered and validated in place, never copied.

Use this if you want history on your content, a backup, or the same profile on more than
one computer.

What goes in the repo
---------------------

The profile directory, exactly as described in :doc:`profiles`::

   my-jobjob-profile/
     content/      highlights.toml  skills.toml  templates.toml
     reference/    background.md  writing_style.md  cover_letters/  stars/
     config/.profile
     prompt/       (optional prompt overrides)

.. warning::

   ``config/.profile`` holds your name and contact details but **no secrets** — your
   Anthropic key and Google token live in the machine-local app config, never in a
   profile. It is still safe to commit ``.profile``. Keep the repository **private** if
   you'd rather not publish your résumé content.

1. Create the repository
------------------------

You'll need **Git** (https://git-scm.com/downloads) and a **GitHub** account
(https://github.com/join).

Easiest path — start from an existing profile jobjob already made for you:

#. In the dashboard, create or import a profile (see :doc:`profiles`). Note its folder,
   e.g. ``~/Documents/jobjob/profiles/local``.
#. Turn that folder into a repository and push it. In a terminal::

      cd ~/Documents/jobjob/profiles/local
      git init
      git add .
      git commit -m "Initial profile"

#. Create an empty repo on GitHub (https://github.com/new), then connect and push —
   GitHub shows the exact two lines, which look like::

      git remote add origin https://github.com/<you>/<repo>.git
      git push -u origin main

2. Use it on another machine
----------------------------

#. Install jobjob there (:doc:`install`) and run it once so the jobjob folder exists.
#. Clone your repo somewhere convenient::

      git clone https://github.com/<you>/<repo>.git ~/Documents/jobjob/profiles/mine

#. Register it (next section), then switch to it.

3. Register the profile
-----------------------

**In the dashboard (recommended):** **Settings → Profiles → Register**, point it at the
cloned folder, then **switch** to it.

**By hand:** add it to the app config (see :doc:`configuration`)::

   JOBJOB_PROFILE_MINE=/Users/you/Documents/jobjob/profiles/mine
   JOBJOB_ACTIVE_PROFILE=mine

The registry key after ``JOBJOB_PROFILE_`` is the profile's name (``MINE`` →
``mine``). Registration **validates** the folder's shape; nothing is copied, so edits in
the app write straight into your repository.

4. Keep it in sync
------------------

Edits you make in the **Static Content** tab change the files in the repo folder.
Commit and push them like any other change::

   cd ~/Documents/jobjob/profiles/mine
   git add .
   git commit -m "Update highlights"
   git push

On another machine, ``git pull`` before you start to get the latest content.

See also
--------

→ :doc:`profiles` · :doc:`configuration`
