# Shortcuts for working on this repository from your own computer. Run `make` to list them.
.PHONY: help database check

help:
	@echo "make database  create the course database, smarter_test_db, in the smarter-mariadb Docker container"
	@echo "               (see scripts/create-course-database.sh --help for another container or server)"
	@echo "make check     run the automated checks on every file"

database:
	./scripts/create-course-database.sh

check:
	pre-commit run --all-files
