# Your First AI Application, Part 6

The finished files of Part 6: Searching Your Own Documents With a Vectorstore (coming soon, in the [Tutorials](https://blog.smarter.sh/category/tutorials/) category).

Stackademy's student handbook, which Stanley searches when a question is about a policy: a Pinecone Vectorstore, the handbook loaded into it, and the Vectorsearch `handbook_search`, which Stanley lists. `stackademy_topics` grows to include student policies.

This part builds on [Part 5](../part-5/): apply that part's files first, if you haven't.

| File | What it is |
| --- | --- |
| [`stackademy-handbook-store.yaml`](stackademy-handbook-store.yaml) | The Vectorstore `stackademy_handbook`: a Pinecone index for the handbook. |
| [`stackademy-handbook.md`](stackademy-handbook.md) | Stackademy's student handbook: the document that the Vectorstore holds. |
| [`handbook-search.yaml`](handbook-search.yaml) | The Vectorsearch `handbook_search`: how Stanley searches the handbook. |
| [`stackademy-topics.yaml`](stackademy-topics.yaml) | The Guardrail `stackademy_topics`: keeps Stanley on Stackademy's topics. |
| [`course-advisor.yaml`](course-advisor.yaml) | The LLMClient `course_advisor`: Stanley. |

Apply them in this order, from this folder:

```console
smarter apply -f stackademy-handbook-store.yaml
smarter deploy vectorstore stackademy_handbook
smarter describe vectorstore stackademy_handbook   # until its status is ready
smarter documents vectorstore stackademy_handbook --add stackademy-handbook.md
smarter apply -f handbook-search.yaml
smarter apply -f stackademy-topics.yaml
smarter apply -f course-advisor.yaml
```

You can also add the handbook in the web console: open the Vectorstore's details, and drop the file on its Documents section.

This part needs a Pinecone api key in your platform's `SMARTER_APP_VECTORSTORE_PINECONE_API_KEY`. `stackademy-handbook.md` isn't a manifest: it is the document that the Vectorstore holds.

These files are the tutorial's answers. A Smarter platform never loads this folder: you build these resources yourself, as the post shows.
