#!/usr/bin/env python3
"""Tests for the resume-import API (extract + save).

A minimal FastAPI app mounts only the resume-import router. The AI client and the
extractor are injected so no network call is made; saves are sandboxed to tmp_path.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import security
import routers.resume_import as ri
from jobjob.ingest.resume_import import ResumeImportDraft
from jobjob.structure.highlight import Highlight
from jobjob.structure.skill import Skill


@pytest.fixture
def repo(tmp_path):
    security.configure_sandbox([tmp_path])
    return tmp_path


@pytest.fixture
def client(repo):
    app = FastAPI()
    app.include_router(ri.router, prefix="/api/resume-import")
    app.state.repo_root = repo
    app.state.profile_dir = None  # no active profile -> writes under repo static/
    return TestClient(app)


_DRAFT = ResumeImportDraft(
    objective="Tell true stories about cells.",
    sections=("Experience",),
    highlights=(
        Highlight(context="a", text="Did a thing.", keywords=("x",), topic="Creativity"),
    ),
    skills=(Skill(label="fact_checking", text="Fact-Checking", keywords=("accuracy",)),),
    background="Tila Mer is a science correspondent.",
)


class TestExtractEndpoint:
    def test_happy_path_returns_draft(self, client, monkeypatch):
        monkeypatch.setattr(ri, "_ai_client", lambda: object())
        monkeypatch.setattr(ri, "extract_resume", lambda *a, **k: _DRAFT)
        resp = client.post(
            "/api/resume-import/extract",
            files={"file": ("resume.txt", b"resume text", "text/plain")},
            data={"background_mode": "fuller"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["objective"] == "Tell true stories about cells."
        assert body["highlights"][0]["topic"] == "Creativity"
        assert body["background_mode"] == "fuller"

    def test_unsupported_suffix_415(self, client):
        resp = client.post(
            "/api/resume-import/extract",
            files={"file": ("resume.rtf", b"x", "application/rtf")},
            data={"background_mode": "fuller"},
        )
        assert resp.status_code == 415

    def test_bad_background_mode_422(self, client):
        resp = client.post(
            "/api/resume-import/extract",
            files={"file": ("resume.pdf", b"x", "application/pdf")},
            data={"background_mode": "wild"},
        )
        assert resp.status_code == 422

    def test_extract_value_error_is_422(self, client, monkeypatch):
        def _boom(*a, **k):
            raise ValueError("image-only PDF")

        monkeypatch.setattr(ri, "_ai_client", lambda: object())
        monkeypatch.setattr(ri, "extract_resume", _boom)
        resp = client.post(
            "/api/resume-import/extract",
            files={"file": ("resume.pdf", b"x", "application/pdf")},
            data={"background_mode": "conservative"},
        )
        assert resp.status_code == 422
        assert "image-only" in resp.json()["detail"]


class TestSaveEndpoint:
    def _payload(self, **targets):
        return {
            "highlights": [
                {"context": "a", "topic": "Creativity", "text": "Did a thing.",
                 "keywords": ["x"], "enabled": True},
            ],
            "skills": [{"label": "fact_checking", "text": "Fact-Checking", "keywords": ["accuracy"]}],
            "background": "Tila Mer is a science correspondent.",
            "targets": targets,
        }

    def test_saves_selected_sections(self, client, repo):
        resp = client.post(
            "/api/resume-import/save",
            json=self._payload(highlights="replace", background="replace"),
        )
        assert resp.status_code == 200, resp.text
        saved = resp.json()["saved"]
        assert saved["highlights"]["count"] == 1
        assert "background" in saved
        assert "skills" not in saved  # not targeted
        assert (repo / "static" / "content" / "highlights.toml").is_file()
        assert (repo / "static" / "reference" / "background.md").is_file()

    def test_nothing_selected_422(self, client):
        resp = client.post("/api/resume-import/save", json=self._payload())
        assert resp.status_code == 422

    def test_bad_mode_422(self, client):
        resp = client.post(
            "/api/resume-import/save", json=self._payload(skills="merge")
        )
        assert resp.status_code == 422
