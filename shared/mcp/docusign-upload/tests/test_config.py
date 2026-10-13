"""Config rules: required settings, key custody, upload roots per environment."""
import os
import tempfile
import unittest
from unittest.mock import patch

from docusign_upload import config
from docusign_upload.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = os.path.join(self.tmp.name, "synthetic-key.pem")
        with open(self.key, "w", encoding="utf-8") as fh:
            fh.write("not a real key; config never opens it\n")
        config._FROM_DOTENV.clear()
        self.addCleanup(config._FROM_DOTENV.clear)

    def env(self, **overrides):
        """Patch os.environ to a complete demo config plus overrides (None removes a key)."""
        values = {"DOCUSIGN_ENV_FILE": os.path.join(self.tmp.name, "absent.env"),
                  "DOCUSIGN_ENVIRONMENT": "demo",
                  "DOCUSIGN_INTEGRATION_KEY": "ik-synthetic-0000",
                  "DOCUSIGN_USER_ID": "user-synthetic-0000",
                  "DOCUSIGN_ACCOUNT_ID": "acct-synthetic",
                  "DOCUSIGN_PRIVATE_KEY_PATH": self.key}
        values.update(overrides)
        return patch.dict(os.environ, {k: v for k, v in values.items() if v is not None}, clear=True)

    def test_loads_a_complete_demo_config(self):
        with self.env():
            c = load_config()
        self.assertEqual((c.environment, c.label, c.auth_host),
                         ("demo", "SANDBOX", "account-d.docusign.com"))
        self.assertEqual(c.upload_roots, (config.runtime_root(),))
        self.assertEqual((c.enable_writes, c.enable_writes_source, c.timeout), (False, "default", 60.0))

    def test_missing_settings_are_named(self):
        with self.env(DOCUSIGN_INTEGRATION_KEY=None, DOCUSIGN_USER_ID=None):
            with self.assertRaises(ConfigError) as cm:
                load_config()
        self.assertIn("DOCUSIGN_INTEGRATION_KEY", str(cm.exception))
        self.assertIn("DOCUSIGN_USER_ID", str(cm.exception))

    def test_environment_must_be_demo_or_production(self):
        with self.env(DOCUSIGN_ENVIRONMENT="staging"):
            with self.assertRaisesRegex(ConfigError, "'demo' or 'production'"):
                load_config()

    def test_key_on_c_is_refused_without_echoing_the_path(self):
        for path in (r"C:\secretfolder-x1\docusign.pem", "c:/secretfolder-x1/docusign.pem",
                     r"\\?\C:\secretfolder-x1\docusign.pem"):
            with self.subTest(path=path), self.env(DOCUSIGN_PRIVATE_KEY_PATH=path):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("on C:", str(cm.exception))
                self.assertNotIn("secretfolder-x1", str(cm.exception))

    def test_key_must_be_absolute(self):
        with self.env(DOCUSIGN_PRIVATE_KEY_PATH="keys/docusign.pem"):
            with self.assertRaisesRegex(ConfigError, "absolute"):
                load_config()

    def test_key_inside_the_checkout_is_refused(self):
        inside = os.path.join(config.checkout_root(), "shared", "mcp", "docusign-upload", "key.pem")
        with self.env(DOCUSIGN_PRIVATE_KEY_PATH=inside):
            with self.assertRaisesRegex(ConfigError, "inside the repo checkout"):
                load_config()

    def test_key_file_must_exist(self):
        with self.env(DOCUSIGN_PRIVATE_KEY_PATH=os.path.join(self.tmp.name, "missing.pem")):
            with self.assertRaisesRegex(ConfigError, "does not point to a file"):
                load_config()

    def test_demo_refuses_roots_outside_runtime(self):
        with self.env(DOCUSIGN_UPLOAD_ROOTS=self.tmp.name):
            with self.assertRaisesRegex(ConfigError, "synthetic jobs"):
                load_config()

    def test_demo_accepts_a_folder_inside_runtime(self):
        sub = os.path.join(config.runtime_root(), "contract-admin", "outputs")
        with self.env(DOCUSIGN_UPLOAD_ROOTS=sub):
            self.assertEqual(load_config().upload_roots, (sub,))

    def test_production_needs_roots_and_refuses_c(self):
        with self.env(DOCUSIGN_ENVIRONMENT="production"):
            with self.assertRaisesRegex(ConfigError, "required in production"):
                load_config()
        with self.env(DOCUSIGN_ENVIRONMENT="production", DOCUSIGN_UPLOAD_ROOTS=r"C:\PROJECTS"):
            with self.assertRaisesRegex(ConfigError, "C:"):
                load_config()
        with self.env(DOCUSIGN_ENVIRONMENT="production", DOCUSIGN_UPLOAD_ROOTS=self.tmp.name):
            c = load_config()
        self.assertEqual((c.label, c.auth_host, c.upload_roots),
                         ("PRODUCTION", "account.docusign.com", (self.tmp.name,)))

    def test_real_environment_beats_dotenv_and_the_source_is_reported(self):
        dotenv = os.path.join(self.tmp.name, "server.env")
        with open(dotenv, "w", encoding="utf-8") as fh:
            fh.write("DOCUSIGN_ENABLE_WRITES=true\nDOCUSIGN_TIMEOUT=7\n")
        with self.env(DOCUSIGN_ENV_FILE=dotenv):
            c = load_config()
        self.assertEqual((c.enable_writes, c.enable_writes_source, c.timeout), (True, "dotenv", 7.0))
        config._FROM_DOTENV.clear()
        with self.env(DOCUSIGN_ENV_FILE=dotenv, DOCUSIGN_ENABLE_WRITES="false"):
            c = load_config()
        self.assertEqual((c.enable_writes, c.enable_writes_source), (False, "env"))

    def test_consent_url_is_encoded(self):
        with self.env(DOCUSIGN_CONSENT_REDIRECT_URI="https://example.com/after consent"):
            url = load_config().consent_url()
        self.assertTrue(url.startswith("https://account-d.docusign.com/oauth/auth?"))
        self.assertIn("scope=signature%20impersonation", url)
        self.assertIn("client_id=ik-synthetic-0000", url)
        self.assertIn("redirect_uri=https%3A%2F%2Fexample.com%2Fafter%20consent", url)
        with self.env():
            self.assertIsNone(load_config().consent_url())

    def test_redacted_view_hides_the_key_path_and_counts_roots(self):
        with self.env():
            view = load_config().redacted()
        self.assertNotIn(self.key, str(view))
        self.assertEqual((view["environment"], view["upload_roots"]), ("SANDBOX", 1))


class InsideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_spaces_and_brackets_in_folder_names(self):
        root = os.path.join(self.tmp.name, "PROJECTS", "REGION - SEQ")
        job = os.path.join(root, "26098 LOT 4 [STAGE 2]", "CONTRACT DOCUMENTATION")
        os.makedirs(job)
        self.assertTrue(config.is_inside(os.path.join(job, "BUILD CONTRACT_LOT 4.pdf"), root))
        self.assertFalse(config.is_inside(root, root))
        sibling = os.path.join(self.tmp.name, "PROJECTS", "REGION - SEQX", "a.pdf")
        self.assertFalse(config.is_inside(sibling, root))

    def test_a_link_out_of_the_root_is_outside(self):
        root = os.path.join(self.tmp.name, "root")
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(root)
        os.makedirs(outside)
        link = os.path.join(root, "link")
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks need extra rights on this machine")
        self.assertFalse(config.is_inside(os.path.join(link, "a.pdf"), root))

    def test_windows_drive(self):
        self.assertEqual(config.windows_drive(r"C:\x"), "c:")
        self.assertEqual(config.windows_drive("z:/x"), "z:")
        self.assertEqual(config.windows_drive(r"\\?\C:\x"), "c:")
        self.assertEqual(config.windows_drive("/Users/x"), "")
