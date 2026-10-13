"""Document checks: roots, type, size, encryption, page count."""
import logging
import os
import tempfile
import unittest
from unittest.mock import patch

from docusign_upload import pdfcheck
from docusign_upload.pdfcheck import PdfCheckError, check_pdf
from support import make_pdf


class PdfCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "runtime")
        os.makedirs(self.root)
        self.roots = (self.root,)
        # pypdf warns on stderr about the deliberately damaged file; the check itself is asserted
        pypdf_log = logging.getLogger("pypdf")
        self.addCleanup(pypdf_log.setLevel, pypdf_log.level)
        pypdf_log.setLevel(logging.ERROR)

    def path(self, *parts):
        p = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def write(self, name, data):
        p = self.path(name)
        with open(p, "wb") as fh:
            fh.write(data)
        return p

    def test_a_good_pdf_reports_name_pages_and_bytes(self):
        p = make_pdf(self.path("BUILD CONTRACT_LOT 1_TESTVILLE_EXAMPLE.pdf"), 37)
        f = check_pdf(p, self.roots)
        self.assertEqual((f.name, f.pages, f.path), ("BUILD CONTRACT_LOT 1_TESTVILLE_EXAMPLE.pdf", 37, p))
        self.assertEqual(f.bytes, os.path.getsize(p))

    def test_spaces_and_brackets_in_the_job_folder_are_fine(self):
        p = make_pdf(self.path("26098 LOT 4 [STAGE 2]", "CONTRACT DOCUMENTATION", "PLANS_LOT 4.pdf"), 3)
        self.assertEqual(check_pdf(p, self.roots).pages, 3)

    def test_refusals(self):
        outside_dir = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(outside_dir)
        cases = {
            "relative/path.pdf": "absolute",
            make_pdf(os.path.join(outside_dir, "a.pdf"), 1): "outside the allowed upload roots",
            self.path("missing.pdf"): "not an existing file",
            self.write("notes.txt", b"%PDF-1.7 pretend"): r"not a \.pdf",
            self.write("fake.pdf", b"PK\x03\x04 a zip, not a pdf"): "does not start with %PDF-",
            self.write("damaged.pdf", b"%PDF-1.7\nnothing else here"): "page count could not be read|has no pages",
            make_pdf(self.path("locked.pdf"), 2, password="synthetic"): "password-protected",
        }
        for path, needle in cases.items():
            with self.subTest(file=os.path.basename(path)):
                with self.assertRaisesRegex(PdfCheckError, needle):
                    check_pdf(path, self.roots)

    def test_no_roots_means_no_documents(self):
        p = make_pdf(self.path("a.pdf"), 1)
        with self.assertRaisesRegex(PdfCheckError, "outside"):
            check_pdf(p, ())

    def test_size_limit(self):
        p = make_pdf(self.path("big.pdf"), 1)
        with patch.object(pdfcheck, "MAX_DOCUMENT_BYTES", 10):
            with self.assertRaisesRegex(PdfCheckError, "limit per document"):
                check_pdf(p, self.roots)

    def test_a_link_out_of_the_root_is_refused(self):
        outside_dir = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(outside_dir)
        target = make_pdf(os.path.join(outside_dir, "target.pdf"), 1)
        link = self.path("link.pdf")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks need extra rights on this machine")
        with self.assertRaisesRegex(PdfCheckError, "outside"):
            check_pdf(link, self.roots)
