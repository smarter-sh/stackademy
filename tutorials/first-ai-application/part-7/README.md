# Your First AI Application, Part 7

The finished files of [Part 7: Deploying an AI Chatbot and Embedding It in a Web Page](https://blog.smarter.sh/2026/11/23/first-ai-application-part-7-deploy-embed/).

Stanley goes live: deployed at his own url, and embedded in a page of Stackademy's website with Smarter Chat's embed script, from the `@smarter.sh/ui-chat` npm package.

This part builds on [Part 6](../part-6/): apply that part's files first, if you haven't.

| File | What it is |
| --- | --- |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley, who now allows requests from the web page's origin, `http://localhost:8000`. |
| [`index.html`](index.html) | A page of Stackademy's website, which embeds Stanley in a chat launcher. |

Apply and deploy Stanley, from this folder:

```console
smarter apply -f course-advisor.yaml
smarter deploy llmclient course_advisor
smarter describe llmclient course_advisor   # its status.url
```

On a Smarter platform on your own computer, his url is `http://course-advisor.3141-5926-5359.api.localhost:9357/`. Then serve the page, and open http://localhost:8000:

```console
python3 -m http.server 8000
```

On another platform, change `data-chatbot` in `index.html` to the url that `smarter describe` shows, and the origin in `allowedOrigins` to the page's.

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
