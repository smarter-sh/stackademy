"""
Validate every Smarter manifest in this repository on a Smarter platform, with the Smarter Python SDK.

Each manifest is sent to the platform's ``/api/v1/cli/validate/`` endpoint, which checks it against the model
of its kind, as ``apply`` does first, without applying anything. There is one test per manifest.

The manifests are found as a platform finds them when it loads this repository: every ``*.yaml``, ``*.yml`` and
``*.yaml.tpl`` file whose ``apiVersion`` starts with ``smarter.sh/``, outside hidden folders, ``scripts/``,
``tests/`` and ``venv/``. Templates are filled in with the scheme and host of the platform that validates them.

Run it with ``make test``, or ``venv/bin/python -m unittest discover -s tests -v``. It needs:

- ``SMARTER_API_KEY``: a Smarter api key;
- optionally ``SMARTER_ENVIRONMENT`` (local, alpha, beta, next or prod) or ``SMARTER_BASE_URL``
  (e.g. http://localhost:9357), to choose the platform. Otherwise the SDK reads ``~/.smarter/config.yaml``.
"""

import os
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from smarter import Smarter, SmarterError

ROOT = Path(__file__).resolve().parent.parent
SKIPPED_FOLDERS = {"scripts", "tests", "venv"}
MANIFEST_SUFFIXES = (".yaml", ".yml", ".yaml.tpl")
API_VERSION = re.compile(r"""^apiVersion:\s*["']?smarter\.sh/""", re.MULTILINE)


def find_manifests() -> list[Path]:
    """
    The repository's Smarter manifests, as a platform finds them.

    :returns: Their paths, sorted.
    """
    manifests = []
    for path in sorted(ROOT.rglob("*")):
        parts = path.relative_to(ROOT).parts
        if parts[0] in SKIPPED_FOLDERS or any(part.startswith(".") for part in parts):
            continue
        if path.is_file() and path.name.endswith(MANIFEST_SUFFIXES):
            if API_VERSION.search(path.read_text(encoding="utf-8")):
                manifests.append(path)
    return manifests


def fill_template(text: str, base_url: str) -> str:
    """
    Fill in a manifest template's variables, as a platform does when it loads this repository.

    :param text: The template.
    :param base_url: The platform's api url, whose scheme and host fill in the template.
    :returns: The manifest.
    """
    url = urlsplit(base_url)
    return text.replace("${environment_platform_scheme}", url.scheme).replace(
        "${environment_platform_domain}", url.netloc
    )


class TestManifests(unittest.TestCase):
    """One test per manifest, added by :func:`add_tests`."""

    client: Smarter

    @classmethod
    def setUpClass(cls):
        """Connect to the platform with the api key in ``SMARTER_API_KEY``."""
        if not os.environ.get("SMARTER_API_KEY", "").strip():
            raise RuntimeError("SMARTER_API_KEY is not set: export a Smarter api key, e.g. export SMARTER_API_KEY=...")
        cls.client = Smarter()

    def assert_valid(self, path: Path):
        """
        Validate one manifest on the platform.

        :param path: The manifest's path.
        """
        text = path.read_text(encoding="utf-8")
        if path.name.endswith(".tpl"):
            text = fill_template(text, self.client.base_url)
        try:
            result = self.client.manifests.validate(text)
        except SmarterError as e:
            self.fail(f"{path.relative_to(ROOT)}: {e}")
        self.assertTrue(result.valid, f"{path.relative_to(ROOT)}: {result.errors}")


def add_tests():
    """Add a test to :class:`TestManifests` for each manifest, named after its path."""
    for path in find_manifests():
        name = "test_" + re.sub(r"\W", "_", str(path.relative_to(ROOT)))
        setattr(TestManifests, name, lambda self, path=path: self.assert_valid(path))


add_tests()


class TestFindManifests(unittest.TestCase):
    """The repository has manifests to validate."""

    def test_finds_manifests(self):
        """A change to the folders or the search must not leave nothing to validate."""
        self.assertTrue(find_manifests(), "No manifests found.")


if __name__ == "__main__":
    unittest.main()
