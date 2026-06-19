#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.gapi.drive as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_service(self) -> mock.MagicMock:
        # NOTE: service.files() returns the same files-resource mock each call,
        #   so per-method return values are easy to configure.
        service = mock.MagicMock()
        self.files = service.files.return_value
        return service

    def set_list(self, files) -> None:
        self.files.list.return_value.execute.return_value = {"files": files}


class TestSanitizeName(ThisTestCase):
    """Test function."""

    def test_strips_disallowed_characters(self) -> None:
        # NOTE: characters are removed, not replaced with spaces.
        self.assertEqual("Acme Inc", MOD.sanitize_name("Acme, Inc."))

    def test_collapses_whitespace_from_dropped_punctuation(self) -> None:
        self.assertEqual("Data AI Policy", MOD.sanitize_name("Data & AI Policy"))


class TestPascalCase(ThisTestCase):
    """Test function."""

    def test_joins_words_capitalized(self) -> None:
        self.assertEqual("IsomorphicLabs", MOD.pascal_case("Isomorphic Labs"))

    def test_preserves_internal_capitals(self) -> None:
        self.assertEqual("MLEngineer", MOD.pascal_case("ML Engineer"))

    def test_strips_punctuation(self) -> None:
        self.assertEqual(
            "PrincipalCorrespondent", MOD.pascal_case("Principal, Correspondent")
        )


class TestApplicationFolderName(ThisTestCase):
    """Test function."""

    def test_formats_company_role_name(self) -> None:
        # No date prefix — reprocessing overwrites in place (date is recovered
        # from the folder mtime for display).
        found = MOD.application_folder_name("Acme", "Senior Engineer")
        self.assertEqual("Acme - Senior Engineer", found)


class TestFindApplicationFolder(ThisTestCase):
    """Test function."""

    def test_returns_id_when_present(self) -> None:
        service = self.make_service()
        self.set_list([{"id": "F1", "name": "Acme - Eng"}])
        self.assertEqual("F1", MOD.find_application_folder(service, "Acme", "Eng"))

    def test_returns_none_when_absent(self) -> None:
        service = self.make_service()
        self.set_list([])
        self.assertIsNone(MOD.find_application_folder(service, "Acme", "Eng"))


class TestCreateApplicationFolder(ThisTestCase):
    """Test function."""

    def test_reuses_existing_folder(self) -> None:
        service = self.make_service()
        self.set_list([{"id": "F1", "name": "n", "webViewLink": "x"}])

        found = MOD.create_application_folder(service, "Acme", "Eng")

        self.assertEqual("F1", found)
        self.files.create.assert_not_called()

    def test_creates_when_absent(self) -> None:
        service = self.make_service()
        self.set_list([])
        self.files.create.return_value.execute.return_value = {
            "id": "NEW", "name": "n"
        }

        found = MOD.create_application_folder(service, "Acme", "Eng", parent_id="P")

        with self.subTest("returns new id"):
            self.assertEqual("NEW", found)
        with self.subTest("sets parent on metadata"):
            _, kwargs = self.files.create.call_args
            self.assertEqual(["P"], kwargs["body"]["parents"])


class TestCopyResumeTemplate(ThisTestCase):
    """Test function."""

    def test_requires_template_id(self) -> None:
        service = self.make_service()
        with self.assertRaisesRegex(ValueError, "template_id is required"):
            MOD.copy_resume_template(service, "F", "")

    def test_resets_existing_in_place(self) -> None:
        # On reprocess the existing resume doc is reset to the template in place
        # (same id → revision history preserved); it is NOT copied/recreated.
        service = self.make_service()
        self.set_list([{"id": "OLD", "name": "Resume"}])

        with mock.patch.object(MOD, "_reset_doc_to_template") as reset:
            found = MOD.copy_resume_template(service, "F", "TPL")

        with self.subTest("returns the existing id"):
            self.assertEqual("OLD", found)
        with self.subTest("reset the existing doc to the template"):
            args = reset.call_args.args
            self.assertIn("OLD", args)
            self.assertIn("TPL", args)
        with self.subTest("did not copy"):
            self.files.copy.assert_not_called()

    def test_copies_when_absent(self) -> None:
        service = self.make_service()
        self.set_list([])
        self.files.copy.return_value.execute.return_value = {
            "id": "DOC", "name": "Resume"
        }

        found = MOD.copy_resume_template(service, "F", "TPL")

        with self.subTest("returns copied id"):
            self.assertEqual("DOC", found)
        with self.subTest("copied from template"):
            _, kwargs = self.files.copy.call_args
            self.assertEqual("TPL", kwargs["fileId"])


