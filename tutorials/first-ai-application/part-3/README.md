# Your First AI Application, Part 3

The finished files of [Part 3: Calling a REST API With an ApiPlugin](https://blog.smarter.sh/2026/11/23/first-ai-application-part-3-rest-api/).

A tool that calls Stackademy's course catalogue api: a Secret with the api's key, an ApiConnection to the api, and the ApiPlugin `course_catalog`, which Stanley now lists.

This part builds on [Part 2](../part-2/): apply that part's files first, if you haven't.

| File | What it is |
| --- | --- |
| [`catalog-api-key.yaml`](catalog-api-key.yaml) | The Secret `catalog_api_key`: the course catalogue api's key. |
| [`catalog-api.yaml`](catalog-api.yaml) | The ApiConnection `catalog_api`: where the course catalogue api is. |
| [`course-catalog.yaml`](course-catalog.yaml) | The ApiPlugin `course_catalog`: searches the course catalogue. |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley. |

Apply them in this order, from this folder:

```console
smarter apply -f catalog-api-key.yaml
smarter apply -f catalog-api.yaml
smarter apply -f course-catalog.yaml
smarter apply -f course-advisor.yaml
```

`catalog-api.yaml` points at `http://localhost:9357`, a Smarter platform on your own computer. On another platform, change `baseUrl` to its address.

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
