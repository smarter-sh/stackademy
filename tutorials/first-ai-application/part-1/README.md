# Your First AI Application, Part 1

The finished files of [Part 1: An OpenAI Chatbot in the Prompt Engineering Workbench](https://blog.smarter.sh/2026/11/23/first-ai-application-part-1-workbench/).

Stanley, Stackademy's course advisor: an LLMClient with a system prompt, built in the Prompt Engineering Workbench.

| File | What it is |
| --- | --- |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley. |

Apply them in this order, from this folder:

```console
smarter apply -f course-advisor.yaml
```

Stanley only knows what's in his prompt, so he can't answer questions about real courses yet.

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
