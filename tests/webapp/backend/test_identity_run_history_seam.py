#!/usr/bin/env python3
"""Integration seam: identity joins across run-history + tracking + the
frontend contract (docs-tests-overview).

Per-change unit tests cover ``run_matches_application`` (tracking_service)
and entity-id stamping (run_history) against hand-built dicts in isolation.
Nothing exercises the real ``/api/jobs`` (run listing) and
``/api/tracking/completed`` (application listing) endpoints *together*,
confirming their actual response shapes are joinable the way
``webapp/frontend/src/pages/ApplicationsPage.tsx``'s ``runMatchesApplication``
(a JS mirror of ``services.tracking_service.run_matches_application``)
assumes — including the case the id-preferring join exists for: a folder
rename that happens *after* a run has already been recorded against the old
name.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.jobs as jobs_router_module
from routers.jobs import router as jobs_router
from routers.tracking import router as tracking_router
from services import run_history
from services.application_metadata import ensure_entity_id
from services.tracking_service import (
    invalidate_completed_cache,
    run_matches_application,
)

_ARTIFACT_NAMES = [
    "summary.json",
    "JD_Acme_Engineer.pdf",
    "README.docx",
    "skills_analysis.json",
]


def _make_application(folder, *, with_identity: bool):
    folder.mkdir(parents=True, exist_ok=True)
    for name in _ARTIFACT_NAMES:
        (folder / name).write_text("x")
    if with_identity:
        entity_id = ensure_entity_id(folder)
        return entity_id
    return None


@pytest.fixture(autouse=True)
def _reset_live_jobs(monkeypatch):
    monkeypatch.setattr(jobs_router_module, "_jobs", {})


@pytest.fixture
def mirror(tmp_path):
    """Shared root: both the runs store (input dir) and the local mirror
    (output dir) live under it, same as a real deployment's settings dict."""
    invalidate_completed_cache()
    return tmp_path


@pytest.fixture
def client(mirror):
    app = FastAPI()
    app.include_router(jobs_router, prefix="/api/jobs")
    app.include_router(tracking_router, prefix="/api/tracking")
    app.state.settings = {
        "applications_input_dir": mirror,
        "applications_output_dir": mirror,
        "applications_output_drive_id": None,
        "credentials_file": None,
        "token_file": None,
        "enrichment_output_sheet_id": None,
    }
    return TestClient(app)


def _completed_item(client, folder_name):
    resp = client.get("/api/tracking/completed?refresh=true")
    assert resp.status_code == 200
    (item,) = [i for i in resp.json() if i["folder_name"] == folder_name]
    return item


def _run_record(client, run_id):
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    (record,) = [r for r in resp.json() if r["run_id"] == run_id]
    return record


class TestIdentityJoinAcrossRealEndpoints:
    """Both real endpoints' output, fed straight into the pure join helper —
    not hand-typed dicts — must join the way the frontend relies on."""

    def test_joins_by_entity_id_through_real_endpoint_responses(self, client, mirror):
        folder = mirror / "Acme - Principal Engineer"
        entity_id = _make_application(folder, with_identity=True)
        runs = run_history.runs_dir(mirror)
        run_history.start_run(
            runs, "r1", kind="build", label="jd.pdf", folder_name=folder.name
        )
        run_history.finish_run(runs, "r1", status="completed", entity_id=entity_id)

        run = _run_record(client, "r1")
        item = _completed_item(client, folder.name)

        assert run["entity_id"] == entity_id
        assert item["entity_id"] == entity_id
        assert run_matches_application(run, item) is True

    def test_join_survives_a_rename_after_the_run_via_entity_id(self, client, mirror):
        # The whole point of the id-preferring join: a run recorded against
        # the old folder name must still match the application after it is
        # renamed (e.g. via Edit source / re-parse), because both sides now
        # carry the same entity_id.
        old_folder = mirror / "Acme - Principal Engineer"
        entity_id = _make_application(old_folder, with_identity=True)
        runs = run_history.runs_dir(mirror)
        run_history.start_run(
            runs, "r1", kind="build", label="jd.pdf", folder_name=old_folder.name
        )
        run_history.finish_run(runs, "r1", status="completed", entity_id=entity_id)

        new_folder = mirror / "Acme Inc - Principal Engineer"
        old_folder.rename(new_folder)

        run = _run_record(client, "r1")
        renamed_item = _completed_item(client, new_folder.name)

        assert run["folder_name"] != renamed_item["folder_name"]
        assert run_matches_application(run, renamed_item) is True

    def test_legacy_records_fall_back_to_folder_name_and_do_not_survive_rename(
        self, client, mirror
    ):
        # Neither side has an entity_id (pre-application-identity data) — the
        # join falls back to folder_name, exactly as it always has, and a
        # rename legitimately breaks the association (no id to carry it).
        folder = mirror / "Acme - Principal Engineer"
        _make_application(folder, with_identity=False)
        runs = run_history.runs_dir(mirror)
        run_history.start_run(
            runs, "r1", kind="build", label="jd.pdf", folder_name=folder.name
        )
        run_history.finish_run(runs, "r1", status="completed")

        run = _run_record(client, "r1")
        item = _completed_item(client, folder.name)

        assert "entity_id" not in run
        assert item["entity_id"] is None
        assert run_matches_application(run, item) is True

        renamed = mirror / "Acme Inc - Principal Engineer"
        folder.rename(renamed)
        renamed_item = _completed_item(client, renamed.name)
        assert run_matches_application(run, renamed_item) is False


# __END__