class TestUploadFile(ThisTestCase):
    """Test function."""

    def test_creates_when_absent(self) -> None:
        service = self.make_service()
        self.set_list([])
        self.files.create.return_value.execute.return_value = {"id": "U", "name": "n"}
        media_cls = mock.MagicMock()

        found = MOD.upload_file(
            service, "/tmp/x.pdf", "F", "x.pdf", _media_cls=media_cls
        )

        with self.subTest("returns new id"):
            self.assertEqual("U", found)
        with self.subTest("built media"):
            media_cls.assert_called_once()
        with self.subTest("did not update"):
            self.files.update.assert_not_called()

    def test_updates_in_place_when_present(self) -> None:
        service = self.make_service()
        self.set_list([{"id": "EX", "name": "x.pdf"}])
        self.files.update.return_value.execute.return_value = {"id": "EX", "name": "n"}

        found = MOD.upload_file(
            service, "/tmp/x.pdf", "F", "x.pdf", _media_cls=mock.MagicMock()
        )

        with self.subTest("returns existing id"):
            self.assertEqual("EX", found)
        with self.subTest("updated the existing file in place"):
            _, kwargs = self.files.update.call_args
            self.assertEqual("EX", kwargs["fileId"])
        with self.subTest("did not create"):
            self.files.create.assert_not_called()


class TestUploadDocxAsGoogleDoc(ThisTestCase):
    """Test function."""

    def test_creates_when_absent(self) -> None:
        service = self.make_service()
        self.set_list([])
        self.files.create.return_value.execute.return_value = {"id": "U", "name": "n"}

        found = MOD.upload_docx_as_google_doc(
            service, "/tmp/x.docx", "F", "README", _media_cls=mock.MagicMock()
        )

        with self.subTest("returns new id"):
            self.assertEqual("U", found)
        with self.subTest("created as a Google Doc"):
            _, kwargs = self.files.create.call_args
            self.assertEqual(MOD.GDOC_MIME, kwargs["body"]["mimeType"])

    def test_updates_in_place_when_present(self) -> None:
        service = self.make_service()
        self.set_list([{"id": "EX", "name": "README"}])
        self.files.update.return_value.execute.return_value = {"id": "EX", "name": "n"}

        found = MOD.upload_docx_as_google_doc(
            service, "/tmp/x.docx", "F", "README", _media_cls=mock.MagicMock()
        )

        with self.subTest("returns existing id"):
            self.assertEqual("EX", found)
        with self.subTest("updated the existing doc in place"):
            _, kwargs = self.files.update.call_args
            self.assertEqual("EX", kwargs["fileId"])
        with self.subTest("did not create a new doc"):
            self.files.create.assert_not_called()


class TestResetDocToTemplate(ThisTestCase):
    """Test function."""

    def test_exports_template_then_updates_in_place(self) -> None:
        service = self.make_service()
        # Injected downloader: one chunk then done, so the export loop terminates.
        downloader = mock.MagicMock()
        downloader.next_chunk.return_value = (None, True)
        download_cls = mock.MagicMock(return_value=downloader)

        MOD._reset_doc_to_template(
            service, "DOC", "TPL", LOGGER,
            _download_cls=download_cls, _upload_cls=mock.MagicMock(),
        )

        with self.subTest("exported the template as DOCX"):
            _, kwargs = self.files.export_media.call_args
            self.assertEqual("TPL", kwargs["fileId"])
            self.assertEqual(MOD.DOCX_MIME, kwargs["mimeType"])
        with self.subTest("updated the existing doc in place"):
            _, kwargs = self.files.update.call_args
            self.assertEqual("DOC", kwargs["fileId"])


class TestExportDocAsPdf(ThisTestCase):
    """Test function."""

    def test_exports_and_returns_output_path(self) -> None:
        import pathlib
        import tempfile

        service = self.make_service()
        service.files.return_value.export_media.return_value = mock.MagicMock()

        downloader = mock.MagicMock()
        downloader.next_chunk.return_value = (None, True)
        downloader_cls = mock.MagicMock(return_value=downloader)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = pathlib.Path(f.name)

        try:
            result = MOD.export_doc_as_pdf(
                service, "DOC_ID", output_path, _downloader_cls=downloader_cls
            )
            self.assertEqual(output_path, result)
        finally:
            output_path.unlink(missing_ok=True)

    def test_calls_export_media_with_pdf_mime(self) -> None:
        import pathlib
        import tempfile

        service = self.make_service()
        service.files.return_value.export_media.return_value = mock.MagicMock()

        downloader = mock.MagicMock()
        downloader.next_chunk.return_value = (None, True)
        downloader_cls = mock.MagicMock(return_value=downloader)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = pathlib.Path(f.name)

        try:
            MOD.export_doc_as_pdf(
                service, "DOC_ID", output_path, _downloader_cls=downloader_cls
            )
            service.files.return_value.export_media.assert_called_once_with(
                fileId="DOC_ID", mimeType=MOD.PDF_MIME
            )
        finally:
            output_path.unlink(missing_ok=True)

    def test_loops_until_done(self) -> None:
        import pathlib
        import tempfile

        service = self.make_service()
        service.files.return_value.export_media.return_value = mock.MagicMock()

        downloader = mock.MagicMock()
        downloader.next_chunk.side_effect = [
            (None, False),
            (None, False),
            (None, True),
        ]
        downloader_cls = mock.MagicMock(return_value=downloader)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = pathlib.Path(f.name)

        try:
            MOD.export_doc_as_pdf(
                service, "DOC_ID", output_path, _downloader_cls=downloader_cls
            )
            self.assertEqual(3, downloader.next_chunk.call_count)
        finally:
            output_path.unlink(missing_ok=True)


# __END__
