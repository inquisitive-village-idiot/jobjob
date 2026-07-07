#!/usr/bin/env python3
"""Test."""

import io
import json
import logging
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import jobjob.skills.suggest as MOD
from jobjob.structure.skill import Skill, SkillSet
from jobjob.structure.skillcloud import CloudSkill, SkillCloud

LOGGER = logging.getLogger(__name__)

DOCKER = CloudSkill(
    id="docker",
    name="Docker",
    aliases=("containerisation",),
    categories={"technical": 1.0},
)
PYTHON = CloudSkill(
    id="python_computer_programming",
    name="Python (computer programming)",
    aliases=("Python",),
    categories={"technical": 1.0},
)


def make_cloud(*skills: CloudSkill) -> SkillCloud:
    index = {}
    for skill in skills:
        index[skill.id.lower()] = skill.id
        index[skill.name.lower()] = skill.id
        for alias in skill.aliases:
            index[alias.lower()] = skill.id
    return SkillCloud(
        skills={s.id: s for s in skills}, esco_version="test", _index=index
    )


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_root(self) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)

    def make_application_dir(self, root: Path, name: str, analysis: dict) -> Path:
        app_dir = Path(root, name)
        app_dir.mkdir()
        Path(app_dir, MOD.SUMMARY_NAME).write_text("{}", encoding="utf-8")
        Path(app_dir, MOD.SKILLS_NAME).write_text(
            json.dumps(analysis), encoding="utf-8"
        )
        return app_dir


class TestAggregateCandidates(ThisTestCase):
    """Test function."""

    def test_dedupes_across_applications_with_citations(self) -> None:
        root = self.make_root()
        self.make_application_dir(
            root,
            "2026-07-01 - Acme - Engineer",
            {"critical_supported": [{"skill": "Docker", "evidence": "STAR A"}]},
        )
        self.make_application_dir(
            root,
            "2026-07-02 - Globex - Engineer",
            {"important_supported": [{"skill": "containerisation", "evidence": "B"}]},
        )

        result = MOD.aggregate_candidates(root, cloud=make_cloud(DOCKER))

        expected = [
            MOD.SkillSuggestion(
                canonical_id="docker",
                name="Docker",
                citations=(
                    MOD.Citation("2026-07-01 - Acme - Engineer", "STAR A"),
                    MOD.Citation("2026-07-02 - Globex - Engineer", "B"),
                ),
            )
        ]
        self.assertEqual(expected, result)

    def test_declared_skills_are_excluded(self) -> None:
        root = self.make_root()
        self.make_application_dir(
            root,
            "app",
            {
                "critical_supported": [
                    {"skill": "Docker", "evidence": "A"},
                    {"skill": "Python", "evidence": "B"},
                ]
            },
        )
        skill_set = SkillSet(
            skills=(Skill(label="docker", text="Docker", canonical_id="docker"),)
        )

        result = MOD.aggregate_candidates(
            root, skill_set=skill_set, cloud=make_cloud(DOCKER, PYTHON)
        )

        expected = ["python_computer_programming"]
        found = [s.canonical_id for s in result]
        self.assertEqual(expected, found)

    def test_skips_non_canonical_and_incomplete_directories(self) -> None:
        root = self.make_root()
        # Not in the cloud -> no candidate.
        self.make_application_dir(
            root, "app", {"critical_supported": [{"skill": "quantum telepathy"}]}
        )
        # Missing skills_analysis.json -> not a processed application.
        partial = Path(root, "partial")
        partial.mkdir()
        Path(partial, MOD.SUMMARY_NAME).write_text("{}", encoding="utf-8")
        # A stray file at the root is ignored.
        Path(root, "notes.txt").write_text("hi", encoding="utf-8")

        result = MOD.aggregate_candidates(root, cloud=make_cloud(DOCKER))

        expected = []
        self.assertEqual(expected, result)

    def test_unreadable_analysis_is_skipped_with_warning(self) -> None:
        root = self.make_root()
        app_dir = self.make_application_dir(
            root, "good", {"critical_supported": [{"skill": "Docker"}]}
        )
        bad_dir = self.make_application_dir(root, "bad", {})
        Path(bad_dir, MOD.SKILLS_NAME).write_text("{not json", encoding="utf-8")
        mock_logger = mock.Mock()

        result = MOD.aggregate_candidates(
            root, cloud=make_cloud(DOCKER), logger=mock_logger
        )

        with self.subTest("good application still aggregates"):
            expected = [app_dir.name]
            found = [c.application for s in result for c in s.citations]
            self.assertEqual(expected, found)
        with self.subTest("skip is logged"):
            self.assertTrue(mock_logger.warning.called)

    def test_missing_root_raises(self) -> None:
        root = Path(self.make_root(), "nope")
        with self.assertRaisesRegex(FileNotFoundError, "nope"):
            MOD.aggregate_candidates(root, cloud=make_cloud())


