# Shortcuts for working on this repository from your own computer. Run `make` to list them.
PYTHON ?= python3
VENV := venv

.PHONY: help init check database clean

help:
	@echo "make init      set up this clone: a Python virtual environment in $(VENV)/, with pre-commit,"
	@echo "               whose checks then run before each commit"
	@echo "make check     run the automated checks on every file"
	@echo "make database  create the course database, smarter_test_db, in the smarter-mariadb Docker container"
	@echo "               (see scripts/create-course-database.sh --help for another container or server)"
	@echo "make clean     remove $(VENV)/"

init:
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "make init needs Python 3: install it, or run make init PYTHON=/path/to/python3"; exit 1; }
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --quiet --upgrade pip
	$(VENV)/bin/pip install --quiet -r requirements.txt
	$(VENV)/bin/pre-commit install
	$(VENV)/bin/pre-commit install-hooks
	@echo ""
	@echo "Ready. The checks now run before each commit, and 'make check' runs them on every file."

check:
	@[ -x $(VENV)/bin/pre-commit ] || { echo "Run 'make init' first."; exit 1; }
	$(VENV)/bin/pre-commit run --all-files

database:
	./scripts/create-course-database.sh

clean:
	rm -rf $(VENV)
