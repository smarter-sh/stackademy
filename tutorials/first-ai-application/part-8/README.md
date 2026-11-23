# Your First AI Application, Part 8

The finished files of Part 8: Controlling LLM Costs With Budgets, and Auditing With the Journal (coming soon, in the [Tutorials](https://blog.smarter.sh/category/tutorials/) category).

Stanley gets a budget: a daily allowance of 1.00 USD, which refuses his questions with a message of its own once he has spent it. The post first tries it out as a budget of 5,000 tokens a day, which runs out after two or three questions, then raises it to this one.

This part builds on [Part 7](../part-7/): apply that part's files, and deploy Stanley, first, if you haven't.

| File | What it is |
| --- | --- |
| [`course-advisor-daily.yaml`](course-advisor-daily.yaml) | The Budget `course_advisor_daily`: Stanley's daily allowance. |

Apply it from this folder:

```console
smarter apply -f course-advisor-daily.yaml
smarter describe budget course_advisor_daily   # its spending today, and whether it has locked Stanley
```

Only a superuser can apply a Budget. On a Smarter platform on your own computer, `admin@smarter.sh` is one. This part needs Smarter 0.47.4 or later, which prices the built-in providers' default models and turns the Journal on.

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
