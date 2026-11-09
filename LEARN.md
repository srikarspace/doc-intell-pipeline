# Doc Intel Pipeline

We are building a doc intel pipeline. It looks at the pdf docs and returns the data needed in structured form. For this we extract/parse the data from the pdf and share it to a model. Here we compare different parsers and different types of models and see how the pipeline is performing. At the end we compare the quality and deduce which options are better what to choose and why. The good thing about this is that we have verification data already provided. So we can compare the accuracy of the response as well and add Evals as needed.

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
- Context length check is important because based on it we can decide what model we need to choose and if the input context is too big we can chunk the context. Apart from that we can estimate the cost as well. We use char length / 4 as tokens size of the file.

### Phase 1: Create schema, LLM Client, Extract, Score in Evals

#### 1a: Create a schema, LLM Client
- We use pydantic to create a schema.
- Its a Class which is used as both template and validation. We send it to the LLM to return response in a structured response. We also validate with the same Class. One file does two things.
- Three configs to consider when creating a schema and sending to LLM.
    - `extra="forbid"`: no extra props should be returned by the model. Ex: expected `{"name":"sam"}` returned `{"name":"sam", "age": 20}`. This is a warning. It should match expectation.
    - `strict=True`: The expected response should always be returned. Ex: expected `{"is_present": True}` returned `{"is_present": "yes"}`. This is a warning. It should match expectation. If    `strict=False` then Class would convert it `yes` to `True`
    - `required fields`: We have to pass the list of required fields so that LLM knows what not to miss.
        - If three are not satisfied then a warning/error is thrown.
        - We also request `Quotes` along with answer which is the proof of the data in the text.
- `from pydantic import SecretStr` - Here `SecretStr` lets the LLM API know that not to log secrets and if logged they should be like `SecretStr('**********')`
- `@lru_cache` - is like memoization is JS. First time it returns the function and next time it returns the function from cache.
- The provider needs schema in JSON format so we need to convert the schema to JSON.
- We have to create the `call_llm()` that makes the call to the LLM, verifies the response and logs the response to DuckDB.
- Here we decide when to recall the LLM. A bad response is not an error its bad result. We can retry with the base result.
- Status code: 429 is for rate limit. If the requests limit has reached. We can retry in this scenario.
- We need to log cost, time, response and error. Every request need this to analyze later. We can add them to a db table or to a logging server.
- `Temperature=0` - Model picks the right answer.
- We retry ourselves only for Network error and Ratelimit errors but leave the SDK to retry on it self. We return the rest to caller in the agent.
- `require_parameters=True` - Open router passes the request to a model provider who would actually return the response in users request format.

#### 1b: Prompt v1 and Extract

- The prompt(both system and user) is data not code. It lives in a versioned file with version name. Every run says which version was used. 
    - Every new prompt is an experiment and the score can change and we want to know which exact version of prompt was used for what score.
- Contract goes with the prompt but it never changes.
- New prompt, new version, but contract never changes.
- Once call per contract is cheap.
- Good Prompt
    - When extracting labels from text, its good practice to have label definitions.
    - Add guard rails when data not available or any other request apart from labels extraction is provided
- System Prompt: When extracting fields from docs
    - Role of the LLM 
    - Rules for every field:
        - How should be the response for each field
        - What should be responded if there is no value for a field
        - Only add data if field exists
    - Rules for field values:
        - Special format of values for each field if present
    - What each field means:
        - These are the definitions for each field
- User Prompt: Where we pass the content of the doc.
- We load the prompt, build the message with prompt and contract and send the request to the llm with the message
- Once we get the response we extract the data and persist to logs

#### 1c: Scoring in Evals, experiments
- Without evals we have answers and gold labels but we don't know if its right. With evals we will see if the the answer is right.

    ||Model: found|Model: not found|
    |---|---|---|
    |Field: is there|TP(correct)|FN(missed it)|
    |Field: not there|FP(made it up)|TN(correct silently)|

        - True/False: was the model right
        - Positive/Negative: did the model say found?

