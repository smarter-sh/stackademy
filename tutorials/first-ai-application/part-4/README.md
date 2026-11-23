# Your First AI Application, Part 4

The finished files of [Part 4: Querying a SQL Database With a SqlPlugin](https://blog.smarter.sh/2026/11/23/first-ai-application-part-4-sql-database/).

A tool that queries Stackademy's course database: a Secret with the database user's password, a SqlConnection, and the SqlPlugin `course_prerequisites`, a recursive query that lists every course a student must take first.

This part builds on [Part 3](../part-3/): apply that part's files first, if you haven't.

| File | What it is |
| --- | --- |
| [`catalog-db-password.yaml`](catalog-db-password.yaml) | The Secret `catalog_db_password`: the course database user's password. |
| [`catalog-db.yaml`](catalog-db.yaml) | The SqlConnection `catalog_db`: Stackademy's course database. |
| [`course-prerequisites.yaml`](course-prerequisites.yaml) | The SqlPlugin `course_prerequisites`: a course's prerequisites, in order. |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley. |

Apply them in this order, from this folder:

```console
smarter apply -f catalog-db-password.yaml
smarter apply -f catalog-db.yaml
smarter apply -f course-prerequisites.yaml
smarter apply -f course-advisor.yaml
```

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
