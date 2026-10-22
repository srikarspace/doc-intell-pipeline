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

##### Scoring in Evals
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
    - What if even after normalizing some data is missing? goal label `2017` but modal returns `2017-11-14` is this right or wrong. We need to decide what to do to the score as year is still correct.
    - What if model returned only `Michigan` but the goal label is `This Agreement shall be governed by the laws of the State of Michigan.`. Jaccard score is `0.09` right which will be too low that threshold `0.5` then how do we score as the answer is still correct.

- To answer edge cases like above
    - Lets say gold label has no answer but model returned a value. Now we can't compare it right? now we compare quotes in this case.

1. Create gold values and qoutes to compare
2. Then add matching rules for the models answers and the gold values
3. The outcome table. In order to score for each field we need to compare either answers and gold values or quotes as sometimes values can be missing.


## Notes to remember
- If notebook locked your db
    - check `lsof data/docintel.duckdb`. Returns the PID where there is a connection.
    - then `kill {PID}`




