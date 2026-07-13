#!/usr/bin/env python3
"""Integration seam: dedup merge re-parenting a loser's full execution
history into the survivor, followed by promoting one of the re-parented
executions back to root (docs-tests-overview).

``test_dedup_service.py`` and ``TestMergeApplication`` in
``test_tracking_router.py`` each cover one archived execution (or none) on
the loser in isolation. Nothing exercises the compound, real-world shape a
possible-duplicate merge actually resolves: a survivor that *already* has
its own locked/noted archive history, merging a loser that *also* has a
locked/noted archive history plus a live root execution — then confirms the
merged history is actually usable afterward (promote one of the re-parented
executions back to root) without losing any identity/notes/lock state along
the way.
"""

import time
import urllib.parse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import security
from routers.tracking import router
from services.application_metadata import (
    add_note,
    ensure_entity_id,
    read_metadata,
    read_notes,
)

_SURVIVOR = "2026-01-01 - Acme - Engineer"
_LOSER = "2026-01-02 - Acme Inc - Engineer"


def _executions_url(folder):
    return f"/api/tracking/applications/{urllib.parse.quote(folder)}/executions"


def _execution_url(folder, timestamp):
    return f"{_executions_url(folder)}/{timestamp}"


def _merge_url(folder):
    return f"/api/tracking/applications/{urllib.parse.quote(folder)}/merge"


@pytest.fixture
def mirror(tmp_path):
    security.configure_sandbox([tmp_path])
    return tmp_path


@pytest.fixture
def client(mirror):
    app = FastAPI()
    app.include_router(router, prefix="/api/tracking")
    app.state.settings = {"applications_output_dir": str(mirror)}
    return TestClient(app)


def _seed_full_history(
    mirror, folder_name, *, root_text, archived_ts, archived_text, entity_note
):
    """Create a folder with a live root execution, one archived execution,
    an entity_id, and one changelog note. Lock/note on the archived
    execution is set separately via the API (see callers)."""
    folder = mirror / folder_name
    (folder / "archive" / archived_ts).mkdir(parents=True)
    (folder / "summary.json").write_text(root_text)
    (folder / "archive" / archived_ts / "summary.json").write_text(archived_text)
    entity_id = ensure_entity_id(folder)
    add_note(folder, entity_note)
    return folder, entity_id


class TestMergeReparentsFullHistoryAndUnionsNotes:
    def test_survivor_ends_up_with_both_histories_and_promotable(self, client, mirror):
        survivor, survivor_id = _seed_full_history(
            mirror,
            _SURVIVOR,
            root_text="survivor-current",
            archived_ts="ts-survivor-old",
            archived_text="survivor-archived",
            entity_note="recruiter reached out (survivor)",
        )
        client.patch(
            _execution_url(_SURVIVOR, "ts-survivor-old"),
            json={"note": "keep survivor's old run", "locked": True},
        )

        loser, loser_id = _seed_full_history(
            mirror,
            _LOSER,
            root_text="loser-current",
            archived_ts="ts-loser-old",
            archived_text="loser-archived",
            entity_note="recruiter reached out (loser)",
        )
        client.patch(
            _execution_url(_LOSER, "ts-loser-old"),
            json={"note": "loser's own note"},
        )

        # --- merge ---
        resp = client.post(_merge_url(_SURVIVOR), json={"loser_folder_name": _LOSER})
        assert resp.status_code == 200, resp.text

        assert not loser.exists()

        # Survivor identity untouched.
        meta = read_metadata(survivor)
        assert meta["entity_id"] == survivor_id
        assert meta["entity_id"] != loser_id

        # Entity-level notes unioned.
        texts = [n["text"] for n in read_notes(survivor)]
        assert "recruiter reached out (survivor)" in texts
        assert "recruiter reached out (loser)" in texts

        # Execution-level history: survivor's own archived execution keeps
        # its lock/note, the loser's own archived execution is re-parented
        # with its note intact, and the loser's former root execution lands
        # as a brand-new archived execution.
        executions = client.get(_executions_url(_SURVIVOR)).json()["executions"]
        by_ts = {e["timestamp"]: e for e in executions}
        assert len(executions) == 3
        assert by_ts["ts-survivor-old"] == {
            "timestamp": "ts-survivor-old",
            "note": "keep survivor's old run",
            "locked": True,
        }
        assert by_ts["ts-loser-old"]["note"] == "loser's own note"
        assert by_ts["ts-loser-old"]["locked"] is False
        new_ts = next(
            ts for ts in by_ts if ts not in ("ts-survivor-old", "ts-loser-old")
        )
        assert by_ts[new_ts] == {"timestamp": new_ts, "note": None, "locked": False}
        assert (survivor / "archive" / new_ts / "summary.json").read_text() == (
            "loser-current"
        )

        # --- the merged-in history is actually usable: promote the
        # re-parented (loser's own archived) execution back to root ---
        # ``archive_timestamp`` is second-resolution; sleep past the second
        # boundary so the fresh archive dir this promote creates for the
        # outgoing root can't collide with (and clobber) the one the merge
        # above just created.
        time.sleep(1.1)
        promote_resp = client.post(
            f"{_execution_url(_SURVIVOR, 'ts-loser-old')}/promote"
        )
        assert promote_resp.status_code == 200, promote_resp.text
        assert (survivor / "summary.json").read_text() == "loser-archived"

        # Identity and notes are still intact after the promote — merge and
        # promote never touch metadata.json beyond what they're documented to.
        meta_after = read_metadata(survivor)
        assert meta_after["entity_id"] == survivor_id
        texts_after = [n["text"] for n in read_notes(survivor)]
        assert "recruiter reached out (survivor)" in texts_after
        assert "recruiter reached out (loser)" in texts_after

        # The pre-promote root ("survivor-current") is now itself archived,
        # and the promoted execution's lock/note sidecar didn't travel to root
        # (it described archived-state, not the live root).
        remaining = {
            e["timestamp"]
            for e in client.get(_executions_url(_SURVIVOR)).json()["executions"]
        }
        assert "ts-loser-old" not in remaining
        assert "ts-survivor-old" in remaining  # untouched by this promote
        assert (
            len(remaining) == 3
        )  # ts-survivor-old, new_ts, plus the just-archived root


# __END__
