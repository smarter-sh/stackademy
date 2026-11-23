# Your First AI Application, Part 2

The finished files of [Part 2: The YAML Manifest Is the Application](https://blog.smarter.sh/2026/11/23/first-ai-application-part-2-yaml-manifest/).

The same LLMClient, as the YAML manifest that the workbench edits: its welcome message, example prompts and colors.

This part builds on [Part 1](../part-1/): apply that part's files first, if you haven't.

| File | What it is |
| --- | --- |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley. |

Apply them in this order, from this folder:

```console
smarter apply -f course-advisor.yaml
```

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
