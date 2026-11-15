#!/usr/bin/env bash
# -----------------------------------------------------------------------------------
# Creates Stackademy's database, stackademy: its course catalogue, from stackademy.sql, and its back
# office, the tables of its HR, Admissions, Accounting and Course Content departments, from
# backoffice.sql, which scripts/generate_backoffice.py generates.
#
# The database was called smarter_test_db, with the users smarter_test_user and
# smarter_test_proxy_user. Smarter 0.46.0 moved every account's Stackademy plugins to
# stackademy (manage.py rename_stackademy_resources), so the script drops the old
# database and its users, wherever they are left.
#
# The script creates the database, its tables and their rows, and a read-only user for
# each department, whose password is its name, and who may read only its department's
# tables, as backoffice-grants.txt lists them. It replaces the database if it already
# exists, so running it again resets it. Then it checks the result: the courses, that the
# general ledger balances, and that each user may read its tables and nothing else.
#
# It connects as a user that may create databases and users, e.g. root, and reads that
# user's password from the MYSQL_PWD environment variable. Without MYSQL_PWD, it asks
# for the password, except in the smarter-mariadb container of Smarter's local
# development environment, whose root password is "smarter".
#
# Smarter runs it when it sets up a platform, before it applies this repository's
# manifests (see scripts.yaml), with no arguments, and with the platform's database
# server in SMARTER_DATABASE_HOST, SMARTER_DATABASE_PORT and
# SMARTER_DATABASE_ADMIN_USERNAME, and the administrator's password in MYSQL_PWD. Smarter
# logs each line that it writes: its report on stdout, and problems on stderr.
#
# Usage:
#   scripts/create-course-database.sh                         # into the smarter-mariadb Docker container
#   scripts/create-course-database.sh --container my-mariadb  # into another Docker container
#   scripts/create-course-database.sh --host db.example.com   # into a server, with a MariaDB or MySQL client
#
# Options:
#   --container NAME   the Docker container that runs MariaDB or MySQL (default: smarter-mariadb)
#   --host HOST        connect to this server instead of a container (default: SMARTER_DATABASE_HOST)
#   --port PORT        the server's port (default: SMARTER_DATABASE_PORT, or 3306)
#   --user USER        the user to connect as (default: SMARTER_DATABASE_ADMIN_USERNAME, or root)
#   -h, --help         show this help
# -----------------------------------------------------------------------------------
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILES=("$SCRIPTS_DIR/stackademy.sql" "$SCRIPTS_DIR/backoffice.sql")
GRANTS_FILE="$SCRIPTS_DIR/backoffice-grants.txt"
DATABASE="stackademy"
# the course database's former name, and its users, which the script drops.
RETIRED_DATABASE="smarter_test_db"
RETIRED_USERS=("smarter_test_user" "smarter_test_proxy_user")
EXPECTED_COURSES=48
# the back office's fiscal year: the Board Pack's views total it, and nothing from another year.
FISCAL_YEAR=2025
# a table that only HR may read: every other user must be refused it.
SENSITIVE_TABLE="compensation"
SENSITIVE_TABLE_READER="stackademy_hr"
DEFAULT_CONTAINER="smarter-mariadb"
DEFAULT_CONTAINER_PASSWORD="smarter"

container="$DEFAULT_CONTAINER"
host="${SMARTER_DATABASE_HOST:-}"
port="${SMARTER_DATABASE_PORT:-3306}"
user="${SMARTER_DATABASE_ADMIN_USERNAME:-root}"

usage() {
    sed -n '/^# Usage:/,/^# ---/p' "${BASH_SOURCE[0]}" | sed -e '$d' -e 's/^# \{0,1\}//'
}

# The report, on stdout. Each line stands on its own, because Smarter logs it as one line, after the
# script's name.
report() {
    printf '%s\n' "$*"
}

# Stop, with the reason on stderr, and exit status 1.
fail() {
    printf 'FAILED: %s\n' "$*" >&2
    exit 1
}

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -c1-12
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -c1-12
    else
        echo "unknown"
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --container) container="${2:?--container needs a name}"; shift 2 ;;
        --host) host="${2:?--host needs a host name}"; shift 2 ;;
        --port) port="${2:?--port needs a number}"; shift 2 ;;
        --user) user="${2:?--user needs a user name}"; shift 2 ;;
        -h | --help) usage; exit 0 ;;
        *) usage >&2; fail "unknown option: $1" ;;
    esac
