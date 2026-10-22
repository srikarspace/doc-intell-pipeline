# Phase 0c: explore the data

In this part, you look at the data before you choose anything. You open a notebook and ask the
two tables six questions with SQL. Each question gets a short answer in your own words, a
"finding". Part 0d uses your findings to choose the 12 fields and the dev/test split.

## Words used in this part

Read these first. The rest of the doc uses them a lot.

- **Notebook**: a file with small boxes of code. You run one box and see its result right below
  it. Our notebook is `notebooks/00_explore.ipynb`.
- **Cell**: one box in a notebook. A **code cell** runs Python. A **markdown cell** holds text,
  like your findings.
- **Kernel**: the Python program behind the notebook. It keeps your variables between cells.
  Example: `con` made in cell 1 still exists in cell 5.
- **GROUP BY**: split the rows into groups, then run a function like `count(*)` or `avg(...)`
  once per group. Example: one count per contract type.
- **FILTER**: count or sum only some rows inside a group. Example: `count(*) FILTER (WHERE
  n_chars > 1000)`.
- **CTE**: a named middle step in one query, written with `WITH name AS (...)`. Like a `const` in
  JS that the next line uses.
- **JOIN USING**: put two tables side by side, matching rows on a column with the same name.
  Example: `labels JOIN contracts USING (doc_id)`.
- **Median, p90**: sort all values. The median (also called p50) is the value in the middle. p90
  is the value that 90% of rows are below. Example: for 1, 2, 3, 4, 100 the median is 3.
- **Token**: the small piece of text a language model reads. One token is about 4 characters of
  English. Example: "Governing Law" is about 3 tokens.
- **Context window**: the most tokens a model can read in one request. A longer contract does not
  fit and must be cut.
- **Presence rate**: the share of contracts where a lawyer found an answer for a category.
  Example: Governing Law 86% means 86 of every 100 contracts have one.
- **Family**: a group of contracts that belong together. Example: a contract and its amendment
  from the same company.
- **Leakage**: when the test data secretly contains copies of what you tuned on. Your test score
  then looks better than it really is.
- **Stratify**: split data so both halves keep the same mix. Example: both get some Distributor
  contracts.

## Objectives

By the end of this part you should be able to:

1. Open the project database from a notebook without locking other programs out.
2. Write SQL with `GROUP BY`, `FILTER`, a CTE, `JOIN USING` and quantiles, and say what each one
   does in one sentence.
3. Say why "presence" must be counted per contract, not per label row.
4. Guess if a contract fits in a model's context window from its length in characters.
5. Explain what a contract family is and why it matters for a dev/test split.

## Dependencies

You install nothing new. Part 0a already added `jupyter` and `ipykernel`. Part 0b made
`data/docintel.duckdb` with two tables: `contracts` (510 rows) and `labels` (28,031 rows).

This part has no new code in `src/`, so it has no test file. Part 0d adds code and its test.

## The big picture

Right now we have the data, but we do not know its shape. After this part, you know six facts
about it. Each fact drives one later decision:

| Question | Used in |
|---|---|
| 1. Contracts per type | 0d: stratify the split by type |
| 2. Length and context window | 1a: model choice; 1c: cost of one run |
| 3. Presence rate per category | 0d: which 12 fields; 1b: scoring absent answers |
| 4. Spans per contract | 1a: list fields in the schema |
| 5. Span length | 1b: scoring rules (exact match or overlap) |
| 6. Contract families | 0d: keep a family on one side of the split |

## Remember this

> Never choose fields or splits from memory. Count first. Presence rates tell you which fields
> have enough examples to measure. Families tell you which contracts must stay together, or the
> test set leaks.
>
> **Look before you choose: counts decide fields, families decide splits.**

## Why

**Choices made blind are hard to defend.** In an interview you will be asked "why these 12
fields?". "The plan said so" is a weak answer. "Notice Period is present in 22% of contracts, so
50 dev docs give about 11 examples" is a strong one.

**The data has surprises.** Some contract types are the same type under two names. One contract
appears twice under two names. A plan written before looking does not know this.

## Design decisions

- **A notebook, not a script.** Exploring is many small questions. The notebook keeps each query
  next to its result and your finding. Other option: the DuckDB command line. It keeps no record.
- **`read_only=True`.** Many programs can read the database at once. Only one program can write,
  and it must be alone. Other option: a normal connection. It locks the file, so every terminal
  checkpoint fails while the notebook is open.