- Precision = `TP / (TP + FP)` = When the model says found how many times its correct
- Recall = `TP / (TP + FN)` = Out of all the things that is there, how much did it find

- We have to `normalize` data. Ex: Change similar texts to same format. `11/14/17`, `2017-11-14` and `2017/11/14` to `2017-11-14`.  Why? The lawyer wrote `11/14/17` and the modal returned `2017-11-14`. A plane `==` is wrong but normalizing first says correct. 
- Having a `Threshold` value is important. What is Threshold? The lowest score that still counts as match. Why? For the quotes the model copies a little more or little less text. An overlap score with a threshold says close enough. Measuring `Jaccard` for two texts can help with calculating threshold. Ex: `"the State of Michigan"` and `"laws of Michigan"` share 2 of 5 words, so `0.4`. We can set a threshold value of `0.4`.
- More questions:
    - What if even after normalizing some data is missing? gold label `2017` but modal returns `2017-11-14` is this right or wrong. We need to decide what to do to the score as year is still correct.
    - What if model returned only `Michigan` but the goal label is `This Agreement shall be governed by the laws of the State of Michigan.`. Jaccard score is `0.09` right which will be too low that threshold `0.5` then how do we score as the answer is still correct.

- To answer edge cases like above
    - Lets say gold label has no answer but model returned a value. Now we can't compare it right? now we compare quotes in this case.

- Scoring
    - We save the answers and score as many times as we want. Because Answers cost money but scoring is free.
    - We can change the scoring rule and score as many times as we want.
    - `predictions` are long. One row per contract and label. Every row keeps the fields whole answer in JSON.
    - `ok` and `found` are also plain columns. Helps calculate TP, FP and FN.
    - Predict and then score.

- Predictions
    - We need to save the runs data, like `run_id`, prompt version, cost etc. To answer product or business when needed.
    - A `runs` table one row per `run`.
    - Primary key on each run is contract and field.
    - Lets say the response JSON is broken then we ignore the whole run. Because if we consider it would be a FN and as a result it would get down the Recall. This makes the model in a good place. We would fix the JSON issue separately. 

- Estimates
    - We should know the cost before we spend. We estimate the cost before making the LLM call. So that we know what would be the actual cost in production.
    - The estimate counts characters not tokens.
    - Sometimes the estimated cost can be cheaper than actual cost. This can be because the distribution used a different provider. For this before running all the contracts we check with few and then we understand how to estimate.

- Scoring Setup:
    1. Create gold values and quotes to compare if not present yet.
    2. Then add matching rules for the models answers and the gold values.
    3. Setup `outcome` table. In order to score for each field we need to compare either answers and gold values or quotes as sometimes values can be missing.
    4. Scoring starts.
    5. Setup tables for `runs`, `scores`(PK: run_id, doc_id, field) and `predictions`(PK: run_id, doc_id, field).
    6. Estimate the cost to answer "What is the run cost before we spend it".
    7. With above setup as we have `runs` stored. We can change the scoring formula when we want to get a new score.

- Runs
    - Call are slow:
        - we are parallel runs for a set of contract at once
        - Doing one at a time will take much longer so we are doing a parallel run.
    - Runs stop:
        - But if network fails for one of the contracts. If we rerun we would pay for all the parallel again.
        - So we keep a resume option so that we can pay for the failed ones.
    - One bad contract should not stop all the other runs

- Experiment 
    - We run an experiment and measure metrics so that we can compare with other experiments
    - Then get F1, TP, FP, FN calculate precision, recall
    - Create a graph for the labels and compare with all the labels

- Models(E1):
    - We need to test different models with a same experiment(data, prompt, score formula)
    - When selecting a modal we need to check license. For business most models with Apache or MIT are fine to use.
    - Reasoning models can add additional tokens for reasoning and that may be considered as output tokens and our overall cost can be higher.
    - We need to choose when after comparing F1, cost, p_50, p_95 and bad answers
    - Sometimes models can have same F1 but we will have to decide what product wants when we compare FP vs FN's