done

for sql_file in "${SQL_FILES[@]}"; do
    [ -r "$sql_file" ] || fail "can't read $sql_file"
done
[ -r "$GRANTS_FILE" ] || fail "can't read $GRANTS_FILE"

# -----------------------------------------------------------------------------------
# Where to connect, and how.
# -----------------------------------------------------------------------------------
client_args=(--default-character-set=utf8mb4)
if [ -n "$host" ]; then
    if command -v mariadb >/dev/null 2>&1; then
        client=mariadb
        # With the password in MYSQL_PWD, the MariaDB client can't verify the server's
        # certificate, and says so on every connection. Say it once, here, instead.
        client_args+=(--skip-ssl-verify-server-cert)
    elif command -v mysql >/dev/null 2>&1; then
        client=mysql
    else
        fail "install a MariaDB or MySQL client (mariadb or mysql) to connect to $host"
    fi
    target="$host:$port"
else
    command -v docker >/dev/null 2>&1 || fail "Docker isn't installed. Use --host to connect to a server instead."
    docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null | grep -q true ||
        fail "the Docker container $container isn't running"
    target="the $container container"
fi

if [ -z "${MYSQL_PWD:-}" ]; then
    if [ -z "$host" ] && [ "$container" = "$DEFAULT_CONTAINER" ]; then
        MYSQL_PWD="$DEFAULT_CONTAINER_PASSWORD"
    elif [ -t 0 ]; then
        read -r -s -p "Password for $user: " MYSQL_PWD
        echo
    else
        fail "set MYSQL_PWD to the password of $user"
    fi
fi
# The clients read the password from MYSQL_PWD, which keeps it off the command line.
export MYSQL_PWD

# Run SQL as $user, or as $as_user, with $MYSQL_PWD, e.g.
#   run_sql -e 'SELECT 1'
#   as_user=stackademy_catalog MYSQL_PWD=stackademy_catalog run_sql -e 'SELECT 1'
run_sql() {
    local login="${as_user:-$user}"
    if [ -n "$host" ]; then
        "$client" "${client_args[@]}" --user="$login" --host="$host" --port="$port" "$@"
    else
        # MariaDB's images have the mariadb client, and MySQL's have mysql.
        docker exec -i -e MYSQL_PWD "$container" sh -c \
            'if command -v mariadb >/dev/null 2>&1; then exec mariadb "$@"; else exec mysql "$@"; fi' \
            sh "${client_args[@]}" --user="$login" "$@"
    fi
}

query() {
    run_sql --batch --skip-column-names -e "$1"
}

# -----------------------------------------------------------------------------------
# Create the database.
# -----------------------------------------------------------------------------------
started=$SECONDS
report "creating Stackademy's course database, $DATABASE"

version="$(query 'SELECT VERSION();')" || fail "can't connect to $target as $user (see the error above)"
report "server: $target, version $version, as $user"
run_sql -e "DROP DATABASE IF EXISTS \`$RETIRED_DATABASE\`;" || fail "can't drop $RETIRED_DATABASE (see the error above)"
for retired_user in "${RETIRED_USERS[@]}"; do
    run_sql -e "DROP USER IF EXISTS '$retired_user'@'%';" || fail "can't drop the user $retired_user (see the error above)"
done
report "dropped the former database, $RETIRED_DATABASE, and its users, if they were there"
for sql_file in "${SQL_FILES[@]}"; do
    report "sql file: $(basename "$sql_file"), sha256 $(sha256 "$sql_file")"
    run_sql <"$sql_file" || fail "$(basename "$sql_file") failed in $target (see the error above)"
done
report "loaded in $((SECONDS - started))s"

# -----------------------------------------------------------------------------------
# Check the result.
# -----------------------------------------------------------------------------------
courses="$(query "SELECT COUNT(*) FROM $DATABASE.courses;")" || fail "can't read $DATABASE.courses"
[ "$courses" = "$EXPECTED_COURSES" ] || fail "$DATABASE.courses has $courses courses, not $EXPECTED_COURSES"
report "checked: $DATABASE.courses has $courses courses"

unbalanced="$(query "SELECT SUM(debit) - SUM(credit) FROM $DATABASE.gl_entries;")" ||
    fail "can't read $DATABASE.gl_entries"
