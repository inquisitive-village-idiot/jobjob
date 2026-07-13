#!/usr/bin/env python3
"""Dedup resolution: merge or delete a flagged-duplicate application entity.

Duplicate *flagging* lives in ``tracking_service`` (a normalized company+role
signal — ``jobjob.structure.dedup`` — computed fresh at listing time; see
``application-identity`` design D3). This module is the user-triggered
resolution once a flag is raised: **merge** two duplicates into one surviving
entity, or **delete** a flagged duplicate outright. Dedup is never automatic —
these are always explicit actions taken from the UI.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from jobjob.storage.base import archive_timestamp
from jobjob.storage.local import LocalStorageAdapter
from services.application_metadata import read_metadata, union_notes


def merge_applications(
    survivor_folder: Path,
    loser_folder: Path,
    *,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """Merge ``loser_folder`` into ``survivor_folder``; the loser is removed.

    The survivor keeps its ``entity_id``/status/root execution untouched
    (design D3 — "the surviving entity keeps its id/status/root execution").
    The loser's current root execution and every one of its already-archived
    executions are re-parented into the survivor's ``archive/``
    (``LocalStorageAdapter.merge_from`` — filesystem moves; the operators
    triggering this from the webapp always work against the local mirror,
    the same as every other execution-management action in this codebase —
    see ``jobjob.storage.drive.DriveStorageAdapter.merge_from`` for the
    Drive-API-move-by-id equivalent used directly by build-time code). The
    loser's changelog notes are unioned into the survivor's ``metadata.json``.
    The now-empty loser folder is then deleted outright.

    Arguments:
        survivor_folder: The entity folder that survives the merge.
        loser_folder: The duplicate entity folder being absorbed.
        logger: Optional logger.
    Returns:
        A summary dict: ``{"merged_artifacts": int, "notes_added": int,
        "executions": int}`` (``executions`` is the survivor's total archived
        count after the merge).
    """
    _logger = logger or logging.getLogger(__name__)
    survivor = LocalStorageAdapter(survivor_folder)
    loser = LocalStorageAdapter(loser_folder)

    moved = survivor.merge_from(loser, archive_timestamp())

    loser_notes = read_metadata(loser_folder).get("notes") or []
    if loser_notes:
        union_notes(survivor_folder, loser_notes)

    shutil.rmtree(loser_folder)
    _logger.info(
        "Merged duplicate %s into %s: %d artifact(s) absorbed, %d note(s) unioned",
        loser_folder,
        survivor_folder,
        len(moved),
        len(loser_notes),
    )
    return {
        "merged_artifacts": len(moved),
        "notes_added": len(loser_notes),
        "executions": len(survivor.list_executions()),
    }


def delete_application(
    folder: Path, *, logger: Optional[logging.Logger] = None
) -> None:
    """Delete an application entity folder outright (dedup: delete duplicate).

    Irreversible — every tier (entity/source/execution, including any
    archived executions) goes with it. The motivating case is a flagged
    duplicate the user has decided is simply wrong (not worth merging), but
    nothing here requires the flag to still be set — the caller/UI decides
    when this is the right action.

    Arguments:
        folder: The application (entity) folder to remove.
        logger: Optional logger.
    """
    _logger = logger or logging.getLogger(__name__)
    shutil.rmtree(folder)
    _logger.info("Deleted application folder: %s", folder)


# __END__