- Adjust score rules(E2):
    - Sometimes the scoring rules can be too hard on the model responses.
    - We need to check the errors and adjust them before adjusting the prompt because we might be scoring again against wrong rules.
    - Adjusting rules is free as we run them over previous results.

- Adjust prompt(E3):
    - Prompt change can fix some while it can break others. So having some rules before changing is better.
    - Adding new prompts costs us.
    - We add rules per label. One folder with all the rules.
    - Score is frozen as well. We will adjust later for new errors if needed.
    - Now update system prompt where we have fields with new rules.
    - Add rules for v2 to keep. Only when these rules pass against v1 we will keep v2.
    - Important learning is that we need to lockin the provider because when choosing different prompts each provider serve differently and that causes differences in results.

### Phase 2: observability, validators & citations, needs-review rules, retry experiments

- check each answer in prod while it runs and record the result and retry if error
- validators and code check
    - We need to check answers and return the list of issues that are easy to understand
    - We write rules to verify the LLMs response
    - Schema checks the LLM response only not the text in the response. We need to add rules to check the response text.
    - We can add rules in schema check or keep them outside to check each field. We should choose outside because if we keep in schema if one breaks the whole contract breaks. While keeping outside checks only the failed labels and returns only the failed issues.

- Add review rules and store issues
    - When a field gets need review flag. A person must take a look at the field.
    - We have to find review rate and rate catch on the results
    - Persist in Db so that someone can review

- Retry
    - Retry when there is an error or network issue
    - Retry should have a repair prompt for errors only. The other which have succeeded should not need to be extracted during retry to save cost.
    - We should be able to stop when retry is not working.
    - Measure the cost and result of retry for observability

### Phase 3: Parse PDFs

- There are three ways to parse PDFs. pypdf(plan py library), OCR style(uses OCR library which pulls models locally and extracts) and use Vision models(takes the PDF images and extracts text)
- We are testing multiple parsers. We need to make sure they all return same shape.
- We check the quality, cost and time and decide which one to choose.
- There will be empty pages so we should not worry when there is no text in a page. 
- Quotes fail when the text doesn't match. 1st and 1 st look similar to use but quote check fails as it compares ['1st] vs ['1', 'st']
- We would also like to cache data so that same PDF would not call LLM and use cache instead.
- If not cached, we parse, store and return

- pypdf
    - pypdf missed lot of quotes after the parse(missed 80%) even though length of the text and words are same. Its because of word breaks or new likes are added by pypdf. Also it can't convert scanned pdfs.

- Docling
    - Docling is a pipeline of small local models. Each model in it does a specific thing and together they create a text page.
    - OCR: Optical character recognition. A program that reads chars from an image using local models.
    - We can enable and disable OCR in docling
    - In docling if table mode is on then in our text we will be seeing table. If we are reading this text its good but if we are sending it to a LLM then the quotes might not match as the table border chars can be in the quotes and that breaks score. We should turn off table mode.
    - Process: pre_process(read text layer) -> layout(find blocks) -> OCR(read letters) -> layout_post_process(clean blocks) -> table(rows and blocks) -> assemble(join the blocks)
    - This is same as pypdf but its much slower may be when scanned pdfs where text is not available this will score better.

- Vision(using vision models or Multi model models)
    - DPI: Dots per inch. Measures how sharp a page is. Ex: 150 DPI makes the page 1275 pixels wide.
    - Data URL: the whole file written as text inside a string. Ex: data:image/png;base64,iVBOR....
    - Here the modal charges money for every page and it doesn't stop. It charged tokens for empty page as well(wrote 130k tokens for empty pages).
    - Two things save money. 1. Max token output. 2. Max budget. PS: Model changes for hidden thinking as well in order to generate output tokens.
    - One call per page not per document as budget and token check can happen often.
    - 

## Notes to remember
- If notebook locked your db
    - check `lsof data/docintel.duckdb`. Returns the PID where there is a connection.
    - then `kill {PID}`