[ "$unbalanced" = "0.00" ] || fail "the general ledger doesn't balance: debits exceed credits by $unbalanced"
report "checked: the general ledger balances"

retired="$(query "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '$RETIRED_DATABASE';")" ||
    fail "can't read information_schema.SCHEMATA"
[ "$retired" = "0" ] || fail "the former database, $RETIRED_DATABASE, is still there"
for retired_user in "${RETIRED_USERS[@]}"; do
    left="$(query "SELECT COUNT(*) FROM mysql.user WHERE User = '$retired_user';")" || fail "can't read mysql.user"
    [ "$left" = "0" ] || fail "the former user $retired_user is still there"
done
report "checked: the former database, $RETIRED_DATABASE, and its users are gone"

# The Board Pack's views total one fiscal year: the ledger and the enrollments start in the December before it.
board_revenue="$(query "SELECT SUM(amount) FROM $DATABASE.board_income_statement WHERE account_type = 'revenue';")" ||
    fail "can't read $DATABASE.board_income_statement"
ledger_revenue="$(query "SELECT SUM(g.credit - g.debit) FROM $DATABASE.gl_entries g JOIN $DATABASE.chart_of_accounts a
    ON a.gl_account = g.gl_account WHERE a.account_type = 'revenue' AND YEAR(g.entry_date) = $FISCAL_YEAR;")" ||
    fail "can't read $DATABASE.gl_entries"
[ "$board_revenue" = "$ledger_revenue" ] ||
    fail "board_income_statement's revenue is $board_revenue, not the ledger's $ledger_revenue for $FISCAL_YEAR"
board_enrollments="$(query "SELECT SUM(enrollments) FROM $DATABASE.board_enrollments;")" ||
    fail "can't read $DATABASE.board_enrollments"
year_enrollments="$(query "SELECT COUNT(*) FROM $DATABASE.enrollments WHERE YEAR(enrolled_on) = $FISCAL_YEAR;")" ||
    fail "can't read $DATABASE.enrollments"
[ "$board_enrollments" = "$year_enrollments" ] ||
    fail "board_enrollments counts $board_enrollments enrollments, not the $year_enrollments of $FISCAL_YEAR"
report "checked: the Board Pack's views total $FISCAL_YEAR, and nothing else"

grants_file_name="$(basename "$GRANTS_FILE")"
# Each line of the grants file: a user, then the tables that it may read. On file descriptor 3, because
# docker exec -i reads stdin, and would swallow the rest of the file.
while read -r db_user tables <&3; do
    case "$db_user" in "" | "#"*) continue ;; esac
    expected_grants=0
    for table in $tables; do
        as_user="$db_user" MYSQL_PWD="$db_user" query "SELECT COUNT(*) FROM $DATABASE.$table;" >/dev/null ||
            fail "$db_user can't log in, or can't read $DATABASE.$table"
        expected_grants=$((expected_grants + 1))
    done
    # USAGE, i.e. may log in, and SELECT on each of its tables. Anything else is too much.
    grants="$(query "SHOW GRANTS FOR '$db_user'@'%';")" || fail "can't read the grants of $db_user"
    table_grants="$(printf '%s\n' "$grants" | grep -c "^GRANT SELECT ON \`$DATABASE\`\.\`[a-z_]*\` TO " || true)"
    others="$(printf '%s\n' "$grants" | grep -v -e '^GRANT USAGE ON \*\.\* TO ' -e "^GRANT SELECT ON \`$DATABASE\`\.\`[a-z_]*\` TO " || true)"
    [ -z "$others" ] || fail "$db_user has more than read access to its tables: $others"
    [ "$table_grants" = "$expected_grants" ] ||
        fail "$db_user may read $table_grants tables, not the $expected_grants of $grants_file_name"
    if [ "$db_user" != "$SENSITIVE_TABLE_READER" ]; then
        if as_user="$db_user" MYSQL_PWD="$db_user" query "SELECT COUNT(*) FROM $DATABASE.$SENSITIVE_TABLE;" >/dev/null 2>&1; then
            fail "$db_user may read $DATABASE.$SENSITIVE_TABLE, which only $SENSITIVE_TABLE_READER may"
        fi
    fi
    report "checked: $db_user may read its $expected_grants tables, and nothing else"
done 3<"$GRANTS_FILE"

report "done in $((SECONDS - started))s"