- **SQL, not Python loops.** DuckDB groups and counts in one line, and fast. Other option:
  pandas. It is not installed, and it is one more API to learn.
- **Presence per contract.** One contract can have 5 Parties rows. So we first make one
  true/false per (contract, category). Other option: count rows. That gives Parties 500%.
- **Tokens = characters / 4.** This is a rough rule for English. It is enough to answer "does it
  fit?". Other option: the model's real tokenizer. We pick the model only in 1a.
- **Family = the company part of `doc_id`.** It sometimes groups contracts that are not related.
  That is safe: keeping two unrelated contracts together costs nothing. Splitting two related ones
  leaks. Other option: find amendments by hand. Slow, and easy to miss one.

## Worked example

Real CUAD numbers. Guess before you open each box.

### Round 1: average or median?

The average contract has 52,563 characters. Is the "typical" contract about that long?

<details><summary>Guess, then open</summary>

No. The median is 33,143 characters. A few very long contracts (the longest has 338,211) pull
the average up. The median ignores how far away the big values are. So we use the median and p90
for lengths in this part.
</details>

### Round 2: two names, one contract?

`ADUROBIOTECH,INC_..._CONSULTING AGREEMENT` and the same name with `(1)` at the end are two rows
in `contracts`. Are they two different contracts?

<details><summary>Guess, then open</summary>

No. The two `.txt` files are the same, byte for byte. If one goes to dev and one goes to test, the
test set holds a copy of a dev contract. That is leakage. Step 7 checks it.
</details>

## Project setup

The empty `notebooks/Untitled.ipynb` is not needed. Remove it:

```sh
git rm -q notebooks/Untitled.ipynb
```

Start Jupyter Lab:

```sh
make nb
```

It opens in your browser, inside the `notebooks/` folder. Make a new notebook (File, New,
Notebook, kernel "Python 3 (ipykernel)"). Rename it to `00_explore.ipynb`.

You should now have:

```
notebooks/
└── 00_explore.ipynb       empty
data/
└── docintel.duckdb        contracts (510) + labels (28,031), from 0b
```

Each step: **why it matters later**, a **guess first** query on a small slice, the **full
query**, then your **finding** in a markdown cell (two or three lines, your own words). Do not go
to the next step until your output matches.

## Step 1: connect from the notebook

**Why.** Every cell needs the database. A read-only connection lets your terminal checkpoints run
at the same time.

Put this in the first cell of `00_explore.ipynb`:

```python
import duckdb

con = duckdb.connect("../data/docintel.duckdb", read_only=True)
con.sql("SELECT count(*) AS n_contracts FROM contracts")
```

