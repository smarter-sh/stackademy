#!/usr/bin/env python3
"""
Generate Stackademy's back office: the tables of its HR, Admissions, Accounting and Course Content departments.

Stackademy's course catalogue, in ``stackademy.sql``, is what students see. Its back office is what its employees
work with, and what the department assistants in this repository answer from: who works where and for how much,
who enrolled and paid, what the company spent, and which lessons are still being made. This script writes it as
``backoffice.sql``, which ``create-course-database.sh`` loads after ``stackademy.sql``, and the read-only database
user of each department, with the tables that it may read, as ``backoffice-grants.txt``, which the same script
checks.

Everything is fictional, and generated, not typed. It covers one fiscal year, 2025, and is the same every time:
the random numbers come from a fixed seed, so a question such as "What was the tuition revenue in Q3?" has the same
answer for as long as the data is unchanged, and the repository's demonstrations can rely on it. Run it after
changing it, and commit both files:

.. code-block:: console

    python3 scripts/generate_backoffice.py            # write backoffice.sql and backoffice-grants.txt
    python3 scripts/generate_backoffice.py --check    # fail if either is out of date, as the checks do

It uses only Python's standard library.
"""

import argparse
import datetime
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOGUE_SQL = HERE / "stackademy.sql"
BACKOFFICE_SQL = HERE / "backoffice.sql"
GRANTS_TXT = HERE / "backoffice-grants.txt"

DATABASE = "stackademy"
SEED = 20250101
FISCAL_YEAR = 2025
AS_OF = datetime.date(2025, 12, 31)
"""The day on which the data stands: everything after it is in the future."""
EMAIL_DOMAIN = "stackademy.example"
"""A domain reserved for examples (RFC 2606), so that no address in the data can reach anyone."""

# -----------------------------------------------------------------------------------------------------------------
# Who may read what. Each department's assistant connects as its own read-only user, whose password is its name,
# and may read only its department's tables, so that the database itself keeps, e.g., salaries from Accounting.
# -----------------------------------------------------------------------------------------------------------------
CATALOGUE_TABLES = ["courses", "cohorts", "course_modules", "lessons"]
GRANTS: dict[str, list[str]] = {
    "stackademy_catalog": CATALOGUE_TABLES,
    "stackademy_catalog_proxy": CATALOGUE_TABLES,
    "stackademy_hr": ["departments", "employees", "compensation", "pto_balances", "pto_requests", "job_requisitions"],
    "stackademy_admissions": [
        "courses",
        "cohorts",
        "corporate_contracts",
        "students",
        "enrollments",
        "promo_codes",
        "payments",
        "refunds",
    ],
    "stackademy_accounting": [
        "departments",
        "employees",
        "courses",
        "cohorts",
        "enrollments",
        "payments",
        "refunds",
        "chart_of_accounts",
        "corporate_contracts",
        "ar_invoices",
        "vendors",
        "ap_invoices",
        "gl_entries",
        "department_budgets",
        "expense_reports",
    ],
    "stackademy_content": [
        "departments",
        "employees",
        "vendors",
        "courses",
        "course_modules",
        "lessons",
        "assets",
        "production_tasks",
    ],
}

DEPARTMENTS = [
    ("EXEC", "Executive Office"),
    ("IT", "Information Technology"),
    ("HR", "Human Resources"),
    ("FIN", "Finance and Accounting"),
    ("CONT", "Course Content"),
    ("ADM", "Admissions and Sales"),
    ("INST", "Instruction"),
]

# (department, title, pay band, annual salary in dollars), each a position that one employee holds. The first of
# each department is its head, who reports to the chief executive; the others report to their department's head.
POSITIONS = [
    ("EXEC", "Chief Executive Officer", "F", 240000),
    ("EXEC", "Executive Assistant", "B", 62000),
    ("IT", "Head of IT", "E", 165000),
    ("IT", "Platform Engineer", "D", 128000),
    ("IT", "Platform Engineer", "D", 121000),
    ("IT", "IT Support Specialist", "B", 64000),
    ("HR", "HR Director", "E", 142000),
    ("HR", "HR Business Partner", "C", 88000),
    ("HR", "Recruiter", "C", 79000),
    ("FIN", "Chief Financial Officer", "F", 205000),
    ("FIN", "Controller", "D", 126000),
    ("FIN", "Staff Accountant", "C", 74000),
    ("FIN", "Accounts Payable Specialist", "B", 59000),
    ("CONT", "Head of Course Content", "E", 148000),
    ("CONT", "Instructional Designer", "C", 86000),
    ("CONT", "Instructional Designer", "C", 82000),
    ("CONT", "Instructional Designer", "C", 79000),
    ("CONT", "Video Producer", "C", 81000),
    ("CONT", "Illustrator", "C", 72000),
    ("CONT", "Content Editor", "B", 66000),
    ("ADM", "Admissions Director", "E", 138000),
    ("ADM", "Admissions Advisor", "B", 58000),
    ("ADM", "Admissions Advisor", "B", 56000),
    ("ADM", "Admissions Advisor", "B", 57000),
    ("ADM", "Marketing Manager", "C", 92000),
    ("INST", "Dean of Instruction", "E", 152000),
]
INSTRUCTORS = 14
"""Instructors, in Instruction, besides its dean."""

FIRST_NAMES = [
    "Avery", "Blake", "Camila", "Dario", "Elena", "Farid", "Greta", "Hiro", "Imani", "Jonas", "Keira", "Liam",
    "Mira", "Nikhil", "Odette", "Pavel", "Quinn", "Rosa", "Soren", "Talia", "Umar", "Vera", "Wes", "Ximena",
    "Yusuf", "Zara", "Anya", "Bruno", "Cleo", "Dmitri", "Esme", "Felix", "Gwen", "Hamid", "Ingrid", "Jude",
    "Kofi", "Lena", "Marco", "Noor", "Oskar", "Priya", "Rafael", "Sienna", "Tomas", "Uma", "Viktor", "Wren",
]  # fmt: skip
LAST_NAMES = [
    "Abernathy", "Bellamy", "Castellanos", "Dumont", "Eriksen", "Fairbanks", "Galloway", "Hartigan",
    "Ivanova", "Jaramillo", "Kowalczyk", "Lindqvist", "Marchetti", "Nakashima", "Okonkwo", "Pemberton",
    "Quintero", "Ravensworth", "Sandoval", "Thornbury", "Underhill", "Valcourt", "Whitlock", "Yamamura",
]  # fmt: skip
COUNTRIES = ["US", "US", "US", "US", "CA", "CA", "GB", "GB", "IN", "DE", "FR", "BR", "MX", "AU", "NG", "PH"]

