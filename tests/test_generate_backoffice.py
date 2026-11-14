"""
Test ``scripts/generate_backoffice.py``, the generator of Stackademy's back office.

These tests need no Smarter platform and no database: they build the back office in memory, and write it into a
temporary folder. Run them with ``make test``, or on their own with
``venv/bin/python -m unittest tests.test_generate_backoffice -v``.
"""

import contextlib
import datetime
import importlib.util
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "generate_backoffice.py"


def load_generator():
    """
    Import the generator from its file: ``scripts/`` is not a package.

    :returns: The module.
    """
    spec = importlib.util.spec_from_file_location("generate_backoffice", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = load_generator()


class TestHelpers(unittest.TestCase):
    """The generator's small helpers."""

    def test_money(self):
        """Cents become dollars and cents, without floating point, negative amounts included."""
        self.assertEqual(generator.money(123456), "1234.56")
        self.assertEqual(generator.money(5), "0.05")
        self.assertEqual(generator.money(-250), "-2.50")
        self.assertEqual(generator.Money(100).text, "1.00")

    def test_sql_value(self):
        """Each kind of Python value becomes its SQL literal, with quotes and backslashes escaped."""
        self.assertEqual(generator.sql_value(None), "NULL")
        self.assertEqual(generator.sql_value(True), "1")
        self.assertEqual(generator.sql_value(False), "0")
        self.assertEqual(generator.sql_value(42), "42")
        self.assertEqual(generator.sql_value(generator.Money(1999)), "19.99")
        self.assertEqual(generator.sql_value(datetime.date(2025, 3, 1)), "'2025-03-01'")
        self.assertEqual(generator.sql_value("O'Brien \\ co"), "'O''Brien \\\\ co'")

    def test_month_end(self):
        """The last day of a month, December and February included."""
        self.assertEqual(generator.month_end(2025, 2), datetime.date(2025, 2, 28))
        self.assertEqual(generator.month_end(2025, 12), datetime.date(2025, 12, 31))

    def test_day_of_year(self):
        """A random day stays within its range, both ends included."""
        rng = random.Random(1)
        start = datetime.date(2025, 1, 1)
        end = datetime.date(2025, 1, 3)
        days = {generator.day_of_year(rng, start, end) for _ in range(100)}
        self.assertEqual(days, {start, datetime.date(2025, 1, 2), end})

    def test_read_courses(self):
        """The catalogue has its 48 courses, each with a code and a price."""
        courses = generator.read_courses()
        self.assertEqual(len(courses), 48)
        for _, code, name, cost in courses:
            self.assertTrue(code.startswith("CS"))
            self.assertTrue(name)
            self.assertGreater(cost, 0)

    def test_read_courses_refuses_a_short_catalogue(self):
        """A catalogue that lacks courses stops the generator, rather than generating a partial back office."""
        with tempfile.TemporaryDirectory() as folder:
            catalogue = Path(folder) / "stackademy.sql"
            catalogue.write_text("-- no courses\n", encoding="utf-8")
            with mock.patch.object(generator, "CATALOGUE_SQL", catalogue):
                with self.assertRaises(SystemExit):
                    generator.read_courses()


class TestBackoffice(unittest.TestCase):
    """The back office that the generator builds."""

    @classmethod
    def setUpClass(cls):
        cls.backoffice = generator.Backoffice()
        cls.backoffice.build()

    def test_every_table_is_built(self):
        """Every table in TABLE_ORDER is built, and has rows."""
        self.assertEqual(set(self.backoffice.tables), set(generator.TABLE_ORDER))
        for name in generator.TABLE_ORDER:
            self.assertTrue(self.backoffice.tables[name].rows, name)

    def test_is_the_same_every_time(self):
        """A second build gives the same SQL: the demonstrations' answers don't change from run to run."""
        second = generator.Backoffice()
        second.build()
        self.assertEqual(generator.render_sql(second), generator.render_sql(self.backoffice))

    def test_ledger_balances(self):
        """The general ledger's debits equal its credits."""
        debits = sum(line[6].cents for line in self.backoffice.gl_lines)
        credits = sum(line[7].cents for line in self.backoffice.gl_lines)
        self.assertGreater(debits, 0)
        self.assertEqual(debits, credits)

    def test_unbalanced_journal_entry_is_refused(self):
        """A journal entry whose debits differ from its credits is an error in the generator, and stops it."""
        backoffice = generator.Backoffice()
        with self.assertRaises(ValueError):
            backoffice.journal(datetime.date(2025, 1, 1), "unbalanced", "test", [("1000", None, 100, 0)])

    def test_grants_name_real_tables(self):
        """Each department user is granted only tables that exist."""
        known = set(generator.TABLE_ORDER) | set(generator.CATALOGUE_TABLES) | set(generator.BOARD_VIEWS)
        for user, tables in generator.GRANTS.items():
            self.assertTrue(set(tables) <= known, user)

    def test_hr_tables_are_kept_from_other_departments(self):
        """Salaries are HR's alone: no other department user may read compensation."""
        for user, tables in generator.GRANTS.items():
            if user != "stackademy_hr":
                self.assertNotIn("compensation", tables, user)

    def test_executives_read_only_the_board_views(self):
        """The executives' user reads the Board Pack's views, which hold totals, and none of the tables beneath them."""
        self.assertEqual(generator.GRANTS["stackademy_executive"], list(generator.BOARD_VIEWS))
        sql = generator.render_sql(self.backoffice)
        for name in generator.BOARD_VIEWS:
            self.assertIn(f"CREATE OR REPLACE SQL SECURITY DEFINER VIEW `{name}` AS", sql)
            self.assertNotIn(name, generator.TABLE_ORDER)

    def test_sql_grants_each_user_its_tables(self):
        """The SQL creates each department user and grants it each of its tables."""
        sql = generator.render_sql(self.backoffice)
        for user, tables in generator.GRANTS.items():
            self.assertIn(f"CREATE USER IF NOT EXISTS '{user}'@'%'", sql)
            for table in tables:
                self.assertIn(f"GRANT SELECT ON `{generator.DATABASE}`.`{table}` TO '{user}'@'%';", sql)

    def test_grants_file_lists_each_user(self):
        """backoffice-grants.txt has one line per user, with its tables, sorted."""
        lines = [line for line in generator.render_grants().splitlines() if not line.startswith("#")]
        self.assertEqual(len(lines), len(generator.GRANTS))
        for line in lines:
            user, *tables = line.split()
            self.assertEqual(tables, sorted(generator.GRANTS[user]))

    def test_users_are_demonstration_users(self):
        """Each User manifest signs in with the demonstration password, and is neither staff nor superuser."""
        users = generator.render_users(self.backoffice)
        self.assertEqual(len(users), len(generator.LOGINS))
        for path, text in users.items():
            self.assertEqual(path.parent, generator.USERS_DIR)
            self.assertIn("kind: User", text)
            self.assertIn("passwordSecret:", text)
            self.assertNotIn("isSuperuser: true", text)
            self.assertNotIn("isStaff: true", text)

    def test_owners_names_each_department_account(self):
        """owners.yaml gives every department's folder an owner in that department's account."""
        owners = generator.render_owners(self.backoffice)
        for account_number in generator.ACCOUNT_NUMBERS.values():
            if account_number == generator.ACCOUNT_NUMBERS.get("CORP"):
                continue
            self.assertIn(f'accountNumber: "{account_number}"', owners)


class TestMain(unittest.TestCase):
    """The command line: writing the files, and --check."""

    def test_committed_files_are_up_to_date(self):
        """The files in the repository are what the generator makes, as the Checks workflow requires."""
        self.assertEqual(self.run_main("--check"), 0)

    def test_write_then_check(self):
        """Writing creates every file, removes a stale User manifest, and --check then passes."""
        with tempfile.TemporaryDirectory() as folder:
            with self.redirected(Path(folder)) as users_dir:
                users_dir.mkdir()
                stale = users_dir / "nobody.yaml"
                stale.write_text("stale\n", encoding="utf-8")

                self.assertEqual(self.run_main("--check"), 1)
                self.assertTrue(stale.exists(), "--check must not change anything")

                self.assertEqual(self.run_main(), 0)
                self.assertFalse(stale.exists())
                self.assertEqual(len(list(users_dir.glob("*.yaml"))), len(generator.LOGINS))
                self.assertTrue((Path(folder) / "backoffice.sql").exists())

                self.assertEqual(self.run_main("--check"), 0)

    def test_check_finds_a_changed_file(self):
        """--check fails when a generated file was edited by hand."""
        with tempfile.TemporaryDirectory() as folder:
            with self.redirected(Path(folder)):
                self.assertEqual(self.run_main(), 0)
                grants = Path(folder) / "backoffice-grants.txt"
                grants.write_text(grants.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
                self.assertEqual(self.run_main("--check"), 1)

    @contextlib.contextmanager
    def redirected(self, folder: Path):
        """
        Point every file that the generator writes into a temporary folder.

        :param folder: The temporary folder.
        :returns: The folder that holds the User manifests.
        """
        users_dir = folder / "users"
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(generator, "BACKOFFICE_SQL", folder / "backoffice.sql"))
            stack.enter_context(mock.patch.object(generator, "GRANTS_TXT", folder / "backoffice-grants.txt"))
            stack.enter_context(mock.patch.object(generator, "OWNERS_YAML", folder / "owners.yaml"))
            stack.enter_context(mock.patch.object(generator, "USERS_DIR", users_dir))
            yield users_dir

    def run_main(self, *arguments: str) -> int:
        """
        Run the generator's command line, quietly.

        :param arguments: Its arguments, e.g. --check.
        :returns: Its exit code.
        """
        argv = [str(SCRIPT), *arguments]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            return generator.main()


if __name__ == "__main__":
    unittest.main()
