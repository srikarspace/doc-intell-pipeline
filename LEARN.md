# Doc Intel Pipeline

We are building a doc intel pipeline. It looks at the pdf docs and returns the data needed in structured form. For this we extract/parse the data from the pdf and share it to a modal. Here we compare different parsers and different types of modals and see how the pipeline is performing. At the end we compare the quality and deduce which options are better what to choose and why. The good thing about this is that we have verification data already provided. So we can compare the accuracy of the response as well and add Evals as needed.

## We are planning to build this pipeline in phases.

### Phase 0: Scaffolding and setup database
- We setup the repo with uv which is similar to npm in js. Create all the needed files and scaffolding. We are using DuckDB for the database.
- Then we create a DB with two tables one with contracts and one with labels.
- contracts table holds the actual PDF data details which is sanitized for our use.
- labels table holds the verification data provided.
- We verify manually and via adding unit tests if everything looks good. 
 