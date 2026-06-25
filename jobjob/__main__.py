#!/usr/bin/env python3
"""`jobjob` — top-level CLI dispatcher.

A thin adapter exposing the ``apply`` and ``enrich`` endpoints through one
interface. Routes a sub-command to the matching module entrypoint; each
sub-command parses its own arguments (so ``jobjob apply --help`` and
``python -m jobjob.apply`` behave the same). Sub-commands register in ``COMMANDS``.
"""

import sys
from collections.abc import Callable, Iterable, Mapping
from typing import Optional

from jobjob.apply.__main__ import main as apply_main
from jobjob.auth.__main__ import main as auth_main
from jobjob.autofill.__main__ import main as autofill_main
from jobjob.cli import run_main
from jobjob.enrich.__main__ import main as enrich_main

# Sub-command name -> ``main(argv) -> int``.
COMMANDS: Mapping[str, Callable[..., int]] = {
    "apply": apply_main,
    "enrich": enrich_main,
    "auth": auth_main,
    "autofill": autofill_main,
}


def _usage() -> str:
    commands = "\n".join(f"  {name}" for name in COMMANDS)
    return f"usage: jobjob <command> [options]\n\ncommands:\n{commands}"


def main(argv: Optional[Iterable] = None) -> int:
    """Dispatch to a sub-command's main, passing the remaining arguments.

    Arguments:
        argv: Argument vector (defaults to ``sys.argv[1:]``).
    Returns:
        The sub-command's exit code (2 for usage errors).
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(_usage())
        return 0 if argv else 2

    command, rest = argv[0], argv[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"jobjob: unknown command '{command}'\n\n{_usage()}", file=sys.stderr)
        return 2
    return handler(rest)


def console_main() -> int:
    """Console-script entry point: run ``main`` with logging + error handling."""
    return run_main(main)


if __name__ == "__main__":
    sys.exit(run_main(main))


# __END__