class TestAppendConfirmed(ThisTestCase):
    """Test function."""

    SEED = "\n".join(
        (
            "# hand-curated — do not reorder",
            "[tool.skills]",
            "default_number = 12",
            "",
            "[[tool.skills.skill]]",
            'label = "writing"',
            'text = "Science writing"',
            "keywords = []",
            "",
        )
    )

    def make_skills_file(self) -> Path:
        path = Path(self.make_root(), "skills.toml")
        path.write_text(self.SEED, encoding="utf-8")
        return path

    def make_suggestions(self) -> list:
        return [MOD.SkillSuggestion(canonical_id="docker", name="Docker", citations=())]

    def test_appends_entry_derived_from_cloud(self) -> None:
        path = self.make_skills_file()

        result = MOD.append_confirmed(
            self.make_suggestions(),
            ["docker", "docker"],  # duplicates collapse
            path,
            cloud=make_cloud(DOCKER),
        )

        content = path.read_text(encoding="utf-8")
        with self.subTest("one entry appended"):
            expected = 1
            self.assertEqual(expected, result)
        with self.subTest("entry derives from the cloud skill"):
            for needle in ('label = "docker"', 'text = "Docker"', "containerisation"):
                self.assertIn(needle, content)
        with self.subTest("existing formatting and comments preserved"):
            self.assertIn("# hand-curated — do not reorder", content)
            self.assertIn('label = "writing"', content)

    def test_unknown_id_aborts_without_writing(self) -> None:
        path = self.make_skills_file()

        with self.assertRaisesRegex(ValueError, "kubernetes"):
            MOD.append_confirmed(
                self.make_suggestions(),
                ["docker", "kubernetes"],
                path,
                cloud=make_cloud(DOCKER),
            )

        expected = self.SEED
        found = path.read_text(encoding="utf-8")
        self.assertEqual(expected, found)


class TestRenderSuggestions(ThisTestCase):
    """Test function."""

    def test_empty_reports_covered(self) -> None:
        result = MOD.render_suggestions([])
        self.assertIn("No skills-file candidates", result)

    def test_lists_ids_names_and_citations(self) -> None:
        suggestions = [
            MOD.SkillSuggestion(
                canonical_id="docker",
                name="Docker",
                citations=(MOD.Citation("2026-07-01 - Acme - Engineer", "STAR A"),),
            )
        ]

        result = MOD.render_suggestions(suggestions)

        for expected in ("docker — Docker", "Acme", "STAR A", "--apply"):
            with self.subTest(expected=expected):
                self.assertIn(expected, result)


class TestSuggestionsAsDicts(ThisTestCase):
    """Test function."""

    def test_flattens_citations(self) -> None:
        suggestions = [
            MOD.SkillSuggestion(
                canonical_id="docker",
                name="Docker",
                citations=(MOD.Citation("app", "A"),),
            )
        ]

        found = MOD.suggestions_as_dicts(suggestions)

        expected = [
            {
                "canonical_id": "docker",
                "name": "Docker",
                "citations": ({"application": "app", "evidence": "A"},),
            }
        ]
        self.assertEqual(expected, found)


class TestMain(ThisTestCase):
    """Test function (CLI)."""

    def test_prints_report_and_exits_zero(self) -> None:
        root = self.make_root()
        self.make_application_dir(
            root, "app", {"critical_supported": [{"skill": "Docker"}]}
        )
        with (
            mock.patch.object(MOD, "load_skills", return_value=None),
            mock.patch.object(MOD, "get_skill_cloud", return_value=make_cloud(DOCKER)),
            redirect_stdout(io.StringIO()) as captured,
        ):
            result = MOD.main(["suggest", "--root", str(root)])

        expected = 0
        self.assertEqual(expected, result)
        self.assertIn("docker — Docker", captured.getvalue())

    def test_no_configured_root_exits_two(self) -> None:
        settings = mock.Mock(applications_output_dir=None)
        with mock.patch.object(MOD, "load_settings", return_value=settings):
            result = MOD.main(["suggest"])

        expected = 2
        self.assertEqual(expected, result)

    def test_apply_appends_to_the_skills_file(self) -> None:
        root = self.make_root()
        self.make_application_dir(
            root, "app", {"critical_supported": [{"skill": "Docker"}]}
        )
        skills_path = Path(self.make_root(), "skills.toml")
        with (
            mock.patch.object(MOD, "load_skills", return_value=None),
            mock.patch.object(MOD, "get_skill_cloud", return_value=make_cloud(DOCKER)),
            mock.patch.object(MOD, "get_content_path", return_value=skills_path),
            redirect_stdout(io.StringIO()),
        ):
            result = MOD.main(["suggest", "--root", str(root), "--apply", "docker"])

        expected = 0
        self.assertEqual(expected, result)
        self.assertIn('label = "docker"', skills_path.read_text(encoding="utf-8"))

    def test_apply_with_invalid_id_writes_nothing(self) -> None:
        root = self.make_root()
        self.make_application_dir(
            root, "app", {"critical_supported": [{"skill": "Docker"}]}
        )
        skills_path = Path(self.make_root(), "skills.toml")
        with (
            mock.patch.object(MOD, "load_skills", return_value=None),
            mock.patch.object(MOD, "get_skill_cloud", return_value=make_cloud(DOCKER)),
            mock.patch.object(MOD, "get_content_path", return_value=skills_path),
            redirect_stdout(io.StringIO()),
        ):
            result = MOD.main(["suggest", "--root", str(root), "--apply", "kubernetes"])

        with self.subTest("nonzero exit"):
            self.assertNotEqual(0, result)
        with self.subTest("no file created"):
            expected = False
            found = skills_path.exists()
            self.assertEqual(expected, found)


# __END__