VENDORS = [
    # (name, category, payment terms in days, whether a freelancer who makes course content)
    ("Pixel Forge Studios", "Video production", 30, True),
    ("Lumen & Grain Animation", "Animation", 30, True),
    ("Rivera Illustration", "Illustration", 15, True),
    ("Kestrel Voice Works", "Narration", 15, True),
    ("Fernhill Captioning", "Transcription", 15, True),
    ("Northwind Editing Co.", "Video editing", 30, True),
    ("Nimbus Cloud Hosting", "Cloud hosting", 30, False),
    ("Cortex AI Services", "AI services", 30, False),
    ("Beacon Ads Network", "Advertising", 45, False),
    ("Ledgerline Payroll", "Payroll services", 15, False),
    ("Harbor Office Supply", "Office supplies", 30, False),
    ("Summit Legal LLP", "Legal services", 30, False),
]

CHART_OF_ACCOUNTS = [
    ("1000", "Cash", "asset"),
    ("1100", "Accounts Receivable", "asset"),
    ("2000", "Accounts Payable", "liability"),
    ("3000", "Owner's Equity", "equity"),
    ("4000", "Tuition Revenue", "revenue"),
    ("4100", "Tuition Refunds", "revenue"),
    ("4200", "Corporate Training Revenue", "revenue"),
    ("5000", "Salaries and Wages", "expense"),
    ("5100", "Contractor Services", "expense"),
    ("5200", "Cloud Hosting and Software", "expense"),
    ("5300", "AI Services", "expense"),
    ("5400", "Marketing and Advertising", "expense"),
    ("5500", "Travel and Employee Expenses", "expense"),
    ("5600", "Office and Facilities", "expense"),
    ("5700", "Professional Services", "expense"),
]

# (vendor, expense account, department, monthly amount in dollars), recurring every month of the year.
RECURRING_INVOICES = [
    ("Nimbus Cloud Hosting", "5200", "IT", 7800),
    ("Cortex AI Services", "5300", "IT", 2400),
    ("Beacon Ads Network", "5400", "ADM", 11500),
    ("Ledgerline Payroll", "5700", "FIN", 900),
    ("Harbor Office Supply", "5600", "EXEC", 650),
]

CORPORATE_CLIENTS = [
    # (client, seats, annual contract value in dollars, first month billed). Every company is fictional.
    ("Halverson Logistics", 120, 610000, 1),
    ("Brightwater Health", 90, 510000, 1),
    ("Quarry Lane Bank", 150, 745000, 2),
    ("Tidewell Energy", 60, 340000, 1),
    ("Orchard Peak Retail", 80, 405000, 3),
    ("Copperline Telecom", 110, 560000, 1),
    ("Meridian Insurance Group", 70, 380000, 4),
    ("Northgate Public Schools", 140, 475000, 1),
    ("Sablewood Manufacturing", 50, 270000, 6),
]

PROMO_CODES = [("EARLYBIRD", 15), ("ALUMNI", 20), ("SPRING25", 10), ("TEAM5", 25)]
EXPENSE_CATEGORIES = [("Travel", 300, 1400), ("Meals", 40, 220), ("Conference", 400, 1800), ("Software", 20, 300)]
MODULE_TITLES = ["Foundations", "Core Concepts", "Applied Techniques", "Case Studies", "Capstone Exercise"]
ASSET_TYPES = ["video", "transcript", "artwork"]
TASK_TYPE = {"video": "edit video", "transcript": "transcribe", "artwork": "illustrate"}
FREELANCERS_BY_ASSET = {
    "video": ["Pixel Forge Studios", "Northwind Editing Co.", "Lumen & Grain Animation"],
    "transcript": ["Fernhill Captioning", "Kestrel Voice Works"],
    "artwork": ["Rivera Illustration", "Lumen & Grain Animation"],
}
IN_PRODUCTION_COURSES = ["CS303", "CS309", "CS312", "CS405", "CS406"]
"""Courses whose lessons are still being made: the Course Content team's work in progress."""


@dataclass
class Table:
    """One table: its definition, and its rows, in order."""

    name: str
    ddl: str
    rows: list[tuple] = field(default_factory=list)


def money(cents: int) -> str:
    """Dollars and cents, e.g. 123456 -> 1234.56, without floating point."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def sql_value(value) -> str:
    """A Python value as a SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, Money):
        return value.text
    if isinstance(value, datetime.date):
        return f"'{value.isoformat()}'"
    text = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{text}'"


@dataclass(frozen=True)
class Money:
    """An amount in cents, written as dollars and cents."""

    cents: int

    @property
    def text(self) -> str:
        return money(self.cents)


def read_courses() -> list[tuple[int, str, str, int]]:
    """
    The courses of the catalogue, from ``stackademy.sql``: its single source.

    :returns: (course_id, course_code, course_name, cost in cents) for each course.
    """
    sql = CATALOGUE_SQL.read_text(encoding="utf-8")
    pattern = re.compile(r"\((\d+),'(CS\d+)','((?:[^']|'')*)','(?:[^']|'')*',(\d+)\.(\d{2}),(?:NULL|\d+)\)")
    courses = []
    for match in pattern.finditer(sql):
        cost_cents = int(match.group(4)) * 100 + int(match.group(5))
        courses.append((int(match.group(1)), match.group(2), match.group(3).replace("''", "'"), cost_cents))
    if len(courses) != 48:
        raise SystemExit(f"expected 48 courses in {CATALOGUE_SQL.name}, found {len(courses)}")
    return courses


