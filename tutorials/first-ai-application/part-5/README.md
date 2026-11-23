# Your First AI Application, Part 5

The finished files of [Part 5: LLM Guardrails That Keep a Chatbot Safe and On Topic](https://blog.smarter.sh/2026/11/23/first-ai-application-part-5-guardrails/).

Guardrails: three of Smarter's built-in guardrails, which redact personal information and refuse prompt injection and harmful prompts, and `stackademy_topics`, an LLM judge that keeps Stanley on topic.

This part builds on [Part 4](../part-4/): apply that part's files first, if you haven't.

| File | What it is |
| --- | --- |
| [`stackademy-topics.yaml`](stackademy-topics.yaml) | The Guardrail `stackademy_topics`: keeps Stanley on Stackademy's topics. |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley. |

Apply them in this order, from this folder:

```console
smarter apply -f stackademy-topics.yaml
smarter apply -f course-advisor.yaml
```

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