*Python here: [Jupyter cells and the kernel](./py/phase-0c.md#py-1) ·
[DuckDB from Python](./py/phase-0c.md#py-2).*

Here, we:

1. Use the path `../data/...`. The notebook runs inside `notebooks/`, so `..` goes up to the repo
   root first.
2. Open the file read-only. We only look in this part.
3. Show a query result. In a notebook, the last line of a cell is shown below it.

Checkpoint. Run the cell (Shift+Enter):

```
┌─────────────┐
│ n_contracts │
│    int64    │
├─────────────┤
│         510 │
└─────────────┘
```

## Step 2: contracts per type

**Why it matters later.** In 0d we split contracts into dev and test. Both halves should have
every kind of contract. So we need to know the types and their sizes.

Guess first: which of Supply, Franchise and Reseller has the most contracts? Add a cell:

```python
con.sql("""
SELECT contract_type, count(*) AS n
FROM contracts
WHERE contract_type IN ('Supply', 'Franchise', 'Reseller')
GROUP BY contract_type
ORDER BY n DESC
""")
```

```
┌───────────────┬───────┐
│ contract_type │   n   │
├───────────────┼───────┤
│ Supply        │    18 │
│ Franchise     │    15 │
│ Reseller      │    12 │
└───────────────┴───────┘
```

(From here on, we drop the type line under the column names to save space. You will see it.)

*Python here: [GROUP BY and aggregates](./py/phase-0c.md#py-3).*

Here, we keep three types (`WHERE ... IN`), make one group per type (`GROUP BY`), and count the
rows in each group (`count(*)`).

Full query. Remove the `WHERE` line, and add `contract_type` to the sort so ties have a fixed
order:

```python
con.sql("""
SELECT contract_type, count(*) AS n
FROM contracts
GROUP BY contract_type
ORDER BY n DESC, contract_type
""")
```

```
┌─────────────────────────┬───────┐
│      contract_type      │   n   │
├─────────────────────────┼───────┤
│ Maintenance             │    34 │
│ License_Agreements      │    33 │
│ Distributor             │    32 │
│ Strategic Alliance      │    32 │
│    ·  (rows cut here)   │     · │
│ Affiliate_Agreements    │     9 │
│ Endorsement Agreement   │     9 │
│ Joint Venture           │     9 │
│ Non_Compete_Non_Solicit │     3 │
│ Affiliate Agreement     │     1 │
└─────────────────────────┴───────┘
  28 rows (20 shown)    2 columns
```

Look at the bottom: `Affiliate_Agreements` and `Affiliate Agreement`. That looks like one type
with two names. The type is the PDF's folder name (0b), and CUAD has three folders: Part_I,
Part_II and Part_III. Check where the look-alikes live:

```python
con.sql("""
SELECT contract_type, split_part(pdf_path, '/', 5) AS part, count(*) AS n
FROM contracts
WHERE contract_type LIKE 'Affiliate%'
   OR contract_type LIKE 'Endorsement%'
   OR contract_type LIKE 'Joint Venture%'
GROUP BY contract_type, part
ORDER BY contract_type
""")
```

```
┌────────────────────────┬──────────┬───────┐
│     contract_type      │   part   │   n   │
├────────────────────────┼──────────┼───────┤
│ Affiliate Agreement    │ Part_III │     1 │
│ Affiliate_Agreements   │ Part_I   │     9 │
│ Endorsement            │ Part_I   │    13 │
│ Endorsement            │ Part_II  │     2 │
│ Endorsement Agreement  │ Part_III │     9 │
│ Joint Venture          │ Part_I   │     9 │
│ Joint Venture _ Filing │ Part_III │    14 │
└────────────────────────┴──────────┴───────┘
```

*Python here: [string functions](./py/phase-0c.md#py-8).*

Here, we:

1. Cut the path at each `/` and keep part 5 with `split_part`. Part 5 of
   `data/raw/CUAD_v1/full_contract_pdf/Part_I/...` is `Part_I`.
2. Match names that start the same with `LIKE 'Affiliate%'`. `%` means "anything after".

Each pair of names is one type, just in a different Part folder. So CUAD has 25 real types, not
28.

Add a markdown cell with your finding (two or three lines), then compare:

<details><summary>Reference finding</summary>

28 folder names, but 25 real types: Affiliate, Endorsement and Joint Venture each have two names
(Part_I and Part_III). Types are small: most have 9 to 34 contracts, one has 3. A split must
merge the look-alike names first, or a type can end up on one side only.
</details>

## Step 3: contract length and the context window

**Why it matters later.** In 1a we pick a model. If a contract does not fit in its context
window, we must cut it into pieces, which is much more work. Length also sets the cost of a run.

Guess first: the LIMEENERGY contract from 0b has 54,290 characters. About how many tokens?

```python
con.sql("""
SELECT n_chars, n_chars // 4 AS tokens
FROM contracts
WHERE doc_id LIKE 'LIMEENERGY%'
""")
```

```
┌─────────┬────────┐
│ n_chars │ tokens │
├─────────┼────────┤
│   54290 │  13572 │
└─────────┴────────┘
```

`//` divides and drops the part after the decimal point. So about 13,600 tokens.

Full query. Qwen3 text models read about 32k tokens as standard. Some versions read 128k or
more. We check the exact model in 1a. How many contracts fit in 32k?

```python
con.sql("""
SELECT
    quantile_cont(n_chars // 4, [0.5, 0.9])::INT[] AS p50_p90,
    max(n_chars // 4) AS max_tokens,
    count(*) FILTER (WHERE n_chars // 4 <= 32000) AS fits_32k,
    count(*) FILTER (WHERE n_chars // 4 > 32000) AS over_32k,
    sum(n_chars // 4) AS tokens_all
FROM contracts
""")
```

```
┌───────────────┬────────────┬──────────┬──────────┬────────────┐
│    p50_p90    │ max_tokens │ fits_32k │ over_32k │ tokens_all │
├───────────────┼────────────┼──────────┼──────────┼────────────┤
│ [8286, 30529] │      84552 │      461 │       49 │    6701586 │
└───────────────┴────────────┴──────────┴──────────┴────────────┘
```

*Python here: [FILTER](./py/phase-0c.md#py-4) · [quantiles](./py/phase-0c.md#py-7).*

Here, we:

1. Compute the median and p90 in one call: `quantile_cont(x, [0.5, 0.9])` gives a list of two
   values. `::INT[]` turns them into a list of whole numbers.
2. Count two different groups of rows in the same query with `FILTER (WHERE ...)`.
3. Add up all tokens with `sum`. That is what one run over all 510 contracts would read.

No `GROUP BY` here, so the whole table is one group, and we get one row.

<details><summary>Reference finding</summary>

Median contract is about 8k tokens, p90 about 31k, the longest about 85k. 461 of 510 fit in 32k
tokens. All 510 fit in 128k, so a 128k model never needs to cut a contract. All 510 is about 6.7M
tokens per run, so a smaller subset is cheaper to run many times.
</details>

## Step 4: presence rate per category

**Why it matters later.** To measure a field, we need enough contracts that have it. A field
present in 3% of contracts gives 1 or 2 examples in 50 docs. You cannot measure recall on 2
examples. In 1b, absent answers are scored too, so both sides matter.

Guess first: in the LIMEENERGY contract, how many rows does each category have, and is it
present?

```python
con.sql("""
SELECT category, count(*) AS n_rows, bool_or(is_present) AS present
FROM labels
WHERE doc_id LIKE 'LIMEENERGY%'
  AND category IN ('Parties', 'Governing Law', 'Non-Compete')
GROUP BY category
ORDER BY category
""")
```

```
┌───────────────┬────────┬─────────┐
│   category    │ n_rows │ present │
├───────────────┼────────┼─────────┤
│ Governing Law │      1 │ true    │
│ Non-Compete   │      1 │ false   │
│ Parties       │      5 │ true    │
└───────────────┴────────┴─────────┘
```

`bool_or` is true if at least one row in the group is true. Parties has 5 rows but counts as
present once. Non-Compete has 1 row: the absent row from 0b.

Full query. First make one true/false per (contract, category), then average over contracts:

```python
con.sql("""
WITH per_doc AS (
    SELECT doc_id, category, bool_or(is_present) AS present
    FROM labels
    GROUP BY doc_id, category
)
SELECT category, round(100 * avg(present::INT), 1) AS pct_present
FROM per_doc
GROUP BY category
ORDER BY pct_present DESC
""")
```

```
┌───────────────────────────────────┬─────────────┐
│             category              │ pct_present │
├───────────────────────────────────┼─────────────┤
│ Document Name                     │       100.0 │
│ Parties                           │        99.8 │
│ Agreement Date                    │        92.2 │
│ Governing Law                     │        85.7 │
│ Expiration Date                   │        81.0 │
│      ·  (rows cut here)           │          ·  │
│ Price Restrictions                │         2.9 │
│ Source Code Escrow                │         2.5 │
└───────────────────────────────────┴─────────────┘
  41 rows (20 shown)                    2 columns
```

*Python here: [CTEs with `WITH`](./py/phase-0c.md#py-5) · [`bool_or`](./py/phase-0c.md#py-4).*

Here, we:

1. Build `per_doc` in the CTE: 510 contracts times 41 categories = 20,910 rows, one per pair.
2. Turn true/false into 1/0 with `present::INT`. The average of 1s and 0s is the share of 1s.
3. Multiply by 100 and round to get a percent.

To see all 41 rows, end the cell with `.show(max_rows=50)` after the closing `)`. Look for the
12 candidate fields from `PLAN.md`. Write down the rate of each one.

<details><summary>Reference finding</summary>

Rates go from 100% (Document Name) to 2.5% (Source Code Escrow). Of the 12 candidates, the
rarest are Notice Period To Terminate Renewal (21.8%), Non-Compete (23.3%) and Change Of Control
(23.7%). In 50 dev docs that is only about 11 or 12 present examples each. Also note the exact
spelling: `Change Of Control`, `Ip Ownership Assignment`.
</details>

## Step 5: spans per contract

**Why it matters later.** If a category often has several spans, the model must return a list,
not one value. That changes the schema in 1a and the scoring in 1b.

Guess first: which LIMEENERGY categories have the most spans?

```python
con.sql("""
SELECT category, count(*) AS n_spans
FROM labels
WHERE doc_id LIKE 'LIMEENERGY%' AND is_present
GROUP BY category
ORDER BY n_spans DESC, category
LIMIT 3
""")
```

```
┌────────────────────┬─────────┐
│      category      │ n_spans │
├────────────────────┼─────────┤
│ Warranty Duration  │       8 │
│ Minimum Commitment │       5 │
│ Parties            │       5 │
└────────────────────┴─────────┘
```

The 5 Parties spans are `Distributor`, `Electric City Corp.`, `Electric City of Illinois
L.L.C.`, `Company` and `Electric City of Illinois LLC`. Two are nicknames, and two are the same
company written two ways.

Full query. Spans per contract, averaged over the contracts where the category is present:

```python
con.sql("""
WITH per_doc AS (
    SELECT doc_id, category, count(*) AS n_spans
    FROM labels
    WHERE is_present
    GROUP BY doc_id, category
)
SELECT category, round(avg(n_spans), 1) AS avg_spans, max(n_spans) AS max_spans
FROM per_doc
GROUP BY category
ORDER BY avg_spans DESC
LIMIT 5
""")
```

```
┌────────────────────┬───────────┬───────────┐
│      category      │ avg_spans │ max_spans │
├────────────────────┼───────────┼───────────┤
│ Source Code Escrow │       5.1 │        11 │
│ Parties            │       5.0 │        55 │
│ Rofr/Rofo/Rofn     │       4.3 │        22 │
│ Insurance          │       3.4 │        17 │
│ Audit Rights       │       3.0 │        19 │
└────────────────────┴───────────┴───────────┘
```

Here, we count spans per (contract, category) in the CTE, using only present rows. Then the
outer query takes the average and the max per category.

<details><summary>Reference finding</summary>

Parties averages 5 spans and reaches 55 in one contract. Many are nicknames ("Company",
"Distributor") or the same name spelled twice. So Parties must be a list in the schema, and the
scoring in 1b must decide what to do with nicknames. Most clause categories have 1 to 3 spans.
</details>

## Step 6: span length

**Why it matters later.** A short span (a date) can be checked with exact match. A long span (a
legal clause) almost never matches word for word, so 1b needs an overlap score. The `PLAN.md`
groups assume this. Now we check it.

Guess first: how long is an Agreement Date span, in characters?

```python
con.sql("""
SELECT span_text, length(span_text) AS n_chars
FROM labels
WHERE category = 'Agreement Date' AND is_present
ORDER BY doc_id
LIMIT 3
""")
```

```
┌─────────────────┬─────────┐
│    span_text    │ n_chars │
├─────────────────┼─────────┤
│ June 21, 1999   │      13 │
│ October 1, 2019 │      15 │
│ June 8, 2010    │      12 │
└─────────────────┴─────────┘
```

Full query on the 12 candidate fields:

```python
con.sql("""
SELECT category,
    quantile_cont(length(span_text), 0.5)::INT AS p50,
    quantile_cont(length(span_text), 0.9)::INT AS p90
FROM labels
WHERE is_present AND category IN (
    'Parties', 'Agreement Date', 'Governing Law',
    'Non-Compete', 'Change Of Control', 'Anti-Assignment',
    'Renewal Term', 'Notice Period To Terminate Renewal', 'Cap On Liability',
    'License Grant', 'Ip Ownership Assignment', 'Non-Transferable License')
GROUP BY category
ORDER BY p50
""")
```

```
┌────────────────────────────────────┬───────┬───────┐
│              category              │  p50  │  p90  │
├────────────────────────────────────┼───────┼───────┤
│ Agreement Date                     │    16 │    26 │
│ Parties                            │    17 │    44 │
│ Governing Law                      │   178 │   331 │
│ Anti-Assignment                    │   218 │   585 │
│ Renewal Term                       │   270 │   460 │
│ Notice Period To Terminate Renewal │   298 │   442 │
│ Change Of Control                  │   304 │   772 │
│ Cap On Liability                   │   306 │   705 │
│ Non-Compete                        │   309 │   720 │
│ Ip Ownership Assignment            │   337 │   800 │
│ Non-Transferable License           │   351 │   741 │
│ License Grant                      │   356 │   758 │
└────────────────────────────────────┴───────┴───────┘
```

Here, we measure each span with `length(span_text)`, then take the median and p90 per category.
We keep only present rows, because an absent row has no span (NULL).

<details><summary>Reference finding</summary>

Two clear sizes. Dates and parties are short (median under 20 characters). Everything else is a
clause of 180 to 360 characters, with p90 up to 800. Governing Law is a whole sentence, even
though the value we want is one word ("Delaware"). So short fields need a value plus a quote, and
long fields need overlap scoring.
</details>

## Step 7: contract families

**Why it matters later.** In 0d, if a contract is in dev and its amendment is in test, the test
set has seen most of the text already. That is leakage. We need a key that puts related
contracts together.

Guess first: the four FEDERATED contracts from 0b, and one Monsanto contract. How many
different family keys do you get?

```python
con.sql("""
SELECT DISTINCT lower(split_part(split_part(doc_id, '_', 1), ' - ', 1)) AS family, contract_type
FROM contracts
WHERE doc_id LIKE 'FEDERATED%' OR doc_id LIKE 'Monsanto%'
ORDER BY family
""")
```

```
┌────────────────────────────────────────┬───────────────┐
│                 family                 │ contract_type │
├────────────────────────────────────────┼───────────────┤
│ federatedgovernmentincomesecuritiesinc │ Service       │
│ monsanto company                       │ Marketing     │
└────────────────────────────────────────┴───────────────┘
```

Two. `DISTINCT` removes repeated rows, so the four FEDERATED rows become one.

Here, we build the key in three moves, from the inside out:

1. `split_part(doc_id, '_', 1)`: keep the text before the first `_`. Most names look like
   `COMPANY_date-EX-...`.
2. `split_part(..., ' - ', 1)`: keep the text before the first ` - `. 31 names look like
   `Monsanto Company - SECOND A_R ...` instead.
3. `lower(...)`: the same company is sometimes in capitals, sometimes not.

Full query. How big are the families?

```python
con.sql("""
WITH fam AS (
    SELECT doc_id, lower(split_part(split_part(doc_id, '_', 1), ' - ', 1)) AS family
    FROM contracts
),
sizes AS (
    SELECT family, count(*) AS n_docs FROM fam GROUP BY family
)
SELECT n_docs, count(*) AS n_families
FROM sizes
GROUP BY n_docs
ORDER BY n_docs
""")
```

```
┌────────┬────────────┐
│ n_docs │ n_families │
├────────┼────────────┤
│      1 │        431 │
│      2 │         23 │
│      3 │          3 │
│      4 │          6 │
└────────┴────────────┘
```

Two CTEs in a row: `fam` adds the key, `sizes` counts docs per family. Then we count families per
size. 32 families have more than one contract: 23 families of 2, 3 of 3 and 6 of 4. Together
they hold 79 contracts.

Now, do families stay inside one type? Join the key back to `contracts` to get the type:

```python
con.sql("""
WITH fam AS (
    SELECT doc_id, lower(split_part(split_part(doc_id, '_', 1), ' - ', 1)) AS family
    FROM contracts
)
SELECT family, count(DISTINCT contract_type) AS n_types, count(*) AS n_docs
FROM fam JOIN contracts USING (doc_id)
GROUP BY family
HAVING n_types > 1
ORDER BY n_docs DESC, family
LIMIT 4
""")
```

```
┌───────────────────────────────┬─────────┬────────┐
│            family             │ n_types │ n_docs │
├───────────────────────────────┼─────────┼────────┤
│ lejuholdingsltd               │       2 │      3 │
│ alliedesportsentertainmentinc │       2 │      2 │
│ ecosciencesolutionsinc        │       2 │      2 │
│ gpaqacquisitionholdingsinc    │       2 │      2 │
└───────────────────────────────┴─────────┴────────┘
```

*Python here: [JOIN USING and HAVING](./py/phase-0c.md#py-6).*

Here, we:

1. Match each `fam` row to its `contracts` row with `JOIN ... USING (doc_id)`.
2. Count different types per family with `count(DISTINCT contract_type)`.
3. Keep only groups with more than one type with `HAVING`. `WHERE` filters rows before grouping.
   `HAVING` filters groups after.

Without `LIMIT 4`, you get 11 families. So "stratify by type" and "a family stays on one side"
can disagree. 0d must pick which rule wins.

Last, the duplicate from Round 2. Prove the two files are the same, from your terminal:

```sh
cmp "data/raw/CUAD_v1/full_contract_txt/ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT.txt" \
      "data/raw/CUAD_v1/full_contract_txt/ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT(1).txt" \
      && echo same
```

```text
same
```

`cmp` prints nothing when two files are equal, so `echo same` runs. Our family key puts both in `adurobiotech,inc`, so they will stay together.

<details><summary>Reference finding</summary>

463 families. 32 have 2 to 4 contracts (79 contracts in total): amendments, numbered parts
(`Maintenance Agreement1` to `4`) and one exact copy (ADUROBIOTECH). 11 families span two types.
The split must move whole families, and it must decide which type a mixed family counts as.
</details>

## Step 8: read your six findings together

**Why.** 0d makes three decisions. Each one should point to a finding.

Add one last markdown cell, "Summary". Under it, write one line per decision:

1. **Fields**: which candidates look weak (Step 4) and which are lists (Step 5)?
2. **Subset size**: how many dev docs give at least 10 examples of your rarest field (Step 4),
   and what does a run cost in tokens (Step 3)?
3. **Split rules**: which types to merge (Step 2), and which families to keep together (Step 7)?

Checkpoint. Restart the kernel and run all cells (Kernel, Restart Kernel and Run All Cells).
Every cell runs from top to bottom with no error, and the outputs match the ones above.

Your project should now look like this:

```
notebooks/
└── 00_explore.ipynb       6 questions, 6 findings, 1 summary
data/
└── docintel.duckdb        unchanged (read-only in this part)
```

## Break it on purpose

**Break 1: the lock.** In cell 1, remove `read_only=True` and run the cell again. Guess what a
read-only query from the terminal does now:

```sh
uv run python -c "import duckdb; duckdb.connect('data/docintel.duckdb', read_only=True)"
```

```text
_duckdb.IOException: IO Error: Could not set lock on file ".../data/docintel.duckdb":
Conflicting lock is held in .../bin/python3.12 (PID ...) by user ...
```

The notebook now writes, so it must be alone. Put `read_only=True` back and run cell 1 again.

**Break 2: a column outside the group.** Guess the result:

```python
con.sql("SELECT contract_type, count(*) AS n FROM contracts")
```

```
BinderException: Binder Error: column "contract_type" must appear in the GROUP BY clause or
must be part of an aggregate function.
```

`count(*)` makes one row for the whole table, but `contract_type` has 28 values. They cannot fit
in one row.

## Gotchas

- **Lock errors in 0d.** `make data` writes. It fails while the notebook holds any connection,
  even read-only. Run `con.close()` in the notebook (or shut down the kernel) first.
- **Spelling of categories.** `Change Of Control`, not `Change of Control`. A wrong name in
  `IN (...)` gives no error, only fewer rows.
- **`make lint` reads notebooks too.** ruff checks `.ipynb` files. If it says "would reformat",
  run `make fmt` before you commit.
- **Missing rows in the output.** DuckDB shows 20 rows and puts `·` in the middle. Use
  `.show(max_rows=50)` to see all.
- **Never look at test rows.** There is no split yet, so all data is fine to look at now. After
  0d, only look at dev.

## Explain back, then commit

Explain each finding to Claude in a few sentences (the rule in `PLAN.md`), and say which 0d
decision it feeds. Then:

```sh
git add notebooks/00_explore.ipynb
git commit -m "phase 0c: explore CUAD in a notebook"
```

## Conclusion

What you have now:

- A notebook that answers six questions about CUAD, each with a query and a finding.
- Real numbers behind every 0d decision: type sizes, presence rates, span counts and lengths,
  contract lengths, and families.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why does dividing `labels` rows by 510 give Parties 500%, and which function fixes it?
2. Two contracts from the same company are in different types. Should they stay together in a
   split? Why?

Want more practice? Try these (optional):

1. Presence rate per category, but only for Distributor contracts. Which categories change most?
2. Find the contract with 55 Parties spans and read some of them.
3. Count how many of the 12 candidate fields each contract has (0 to 12).

Checklist (`../PLAN.md`): the **DuckDB SQL** item (GROUP BY, FILTER, CTE, JOIN, quantiles) is
done, together with 0b. This part also gives the evidence for **dev/test split, leakage,
stratification**, which 0d finishes.
