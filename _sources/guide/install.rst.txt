Install
=======

Pick the line that matches the tool you set up in :doc:`prerequisites`, paste it into a
terminal, and press ``Enter``. The same command works on Windows, macOS, and Linux.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Tool
     - Command
   * - **uv**
     - ``uv tool install jobjob``
   * - **pipx**
     - ``pipx install jobjob``
   * - **pip**
     - ``pip install jobjob``

This installs two commands:

- ``jobjob-app`` — launches the local dashboard (what most people use).
- ``jobjob`` — the command-line interface (see :doc:`usage-applications` and
  :doc:`usage-enrichment`).

Confirm it worked
-----------------

Run::

   jobjob-app --help

You should see usage text.

.. tip::

   "Command not found"? Close the terminal and open a new one so it picks up the newly
   installed command, then try again.

Upgrading
---------

Upgrade jobjob the same way you would any installed tool:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Tool
     - Command
   * - **uv**
     - ``uv tool upgrade jobjob``
   * - **pipx**
     - ``pipx upgrade jobjob``
   * - **pip**
     - ``pip install --upgrade jobjob``

You can also update from inside the dashboard (**Settings → Update**).

Next
----

→ :doc:`configuration`
