# Doc Intel Pipeline

We are building a doc intel pipeline. It looks at the pdf docs and returns the data needed in structured form. For this we extract/parse the data from the pdf and share it to a modal. Here we compare different parsers and different types of modals and see how the pipeline is performing. At the end we compare the quality and deduce which options are better what to choose and why. The good thing about this is that we have verification data already provided. So we can compare the accuracy of the response as well and add Evals as needed.

## We are planning to build this pipeline in phases.

### Phase 0: Scaffolding, setup database and basic evals
- We setup the repo with uv which is similar to npm in js. Create all the needed files and scaffolding. We are using DuckDB for the database.

#### Data Preparation
- We have to understand the data so that we can divide training data vs actual test data so. We will have all categories of data in both and also condense duplicates if any so that we don't create wrong data sets. We use dev data to develop and tune the agent and then use test only at the end. We use test in the end to actually get the numbers of how the agent is performing.
    - Use subset of the data. It keeps runs cheap and fast.
    - From the agent response we can't measure everything so its better to check the few important once. We pick items where we have enough examples to test. Check with product what to choose and what is important to keep. Important fields should be reliably consistent.
    - We need to create a seed and use it to generate dev and test splits from the data so that some one uses the repo to run dev and test they would use the same data.
    - Its also about families, we cant split families of data into dev and test. Because we tune dev with a similar family item and test it later with one of the family item right which can impact the data. So we need to make sure we use a similar family data in either dev or test. Not in both.
    - If there are different types of data, we need to share them equally in both dev and test.
    - `make data` it downloads the data and does the db and seed setup.

#### Evals
- Eval data stays fixed. The model answers can change a bit but what we are checking if the precision and recall are still good and improving. Each run gets a run_id to compare if the run gave a better answer. Also setup evals if possible in initial phases.
    - The eval data is the exam paper plus the answer key. The model is the student. Precision and recall are the grade. 
    - Example: 10 contracts really have a Non-Compete clause, and the model says "found" 8 times.
        - 6 of those 8 are real. 2 are made up.
        - Precision = 6 / 8 = 75%. Of the things it said, how many were true?
        - Recall = 6 / 10 = 60%. Of the things it should find, how many did it find?
    - Why the exam must stay fixed. You change the prompt, run again, and the grade goes from 60% to 80%. Same exam, so the prompt change caused the jump.

#### Context window
- Context length check is important because based on it we can decide what modal we need to choose and if the input context is too big we can chunk the context. Apart from that we can estimate the cost as well. We use char length / 4 as tokens size of the file.
 