def day_of_year(rng: random.Random, start: datetime.date, end: datetime.date) -> datetime.date:
    """A random day from start to end, inclusive."""
    span = (end - start).days
    return start + datetime.timedelta(days=rng.randint(0, span))


def month_end(year: int, month: int) -> datetime.date:
    """The last day of the month."""
    if month == 12:
        return datetime.date(year, 12, 31)
    return datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)


class Backoffice:
    """Builds every table of the back office, with one random number generator, in a fixed order."""

    def __init__(self):
        self.rng = random.Random(SEED)
        self.courses = read_courses()
        self.course_by_code = {code: (course_id, name, cost) for course_id, code, name, cost in self.courses}
        self.tables: dict[str, Table] = {}
        self.gl_lines: list[tuple] = []
        self.journal_id = 0
        self.names_used: set[tuple[str, str]] = set()

    def table(self, name: str, ddl: str) -> Table:
        """Start a table."""
        table = Table(name=name, ddl=ddl)
        self.tables[name] = table
        return table

    def unique_name(self) -> tuple[str, str]:
        """A first and last name that no one else in the data has."""
        while True:
            name = (self.rng.choice(FIRST_NAMES), self.rng.choice(LAST_NAMES))
            if name not in self.names_used:
                self.names_used.add(name)
                return name

    def journal(self, entry_date: datetime.date, description: str, source: str, lines: list[tuple]) -> None:
        """
        One balanced journal entry in the general ledger.

        :param lines: (gl_account, department code or None, debit cents, credit cents), whose debits equal its
            credits.
        """
        debits = sum(line[2] for line in lines)
        credits = sum(line[3] for line in lines)
        if debits != credits:
            raise ValueError(f"unbalanced journal entry {description}: {debits} != {credits}")
        self.journal_id += 1
        for account, department_code, debit, credit in lines:
            department_id = self.department_ids[department_code] if department_code else None
            self.gl_lines.append(
                (self.journal_id, entry_date, account, department_id, description, source, Money(debit), Money(credit))
            )

    # ------------------------------------------------------------------------------------------------------------
    # The shared directory, and HR
    # ------------------------------------------------------------------------------------------------------------
    def build_people(self) -> None:
        departments = self.table(
            "departments",
            "  `department_id` int NOT NULL,\n  `code` varchar(8) NOT NULL,\n  `name` varchar(64) NOT NULL,\n"
            "  `head_employee_id` int DEFAULT NULL,\n  PRIMARY KEY (`department_id`),\n  UNIQUE KEY `code` (`code`)",
        )
        self.department_ids = {}
        for department_id, (code, name) in enumerate(DEPARTMENTS, start=1):
            self.department_ids[code] = department_id

        positions = list(POSITIONS)
        for _ in range(INSTRUCTORS):
            positions.append(("INST", "Instructor", "C", self.rng.randint(78, 96) * 1000))

        employees = self.table(
            "employees",
            "  `employee_id` int NOT NULL,\n  `employee_number` varchar(8) NOT NULL,\n"
            "  `first_name` varchar(32) NOT NULL,\n  `last_name` varchar(32) NOT NULL,\n  `email` varchar(96) NOT NULL,\n"
            "  `department_id` int NOT NULL,\n  `title` varchar(64) NOT NULL,\n  `manager_id` int DEFAULT NULL,\n"
            "  `hire_date` date NOT NULL,\n  `employment_type` varchar(16) NOT NULL,\n  `location` varchar(32) NOT NULL,\n"
            "  PRIMARY KEY (`employee_id`),\n  UNIQUE KEY `employee_number` (`employee_number`),\n"
            "  UNIQUE KEY `email` (`email`),\n  KEY `department_id` (`department_id`)",
        )
        compensation = self.table(
            "compensation",
            "  `employee_id` int NOT NULL,\n  `effective_date` date NOT NULL,\n  `annual_salary` decimal(10,2) NOT NULL,\n"
            "  `currency` char(3) NOT NULL,\n  `pay_band` char(1) NOT NULL,\n  `bonus_target_percent` int NOT NULL,\n"
            "  PRIMARY KEY (`employee_id`, `effective_date`)",
        )
        self.employees: list[dict] = []
        heads: dict[str, int] = {}
        for employee_id, (department_code, title, band, salary) in enumerate(positions, start=1):
            first, last = self.unique_name()
            hire_date = day_of_year(self.rng, datetime.date(2017, 1, 1), datetime.date(2025, 9, 30))
            if employee_id == 1:
                hire_date = datetime.date(2016, 3, 1)
            if department_code not in heads:
                heads[department_code] = employee_id
                manager_id = None if department_code == "EXEC" else 1
            else:
                manager_id = heads[department_code]
            employment_type = "part_time" if title == "Instructor" and self.rng.random() < 0.4 else "full_time"
            location = self.rng.choice(["Remote", "Remote", "Remote", "Austin", "Toronto", "London"])
            employee = {
                "id": employee_id,
                "first": first,
                "last": last,
                "department": department_code,
                "title": title,
                "salary_cents": salary * 100,
                "hire_date": hire_date,
            }
            self.employees.append(employee)
            email = f"{first.lower()}.{last.lower()}@{EMAIL_DOMAIN}"
            employees.rows.append(
                (
                    employee_id,
                    f"E{employee_id:04d}",
                    first,
                    last,
                    email,
                    self.department_ids[department_code],
                    title,
                    manager_id,
                    hire_date,
                    employment_type,
                    location,
                )
            )
            raise_date = datetime.date(FISCAL_YEAR, 1, 1)
            previous_salary = int(salary * 100 / (1 + self.rng.choice([0.03, 0.04, 0.05])) / 100) * 100
            if hire_date < raise_date:
                previous_date = max(hire_date, datetime.date(2024, 1, 1))
                compensation.rows.append((employee_id, previous_date, Money(previous_salary), "USD", band, 5))
            bonus = {"F": 30, "E": 20, "D": 10}.get(band, 5)
            effective = raise_date if hire_date < raise_date else hire_date
            compensation.rows.append((employee_id, effective, Money(salary * 100), "USD", band, bonus))
        for department_id, (code, name) in enumerate(DEPARTMENTS, start=1):
            departments.rows.append((department_id, code, name, heads[code]))
        self.instructor_ids = [e["id"] for e in self.employees if e["title"] == "Instructor"]

        pto_balances = self.table(
            "pto_balances",
            "  `employee_id` int NOT NULL,\n  `year` int NOT NULL,\n  `accrued_days` decimal(5,1) NOT NULL,\n"
            "  `used_days` decimal(5,1) NOT NULL,\n  `carried_over_days` decimal(5,1) NOT NULL,\n"
            "  PRIMARY KEY (`employee_id`, `year`)",
        )
        pto_requests = self.table(
            "pto_requests",
            "  `request_id` int NOT NULL,\n  `employee_id` int NOT NULL,\n  `start_date` date NOT NULL,\n"
            "  `end_date` date NOT NULL,\n  `days` int NOT NULL,\n  `kind` varchar(16) NOT NULL,\n"
            "  `status` varchar(16) NOT NULL,\n  `approver_id` int DEFAULT NULL,\n  PRIMARY KEY (`request_id`),\n"
            "  KEY `employee_id` (`employee_id`)",
        )
        manager_of = {row[0]: row[7] for row in employees.rows}
        request_id = 0
        for employee in self.employees:
            accrued = 20.0
            if employee["hire_date"].year == FISCAL_YEAR:
                accrued = round(20 * (12 - employee["hire_date"].month + 1) / 12 * 2) / 2
            used = 0
            for _ in range(self.rng.randint(1, 4)):
                start = day_of_year(self.rng, max(employee["hire_date"], datetime.date(2025, 1, 6)), AS_OF)
                if start.weekday() >= 5:
                    start += datetime.timedelta(days=7 - start.weekday())
                days = self.rng.choice([1, 1, 2, 3, 5])
                end = start + datetime.timedelta(days=days - 1)
                status = "approved"
                if start > datetime.date(2025, 12, 15):
                    status = "pending"
                elif self.rng.random() < 0.06:
                    status = "denied"
                kind = "vacation" if self.rng.random() < 0.8 else "sick"
                if status == "approved" and used + days <= accrued:
                    used += days
                elif status == "approved":
                    status = "denied"
                request_id += 1
                approver = manager_of[employee["id"]] if status != "pending" else None
                pto_requests.rows.append((request_id, employee["id"], start, end, days, kind, status, approver))
            carried = float(self.rng.choice([0, 0, 1, 2, 3, 5]))
            pto_balances.rows.append((employee["id"], FISCAL_YEAR, accrued, float(used), carried))

        job_requisitions = self.table(
            "job_requisitions",
            "  `requisition_id` int NOT NULL,\n  `department_id` int NOT NULL,\n  `title` varchar(64) NOT NULL,\n"
            "  `hiring_manager_id` int NOT NULL,\n  `opened_on` date NOT NULL,\n  `closed_on` date DEFAULT NULL,\n"
            "  `status` varchar(16) NOT NULL,\n  `salary_min` decimal(10,2) NOT NULL,\n  `salary_max` decimal(10,2) NOT NULL,\n"
            "  `applicants` int NOT NULL,\n  PRIMARY KEY (`requisition_id`)",
        )
        requisitions = [
            ("CONT", "Instructional Designer", "open", 78000, 92000),
            ("CONT", "Video Producer", "open", 76000, 90000),
            ("INST", "Instructor, Machine Learning", "open", 82000, 98000),
            ("IT", "Platform Engineer", "filled", 115000, 135000),
            ("ADM", "Admissions Advisor", "filled", 52000, 60000),
            ("FIN", "Staff Accountant", "on_hold", 68000, 78000),
        ]
        for requisition_id, (code, title, status, low, high) in enumerate(requisitions, start=1):
            opened = day_of_year(self.rng, datetime.date(2025, 3, 1), datetime.date(2025, 11, 15))
            closed = None
            if status == "filled":
                closed = opened + datetime.timedelta(days=self.rng.randint(30, 60))
            job_requisitions.rows.append(
                (
                    requisition_id,
                    self.department_ids[code],
                    title,
                    heads[code],
                    opened,
                    closed,
                    status,
                    Money(low * 100),
                    Money(high * 100),
                    self.rng.randint(8, 70),
                )
            )

    # ------------------------------------------------------------------------------------------------------------
    # Admissions: students, cohorts, enrollments and what they paid
    # ------------------------------------------------------------------------------------------------------------
    def build_admissions(self) -> None:
        students = self.table(
            "students",
            "  `student_id` int NOT NULL,\n  `first_name` varchar(32) NOT NULL,\n  `last_name` varchar(32) NOT NULL,\n"
            "  `email` varchar(96) NOT NULL,\n  `country` char(2) NOT NULL,\n  `signup_date` date NOT NULL,\n"
            "  PRIMARY KEY (`student_id`),\n  UNIQUE KEY `email` (`email`)",
        )
        student_count = 320
        for student_id in range(1, student_count + 1):
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            email = f"student{student_id:04d}@learners.{EMAIL_DOMAIN}"
            signup = day_of_year(self.rng, datetime.date(2024, 6, 1), datetime.date(2025, 11, 30))
            students.rows.append((student_id, first, last, email, self.rng.choice(COUNTRIES), signup))
        signup_of = {row[0]: row[5] for row in students.rows}

        promo_codes = self.table(
            "promo_codes",
            "  `code` varchar(16) NOT NULL,\n  `percent_off` int NOT NULL,\n  `valid_from` date NOT NULL,\n"
            "  `valid_to` date NOT NULL,\n  PRIMARY KEY (`code`)",
        )
        for code, percent in PROMO_CODES:
            promo_codes.rows.append((code, percent, datetime.date(2025, 1, 1), datetime.date(2025, 12, 31)))

        cohorts = self.table(
            "cohorts",
            "  `cohort_id` int NOT NULL,\n  `course_id` int NOT NULL,\n  `start_date` date NOT NULL,\n"
            "  `end_date` date NOT NULL,\n  `instructor_id` int NOT NULL,\n  `delivery` varchar(16) NOT NULL,\n"
            "  `capacity` int NOT NULL,\n  PRIMARY KEY (`cohort_id`),\n  KEY `course_id` (`course_id`)",
        )
        cohort_id = 0
        cohort_list = []
        for course_id, code, _name, cost in self.courses:
            if code in IN_PRODUCTION_COURSES:
                continue
            for _ in range(self.rng.choice([0, 1, 1, 2])):
                start = day_of_year(self.rng, datetime.date(2025, 1, 6), datetime.date(2025, 11, 3))
                start -= datetime.timedelta(days=start.weekday())
                end = start + datetime.timedelta(weeks=self.rng.choice([6, 8, 10]))
                cohort_id += 1
                capacity = self.rng.choice([20, 24, 30])
                delivery = self.rng.choice(["online", "online", "live_online"])
                cohorts.rows.append(
                    (cohort_id, course_id, start, end, self.rng.choice(self.instructor_ids), delivery, capacity)
                )
                cohort_list.append((cohort_id, course_id, start, end, capacity, cost))

        enrollments = self.table(
            "enrollments",
            "  `enrollment_id` int NOT NULL,\n  `student_id` int NOT NULL,\n  `cohort_id` int NOT NULL,\n"
            "  `enrolled_on` date NOT NULL,\n  `list_price` decimal(8,2) NOT NULL,\n  `promo_code` varchar(16) DEFAULT NULL,\n"
            "  `price_paid` decimal(8,2) NOT NULL,\n  `status` varchar(16) NOT NULL,\n  PRIMARY KEY (`enrollment_id`),\n"
            "  KEY `student_id` (`student_id`),\n  KEY `cohort_id` (`cohort_id`)",
        )
        payments = self.table(
            "payments",
            "  `payment_id` int NOT NULL,\n  `enrollment_id` int NOT NULL,\n  `paid_on` date NOT NULL,\n"
            "  `amount` decimal(8,2) NOT NULL,\n  `method` varchar(16) NOT NULL,\n  PRIMARY KEY (`payment_id`)",
        )
        refunds = self.table(
            "refunds",
            "  `refund_id` int NOT NULL,\n  `payment_id` int NOT NULL,\n  `refunded_on` date NOT NULL,\n"
            "  `amount` decimal(8,2) NOT NULL,\n  `reason` varchar(64) NOT NULL,\n  PRIMARY KEY (`refund_id`)",
        )
        enrollment_id = 0
        refund_id = 0
        for cohort_id, _course_id, start, end, capacity, cost in cohort_list:
            seats = self.rng.randint(capacity // 3, capacity)
            for student_id in self.rng.sample(range(1, student_count + 1), seats):
                enrolled_on = max(signup_of[student_id], start - datetime.timedelta(days=self.rng.randint(3, 60)))
                if enrolled_on > start:
                    enrolled_on = start - datetime.timedelta(days=1)
                promo = None
                percent = 0
                if self.rng.random() < 0.25:
                    promo, percent = self.rng.choice(PROMO_CODES)
                paid_cents = cost * (100 - percent) // 100
                if end < AS_OF:
                    status = "completed"
                elif start <= AS_OF:
                    status = "active"
                else:
                    status = "enrolled"
                withdrawn = self.rng.random() < 0.06
                if withdrawn:
                    status = "withdrawn"
                enrollment_id += 1
                enrollments.rows.append(
                    (enrollment_id, student_id, cohort_id, enrolled_on, Money(cost), promo, Money(paid_cents), status)
                )
                method = self.rng.choice(["card", "card", "card", "paypal", "invoice"])
                payments.rows.append((enrollment_id, enrollment_id, enrolled_on, Money(paid_cents), method))
                self.journal(
                    enrolled_on,
                    f"Tuition, enrollment {enrollment_id}",
                    "payment",
                    [("1000", None, paid_cents, 0), ("4000", "ADM", 0, paid_cents)],
                )
                if withdrawn:
                    refund_id += 1
                    refunded_on = min(AS_OF, start + datetime.timedelta(days=self.rng.randint(1, 14)))
                    full = refunded_on <= start + datetime.timedelta(days=7)
                    refund_cents = paid_cents if full else paid_cents // 2
                    reason = "withdrew in the first week" if full else "withdrew after the first week"
                    refunds.rows.append((refund_id, enrollment_id, refunded_on, Money(refund_cents), reason))
                    self.journal(
                        refunded_on,
                        f"Refund, enrollment {enrollment_id}",
                        "refund",
                        [("4100", "ADM", refund_cents, 0), ("1000", None, 0, refund_cents)],
                    )

    # ------------------------------------------------------------------------------------------------------------
    # Corporate training: team licenses that companies buy, billed monthly, most of Stackademy's revenue
    # ------------------------------------------------------------------------------------------------------------
    def build_corporate(self) -> None:
        corporate_contracts = self.table(
            "corporate_contracts",
            "  `contract_id` int NOT NULL,\n  `client_name` varchar(64) NOT NULL,\n  `seats` int NOT NULL,\n"
            "  `annual_value` decimal(10,2) NOT NULL,\n  `start_date` date NOT NULL,\n  `end_date` date NOT NULL,\n"
            "  `account_manager_id` int NOT NULL,\n  PRIMARY KEY (`contract_id`)",
        )
        ar_invoices = self.table(
            "ar_invoices",
            "  `invoice_id` int NOT NULL,\n  `contract_id` int NOT NULL,\n  `invoice_number` varchar(32) NOT NULL,\n"
            "  `invoice_date` date NOT NULL,\n  `due_date` date NOT NULL,\n  `amount` decimal(10,2) NOT NULL,\n"
            "  `status` varchar(16) NOT NULL,\n  `paid_on` date DEFAULT NULL,\n  PRIMARY KEY (`invoice_id`),\n"
            "  KEY `contract_id` (`contract_id`)",
        )
        account_managers = [e["id"] for e in self.employees if e["department"] == "ADM"]
        invoice_id = 0
        for contract_id, (client, seats, annual, first_month) in enumerate(CORPORATE_CLIENTS, start=1):
            start = datetime.date(FISCAL_YEAR, first_month, 1)
            end = datetime.date(FISCAL_YEAR + 1, first_month, 1) - datetime.timedelta(days=1)
            corporate_contracts.rows.append(
                (contract_id, client, seats, Money(annual * 100), start, end, self.rng.choice(account_managers))
            )
            monthly = annual * 100 // 12
            for month in range(first_month, 13):
                invoice_id += 1
                invoice_date = month_end(FISCAL_YEAR, month)
                due = invoice_date + datetime.timedelta(days=30)
                number = f"AR-{contract_id:02d}{month:02d}"
                paid_on = None
                status = "open"
                if due <= AS_OF:
                    late = self.rng.random() < 0.12
                    if late and month >= 9:
                        status = "overdue"
                    else:
                        paid_on = due + datetime.timedelta(days=self.rng.randint(-10, 20 if late else 3))
                        status = "paid"
                ar_invoices.rows.append((invoice_id, contract_id, number, invoice_date, due, Money(monthly), status, paid_on))
                self.journal(
                    invoice_date,
                    f"Invoice {number}, {client}",
                    "ar_invoice",
                    [("1100", None, monthly, 0), ("4200", "ADM", 0, monthly)],
                )
                if paid_on:
                    self.journal(paid_on, f"Receipt of {number}", "ar_receipt", [("1000", None, monthly, 0), ("1100", None, 0, monthly)])

    # ------------------------------------------------------------------------------------------------------------
    # Course content: what each course is made of, and what is still being made
    # ------------------------------------------------------------------------------------------------------------
    def build_content(self) -> None:
        course_modules = self.table(
            "course_modules",
            "  `module_id` int NOT NULL,\n  `course_id` int NOT NULL,\n  `sequence` int NOT NULL,\n"
            "  `title` varchar(96) NOT NULL,\n  PRIMARY KEY (`module_id`),\n  KEY `course_id` (`course_id`)",
        )
        lessons = self.table(
            "lessons",
            "  `lesson_id` int NOT NULL,\n  `module_id` int NOT NULL,\n  `sequence` int NOT NULL,\n"
            "  `title` varchar(128) NOT NULL,\n  `duration_minutes` int NOT NULL,\n  `status` varchar(16) NOT NULL,\n"
            "  PRIMARY KEY (`lesson_id`),\n  KEY `module_id` (`module_id`)",
        )
        assets = self.table(
            "assets",
            "  `asset_id` int NOT NULL,\n  `lesson_id` int NOT NULL,\n  `asset_type` varchar(16) NOT NULL,\n"
            "  `status` varchar(16) NOT NULL,\n  PRIMARY KEY (`asset_id`),\n  KEY `lesson_id` (`lesson_id`)",
        )
        production_tasks = self.table(
            "production_tasks",
            "  `task_id` int NOT NULL,\n  `asset_id` int NOT NULL,\n  `task_type` varchar(16) NOT NULL,\n"
            "  `vendor_id` int DEFAULT NULL,\n  `employee_id` int DEFAULT NULL,\n  `status` varchar(16) NOT NULL,\n"
            "  `due_date` date NOT NULL,\n  `cost_estimate` decimal(8,2) NOT NULL,\n  PRIMARY KEY (`task_id`)",
        )
        designers = [e["id"] for e in self.employees if e["department"] == "CONT"]
        module_id = 0
        lesson_id = 0
        asset_id = 0
        task_id = 0
        self.content_invoices: list[tuple[str, datetime.date, int, str]] = []
        for course_id, code, name, _cost in self.courses:
            in_production = code in IN_PRODUCTION_COURSES
            for sequence, module_title in enumerate(MODULE_TITLES[: self.rng.choice([3, 4])], start=1):
                module_id += 1
                course_modules.rows.append((module_id, course_id, sequence, f"{name}: {module_title}"))
                for lesson_sequence in range(1, 4):
                    lesson_id += 1
                    status = "published"
                    if in_production:
                        status = self.rng.choice(["draft", "in_review", "in_production", "published"])
                    title = f"{module_title} {lesson_sequence}"
                    lessons.rows.append((lesson_id, module_id, lesson_sequence, title, self.rng.randint(8, 28), status))
                    for asset_type in ASSET_TYPES:
                        if asset_type == "artwork" and lesson_sequence != 1:
                            continue
                        asset_id += 1
                        asset_status = "approved" if status == "published" else self.rng.choice(
                            ["planned", "in_production", "in_review", "approved"]
                        )
                        assets.rows.append((asset_id, lesson_id, asset_type, asset_status))
                        if not in_production:
                            continue
                        task_id += 1
                        vendor_name = self.rng.choice(FREELANCERS_BY_ASSET[asset_type])
                        cost_cents = {"video": 120000, "transcript": 9000, "artwork": 45000}[asset_type]
                        cost_cents += self.rng.randint(0, 20) * 1000
                        task_status = {"approved": "done", "in_review": "in_review", "in_production": "in_progress"}
                        due = day_of_year(self.rng, datetime.date(2025, 9, 1), datetime.date(2026, 2, 27))
                        production_tasks.rows.append(
                            (
                                task_id,
                                asset_id,
                                TASK_TYPE[asset_type],
                                self.vendor_ids[vendor_name],
                                self.rng.choice(designers),
                                task_status.get(asset_status, "not_started"),
                                due,
                                Money(cost_cents),
                            )
                        )
                        if asset_status == "approved":
                            invoice_date = min(AS_OF, due)
                            self.content_invoices.append((vendor_name, invoice_date, cost_cents, code))

    # ------------------------------------------------------------------------------------------------------------
    # Accounting: vendors, what they billed, payroll, expenses, the budget, and the general ledger
    # ------------------------------------------------------------------------------------------------------------
    def build_vendors(self) -> None:
        vendors = self.table(
            "vendors",
            "  `vendor_id` int NOT NULL,\n  `name` varchar(64) NOT NULL,\n  `category` varchar(32) NOT NULL,\n"
            "  `payment_terms_days` int NOT NULL,\n  `is_content_freelancer` tinyint(1) NOT NULL,\n"
            "  PRIMARY KEY (`vendor_id`),\n  UNIQUE KEY `name` (`name`)",
        )
        self.vendor_ids = {}
        self.vendor_terms = {}
        for vendor_id, (name, category, terms, freelancer) in enumerate(VENDORS, start=1):
            vendors.rows.append((vendor_id, name, category, terms, freelancer))
            self.vendor_ids[name] = vendor_id
            self.vendor_terms[name] = terms

    def build_accounting(self) -> None:
        chart = self.table(
            "chart_of_accounts",
            "  `gl_account` char(4) NOT NULL,\n  `name` varchar(64) NOT NULL,\n  `account_type` varchar(16) NOT NULL,\n"
            "  PRIMARY KEY (`gl_account`)",
        )
        for account, name, account_type in CHART_OF_ACCOUNTS:
            chart.rows.append((account, name, account_type))

        ap_invoices = self.table(
            "ap_invoices",
            "  `invoice_id` int NOT NULL,\n  `vendor_id` int NOT NULL,\n  `invoice_number` varchar(32) NOT NULL,\n"
            "  `invoice_date` date NOT NULL,\n  `due_date` date NOT NULL,\n  `amount` decimal(10,2) NOT NULL,\n"
            "  `gl_account` char(4) NOT NULL,\n  `department_id` int NOT NULL,\n  `description` varchar(128) NOT NULL,\n"
            "  `status` varchar(16) NOT NULL,\n  `paid_on` date DEFAULT NULL,\n  PRIMARY KEY (`invoice_id`),\n"
            "  KEY `vendor_id` (`vendor_id`)",
        )
        invoices: list[tuple[str, datetime.date, int, str, str, str]] = []
        for vendor_name, account, department_code, monthly in RECURRING_INVOICES:
            for month in range(1, 13):
                amount = monthly * 100 + self.rng.randint(-8, 8) * 100 * (monthly // 1000 or 1)
                if vendor_name == "Cortex AI Services":
                    amount = int(monthly * 100 * (1 + month * 0.12))
                invoices.append(
                    (vendor_name, month_end(FISCAL_YEAR, month), amount, account, department_code, f"{month:02d}/2025")
                )
        for vendor_name, invoice_date, amount, course_code in self.content_invoices:
            invoices.append((vendor_name, invoice_date, amount, "5100", "CONT", f"{course_code} production"))
        invoices.append(("Summit Legal LLP", datetime.date(2025, 4, 30), 1850000, "5700", "EXEC", "Contracts review"))
        invoices.sort(key=lambda invoice: (invoice[1], invoice[0]))
        for invoice_id, (vendor_name, invoice_date, amount, account, department_code, label) in enumerate(
            invoices, start=1
        ):
            due = invoice_date + datetime.timedelta(days=self.vendor_terms[vendor_name])
            paid_on = None
            status = "open"
            if due <= AS_OF:
                if self.rng.random() < 0.95:
                    paid_on = due - datetime.timedelta(days=self.rng.randint(0, 5))
                    status = "paid"
                else:
                    status = "overdue"
            number = f"INV-{self.vendor_ids[vendor_name]:02d}{invoice_id:04d}"
            ap_invoices.rows.append(
                (
                    invoice_id,
                    self.vendor_ids[vendor_name],
                    number,
                    invoice_date,
                    due,
                    Money(amount),
                    account,
                    self.department_ids[department_code],
                    f"{vendor_name}: {label}",
                    status,
                    paid_on,
                )
            )
            self.journal(
                invoice_date,
                f"Invoice {number}",
                "ap_invoice",
                [(account, department_code, amount, 0), ("2000", None, 0, amount)],
            )
            if paid_on:
                self.journal(paid_on, f"Payment of {number}", "ap_payment", [("2000", None, amount, 0), ("1000", None, 0, amount)])

        # payroll, at the end of each month, by department.
        for month in range(1, 13):
            pay_day = month_end(FISCAL_YEAR, month)
            lines = []
            total = 0
            for code, _name in DEPARTMENTS:
                monthly = 0
                for employee in self.employees:
                    if employee["department"] == code and employee["hire_date"] <= pay_day:
                        monthly += employee["salary_cents"] // 12
                if monthly:
                    lines.append(("5000", code, monthly, 0))
                    total += monthly
            lines.append(("1000", None, 0, total))
            self.journal(pay_day, f"Payroll {month:02d}/2025", "payroll", lines)

        expense_reports = self.table(
            "expense_reports",
            "  `report_id` int NOT NULL,\n  `employee_id` int NOT NULL,\n  `submitted_on` date NOT NULL,\n"
            "  `category` varchar(16) NOT NULL,\n  `amount` decimal(8,2) NOT NULL,\n  `status` varchar(16) NOT NULL,\n"
            "  `approved_by` int DEFAULT NULL,\n  PRIMARY KEY (`report_id`),\n  KEY `employee_id` (`employee_id`)",
        )
        for report_id in range(1, 81):
            employee = self.rng.choice(self.employees)
            category, low, high = self.rng.choice(EXPENSE_CATEGORIES)
            amount = self.rng.randint(low, high) * 100 + self.rng.randint(0, 99)
            submitted = day_of_year(self.rng, max(employee["hire_date"], datetime.date(2025, 1, 2)), AS_OF)
            status = "approved"
            if submitted > datetime.date(2025, 12, 10):
                status = "submitted"
            elif self.rng.random() < 0.07:
                status = "rejected"
            approver = None
            if status != "submitted":
                approver = 10  # the chief financial officer approves every report
            expense_reports.rows.append((report_id, employee["id"], submitted, category, Money(amount), status, approver))
            if status == "approved":
                self.journal(
                    submitted + datetime.timedelta(days=3),
                    f"Expense report {report_id}",
                    "expense_report",
                    [("5500", employee["department"], amount, 0), ("1000", None, 0, amount)],
                )

        department_budgets = self.table(
            "department_budgets",
            "  `department_id` int NOT NULL,\n  `fiscal_year` int NOT NULL,\n  `fiscal_month` int NOT NULL,\n"
            "  `gl_account` char(4) NOT NULL,\n  `budget_amount` decimal(10,2) NOT NULL,\n"
            "  PRIMARY KEY (`department_id`, `fiscal_year`, `fiscal_month`, `gl_account`)",
        )
        spend: dict[tuple[str, int, str], int] = {}
        for _journal, entry_date, account, department_id, _description, _source, debit, _credit in self.gl_lines:
            if account < "5000" or department_id is None:
                continue
            code = DEPARTMENTS[department_id - 1][0]
            key = (code, entry_date.month, account)
            spend[key] = spend.get(key, 0) + debit.cents
        for (code, month, account), actual in sorted(spend.items()):
            # a plan made at the start of the year: near what was spent, sometimes well under it.
            factor = self.rng.choice([0.9, 0.95, 1.0, 1.0, 1.05, 1.1, 0.75])
            if account == "5300":
                factor = 0.8  # the plan didn't foresee how fast AI services would grow.
            budget = int(actual * factor) // 10000 * 10000
            department_budgets.rows.append((self.department_ids[code], FISCAL_YEAR, month, account, Money(budget)))

        gl_entries = self.table(
            "gl_entries",
            "  `line_id` int NOT NULL,\n  `journal_id` int NOT NULL,\n  `entry_date` date NOT NULL,\n"
            "  `gl_account` char(4) NOT NULL,\n  `department_id` int DEFAULT NULL,\n  `description` varchar(64) NOT NULL,\n"
            "  `source` varchar(16) NOT NULL,\n  `debit` decimal(12,2) NOT NULL,\n  `credit` decimal(12,2) NOT NULL,\n"
            "  PRIMARY KEY (`line_id`),\n  KEY `entry_date` (`entry_date`),\n  KEY `gl_account` (`gl_account`)",
        )
        ordered = sorted(self.gl_lines, key=lambda line: (line[1], line[0]))
        for line_id, line in enumerate(ordered, start=1):
            gl_entries.rows.append((line_id, *line))

    def build(self) -> None:
        """Every table, in an order that keeps the random numbers the same from run to run."""
        self.build_people()
        self.build_vendors()
        self.build_admissions()
        self.build_corporate()
        self.build_content()
        self.build_accounting()


TABLE_ORDER = [
    "departments",
    "employees",
    "compensation",
    "pto_balances",
    "pto_requests",
    "job_requisitions",
    "students",
    "promo_codes",
    "cohorts",
    "enrollments",
    "payments",
    "refunds",
    "corporate_contracts",
    "ar_invoices",
    "course_modules",
    "lessons",
    "assets",
    "vendors",
    "production_tasks",
    "chart_of_accounts",
    "ap_invoices",
    "expense_reports",
    "department_budgets",
    "gl_entries",
]


def render_sql(backoffice: Backoffice) -> str:
    """The SQL that creates and fills every table, then the users and their grants."""
    out = [
        "-- Stackademy's back office: generated by scripts/generate_backoffice.py. Don't edit it: change the script,",
        "-- run it, and commit both. Compatible with MariaDB 10.6+ / 11.x and MySQL 8.x. Every name, number and",
        f"-- address in it is fictional. Fiscal year {FISCAL_YEAR}, as of {AS_OF.isoformat()}.",
        "",
        f"USE `{DATABASE}`;",
        "/*!40101 SET NAMES utf8mb4 */;",
        "SET FOREIGN_KEY_CHECKS=0;",
        "",
    ]
    for name in TABLE_ORDER:
        table = backoffice.tables[name]
        out.append(f"DROP TABLE IF EXISTS `{name}`;")
        out.append(f"CREATE TABLE `{name}` (\n{table.ddl}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
        for start in range(0, len(table.rows), 200):
            chunk = table.rows[start : start + 200]
            values = ",\n".join("(" + ",".join(sql_value(value) for value in row) + ")" for row in chunk)
            out.append(f"INSERT INTO `{name}` VALUES\n{values};")
        out.append("")
    out.append("SET FOREIGN_KEY_CHECKS=1;")
    out.append("")
    out.append("-- The read-only users, one per department, and the tables that each may read. Their passwords are their")
    out.append("-- names: this is a public demonstration database. Every privilege is revoked first, so that a user that")
    out.append("-- an earlier version could read the whole database with is narrowed to its tables.")
    for user, tables in GRANTS.items():
        out.append(f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY '{user}';")
        out.append(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{user}'@'%';")
        for table in tables:
            out.append(f"GRANT SELECT ON `{DATABASE}`.`{table}` TO '{user}'@'%';")
    out.append("FLUSH PRIVILEGES;")
    out.append("")
    return "\n".join(out)


def render_grants() -> str:
    """The users and their tables, one line per user, for create-course-database.sh to check against."""
    lines = [
        "# The read-only users of the stackademy database, and the tables that each may read, one user per line.",
        "# Generated by scripts/generate_backoffice.py; create-course-database.sh checks that each user may read exactly",
        "# these tables, and nothing else.",
    ]
    for user, tables in GRANTS.items():
        lines.append(f"{user} {' '.join(sorted(tables))}")
    return "\n".join(lines) + "\n"


def main() -> int:
    """Write, or check, backoffice.sql and backoffice-grants.txt."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if the committed files are out of date")
    args = parser.parse_args()

    backoffice = Backoffice()
    backoffice.build()
    outputs = {BACKOFFICE_SQL: render_sql(backoffice), GRANTS_TXT: render_grants()}
    stale = []
    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        if args.check:
            stale.append(path.name)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.name}")
    if stale:
        print(f"out of date: {', '.join(stale)}. Run python3 scripts/generate_backoffice.py, and commit the result.")
        return 1
    for name in TABLE_ORDER:
        print(f"{name}: {len(backoffice.tables[name].rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
