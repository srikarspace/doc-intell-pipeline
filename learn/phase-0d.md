# Phase 0d: fields, subset, split

In this part, you make three decisions from your 0c findings: the 12 fields, the set of about 100
contracts, and the rules for the dev/test split. Then you write `make_splits`, which turns your
split rules into a `splits` table. You finish with the E0 data card.

## Words used in this part

Read these first. 0c words (family, leakage, stratify, presence rate) are used again.

- **Field**: one thing we ask the model to extract. Each field is one CUAD category. Example:
  Governing Law.
- **Subset**: the contracts we actually run on. Example: 104 of the 510.
- **Dev set**: the contracts you look at and tune on. Like the practice exam.
- **Test set**: the contracts you only use for the final numbers. Like the real exam. You do not
  look at it before.
- **Split**: the rule that puts each contract in dev or test. The `splits` table stores the
  result.
- **Seed**: a number that starts a random generator. The same seed always gives the same "random"
  order. Example: seed 0 shuffles `[a, b, c]` to the same order every time.
- **Deterministic**: same input, same output, every time, on every machine.
- **Quota**: how many contracts one type gets in the subset. Example: Maintenance has 34 of 510
  contracts, so it gets about 34 / 510 of 100, which is 7.
- **Data card**: a short note about a dataset: what is in it, how it was picked, and its known
  problems. Ours is entry E0 in `EXPERIMENTS.md`.

## Objectives

By the end of this part you should be able to:

1. Defend each of your 12 fields with a number from your 0c notebook.
2. Explain why we need a test set, and why a family must stay on one side.
3. Write a split function that gives the same table every time for the same seed.
4. Check a split for leakage with one SQL query.
5. Fill in the E0 data card.

## Dependencies

You install nothing new. `random`, `re` and `collections` are part of Python itself (the
**standard library**), like `fs` and `path` in Node.

This part needs your notebook `notebooks/00_explore.ipynb` from 0c, with its six findings.

## The big picture

Right now we have 510 contracts and 41 categories, and no plan for which to use. After this part:

- `FIELDS` in `datasets.py` names the 12 categories we extract. 1a builds the schema from it. 1b
  scores only these.
- The `splits` table puts about 100 contracts in dev or test. 1c runs `--split dev` from it.
- E0 explains both choices with numbers. Phase 5 uses it to answer "which documents did we
  choose, and why?".

## Remember this

> The test set is a sealed envelope. A fixed seed fills it the same way every time. Whole
> families go in together, so no copy of a dev contract hides inside. You tune on dev, and you
> open test once, for the final numbers.
>
> **Same seed, same split; whole families; test stays sealed.**

## Why

**A subset keeps runs cheap and fast.** All 510 contracts are about 6.7M tokens per run. In
Phase 1 and 2 you run many times. 50 dev contracts are about 0.6M tokens per run.

**Tuning on your test set lies to you.** If you change the prompt until the numbers look good,
the prompt now fits those exact contracts. The numbers on new contracts will be lower. A test set
you never tune on gives an honest number.

**Every number must trace back.** A `run_id` in 1c says "dev, seed 0". That only means something
if seed 0 always gives the same contracts. So the split must be deterministic.

## Design decisions

- **`FIELDS` is a dict in `datasets.py`.** Keys are the 4 groups, values are CUAD category names.
  Code can import it. Other option: write it only in the notebook. Then no code can use it.
- **`splits` holds only the subset.** One row per chosen contract: `(doc_id, split)`. A run joins
  on it. Other option: all 510 rows with a third value `unused`. Every query then needs one more
  filter.
- **The split logic is Python, not SQL.** Shuffling families and filling quotas is a loop with
  state. Other option: `ORDER BY hash(doc_id)` in SQL. One line, but it cannot keep families
  together.
- **Our own `random.Random(seed)`.** It is a private generator. Other option: `random.seed(0)`
  then `random.shuffle`. Any other code that uses `random` would then change your split.
- **Sort before shuffle.** DuckDB does not promise row order without `ORDER BY`. A shuffle of a
  different starting order gives a different split. Other option: trust the order. It works until
  it does not.
- **Families first, then types.** A family goes to one side as a block. A family with two types
  counts as the type of its first contract (by `doc_id`). Other option: the most common type in
  the family. Same result for 10 of the 11 mixed families, and harder to explain.
- **`make data` also writes `splits`.** One command rebuilds everything, and the same seed gives
  the same table. Other option: a separate `make splits`. One more step to forget.

## Worked example

Real CUAD numbers. Guess before you open each box.

### Round 1: how many examples will dev have?

Notice Period To Terminate Renewal is present in 21.8% of contracts. Dev has 50 contracts. How
many dev contracts have a Notice Period?

<details><summary>Guess, then open</summary>

About 50 times 0.218 = 11, on average. But the split is random. With the reference split below, dev
gets 9. If the model finds 7 of 9, recall is 78%. One more miss and it is 67%. So with small
numbers, one contract moves the score a lot. Keep this in mind when you choose the subset size.
</details>

### Round 2: no `ORDER BY`

`make_splits` reads `SELECT doc_id, contract_type FROM contracts` with no `ORDER BY`, then
shuffles with seed 0. You run it twice on your laptop and get the same table. Is it
deterministic?

<details><summary>Guess, then open</summary>

Not for sure. DuckDB reads with several threads. Without `ORDER BY`, it may return rows in a
different order on another machine, or after `make data` rebuilds the table. The shuffle then
starts from a different list and gives a different split. "It worked twice" is not proof. Always
sort first.
</details>

### Round 3: split per contract

`CardlyticsInc_..._Maintenance Agreement1` to `Agreement4` are four parts of one deal. If each
contract picks its side alone, where do they go?

<details><summary>Guess, then open</summary>

About two in dev and two in test. The four texts share most of their wording. So the model is
tuned on half the deal, then tested on the other half. That is leakage. A family must move as one
block.
</details>

## Project setup

Close the notebook's database connection first. `make data` writes, and it must be alone. In the
notebook, run:

```python
con.close()
```

Then create the test file:

```sh
touch tests/test_splits.py
```

You should now have:

```
src/docintel/evals/
├── datasets.py            changes in this part: FIELDS, family, make_splits
└── store.py
tests/
├── test_data_load.py
├── test_smoke.py
└── test_splits.py         empty
notebooks/
└── 00_explore.ipynb       from 0c
```

Steps 1 to 3 are your decisions. For each: look at the evidence, write your choice, then open the
reference and compare. Steps 4 and 5 turn the decisions into code.

## Step 1: choose the 12 fields (your decision)

**Why.** Every later part measures only these 12. A field with too few examples cannot be
measured. A field nobody cares about wastes the work.

`PLAN.md` fixes the shape: 4 groups, 3 fields each. The candidates come from `PLAN.md`. Here is
the evidence from your 0c notebook, with the main alternatives:

| Group | Category | Present % | Spans when present | Median span (chars) |
|---|---|---|---|---|
| Basic facts | Parties | 99.8 | 5.0 | 17 |
| | Agreement Date | 92.2 | 1.0 | 16 |
| | Governing Law | 85.7 | 1.1 | 178 |
| | *Effective Date* | 76.5 | 1.1 | 20 |
| | *Expiration Date* | 81.0 | 1.1 | 195 |
| Yes/no + quote | Non-Compete | 23.3 | 2.2 | 309 |
| | Change Of Control | 23.7 | 2.1 | 304 |
| | Anti-Assignment | 73.3 | 1.7 | 218 |
| | *Exclusivity* | 35.3 | 2.3 | 300 |
| | *Termination For Convenience* | 35.9 | 1.3 | 163 |
| Numbers/terms | Renewal Term | 34.5 | 1.2 | 270 |
| | Notice Period To Terminate Renewal | 21.8 | 1.1 | 298 |
| | Cap On Liability | 53.9 | 2.4 | 306 |
| | *Uncapped Liability* | 21.8 | 1.5 | 423 |
| | *Minimum Commitment* | 32.4 | 2.6 | 275 |
| License/IP | License Grant | 50.0 | 3.0 | 356 |
| | Ip Ownership Assignment | 24.3 | 2.6 | 337 |
| | Non-Transferable License | 27.1 | 2.2 | 351 |
| | *Irrevocable Or Perpetual License* | 13.7 | 2.4 | 489 |
| | *Joint Ip Ownership* | 9.0 | 2.5 | 299 |

Alternatives are in *italics*. Questions to ask about each field:

1. **Enough examples?** Present % times your dev size (Step 2) should be about 10 or more.
2. **Does it test something new?** Effective Date is often the same text as Agreement Date. Two
   fields that test the same skill teach you less.
3. **Would a user ask for it?** The product request is "parties, renewal term, any non-compete?".
4. **Does the group stay mixed?** Each group should keep its answer shape: short value, yes/no
   with a quote, a term or amount, a long clause.

Write your 12 in a markdown cell called "Fields" in your notebook, with one reason each. Then add
this near the top of `src/docintel/evals/datasets.py`, below `RAW_DIR`, with your choices:

```python
FIELDS = {  # 0d decision: the 12 CUAD categories we extract, 3 per group
    "basic facts": ["...", "...", "..."],
    "yes/no + quote": ["...", "...", "..."],
    "numbers/terms": ["...", "...", "..."],
    "license/IP": ["...", "...", "..."],
}
```

Here, we keep the exact CUAD spelling as the value. Later code joins on `labels.category`, so
`Change of Control` (small "of") would match nothing.

Checkpoint. Check that all 12 names exist in `labels`:

```sh
uv run python -c "
import duckdb
from docintel.evals.datasets import FIELDS
names = [f for group in FIELDS.values() for f in group]
con = duckdb.connect('data/docintel.duckdb', read_only=True)
print(len(names), con.execute('SELECT count(DISTINCT category) FROM labels WHERE list_contains(?, category)', [names]).fetchone())"
```

```text
12 (12,)
```

*Python here: [nested comprehension](./py/phase-0d.md#py-1).*

If the second number is smaller, one name is misspelled. `list_contains(list, x)` is true when
`x` is in the list. The `?` gets its value from `[names]`, like the `$name` placeholders in 0b.

<details><summary>Reference choice (open after you decide)</summary>

The `PLAN.md` candidates, unchanged:

```python
FIELDS = {  # 0d decision: the 12 CUAD categories we extract, 3 per group
    "basic facts": ["Parties", "Agreement Date", "Governing Law"],
    "yes/no + quote": ["Non-Compete", "Change Of Control", "Anti-Assignment"],
    "numbers/terms": ["Renewal Term", "Notice Period To Terminate Renewal", "Cap On Liability"],
    "license/IP": ["License Grant", "Ip Ownership Assignment", "Non-Transferable License"],
}
```

Why:

- Effective Date and Expiration Date lose to Agreement Date and Governing Law. Effective Date
  often repeats Agreement Date. Expiration Date overlaps with Renewal Term.
- Non-Compete and Change Of Control are rare (about 23%). We keep them because they are what a
  lawyer asks about most, and absent answers are scored too. Exclusivity is the backup if dev has
  too few.
- Notice Period is the weakest (21.8%). It pairs with Renewal Term, so they test one skill
  together: "find the term, then the notice for it".
- Irrevocable and Joint Ip are too rare (14% and 9%).
</details>

## Step 2: choose the subset (your decision)

**Why.** The subset sets the cost of every run, and how many examples each field has.

Options:

| Option | Dev size | Notice Period examples in dev (21.8%) | Tokens per dev run |
|---|---|---|---|
| A. All 510, split in half | 255 | about 56 | about 3.4M |
| B. 200, stratified by type | 100 | about 22 | about 1.3M |
| C. 100, stratified by type | 50 | about 11 | about 0.66M |
| D. C, but only contracts under 32k tokens | 50 | about 11 | less |
| E. C, but pick more contracts that have rare fields | 50 | 20 or more | about 0.66M |

How we got the numbers: examples = present % times dev size. Tokens = dev size times 13,140, the
average contract length in tokens from 0c Step 3.

Things to weigh:

1. **Cost.** Multiply tokens per run by how many runs you expect in Phases 1 to 3. Prices for
   your model are on its OpenRouter page.
2. **Noise.** Round 1 showed how much one contract moves recall when examples are few.
3. **Realism.** D removes long contracts, but long contracts are the hard real case, and all of
   them fit in a 128k context window. E makes rare fields look common, so the "absent" side of the
   score no longer looks like real contracts.

Write your choice, with the reason, in a markdown cell called "Subset" in your notebook.

<details><summary>Reference choice (open after you decide)</summary>

**C: 100 contracts, stratified by type, long ones kept, no extra picking.** About 50 dev
contracts give 9 to 13 examples for the rarest fields. That is weak but usable for a first
version, and cheap enough to run often. If the 1c numbers are too noisy, raise `n_docs` to 200.
The split code takes `n_docs` as a parameter, so that is a one-number change. Decide it before
1c, and never change it after.
</details>

## Step 3: choose the split rules (your decision)

**Why.** These rules decide what "test" means for the whole project.

Decide each rule, and write them as a numbered list in a markdown cell called "Split rules":

1. **Dev share.** 50/50 or 60/40? A smaller test set gives noisier final numbers.
2. **Stratify by type?** If yes, which look-alike type names do you merge first (0c Step 2)?
3. **Families.** A family stays on one side. Which key (0c Step 7)?
4. **Mixed families.** 11 families span two types. Which type does such a family count as?
5. **Seed.** Which number? Write it down. It never changes after 1c.

<details><summary>Reference rules (open after you decide)</summary>

1. Dev share 0.5: about 52 dev and 52 test.
2. Stratify by type: each type gets a quota of `n_docs` times its share of the 510 contracts, at
   least 1. Merge `Affiliate Agreement` into `Affiliate_Agreements`, `Endorsement Agreement` into
   `Endorsement`, and `Joint Venture _ Filing` into `Joint Venture`.
3. Family key: the text before the first `_` or ` - ` in `doc_id`, lowercase. A whole family
   goes to one side, even if that puts its type over quota.
4. A mixed family counts as the type of its first contract, sorted by `doc_id`.
5. Seed 0.

Inside each type, the next family goes to the side that is furthest below its share in this
type. On a tie, the side that is furthest below its share overall. On a full tie, dev.
</details>

## Step 4: build `make_splits`

**Why.** The rules from Step 3 must run the same way every time, from one command.

You build it in four pieces. The first two are small helpers from your 0c findings. The last two
are your split rules: you draft them first, then compare with the reference.

### 4a: look-alike types and the family key

Update the imports at the top of `src/docintel/evals/datasets.py`:

```python
import csv
import hashlib
import json
import random
import re
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
```

The other imports (`duckdb`, `pypdf`, `connect`) stay as they are. Add this near the bottom of
`datasets.py`, just above `main`:

```python
SAME_TYPE = {  # 0c, question 1: one type, two folder names
    "Affiliate Agreement": "Affiliate_Agreements",
    "Endorsement Agreement": "Endorsement",
    "Joint Venture _ Filing": "Joint Venture",
}


def family(doc_id: str) -> str:
    """Company part of a doc_id: the text before the first "_" or " - ", lowercase."""
    return re.split(r"_| - ", doc_id, maxsplit=1)[0].lower()
```

*Python here: [`re.split`](./py/phase-0d.md#py-2).*

Here, we:

1. Map each second folder name to the first one. `SAME_TYPE.get(t, t)` later gives the merged
   name, or `t` itself when `t` is not in the dict.
2. Cut `doc_id` at the first `_` or ` - `, keep the left part, and make it lowercase. This is the
   same key as the 0c SQL, written in Python.

Checkpoint. Guess the three keys first:

```sh
uv run python -c "
from docintel.evals.datasets import family
print(family('FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT'))
print(family('Monsanto Company - SECOND A_R EXCLUSIVE AGENCY AND MARKETING AGREEMENT'))
print(family('XACCT Technologies, Inc.SUPPORT AND MAINTENANCE AGREEMENT'))"
```

```text
federatedgovernmentincomesecuritiesinc
monsanto company
xacct technologies, inc.support and maintenance agreement
```

The XACCT name has no `_` and no ` - `, so the whole name is the key. That is fine: a family of
one.

### 4b: group contracts into families

Add this below `family`:

```python
def group_families(rows: list[tuple[str, str]]) -> tuple[dict, dict]:
    """family -> [doc_id, ...] and family -> type (the type of its first doc)."""
    docs, ftype = defaultdict(list), {}
    for doc_id, ctype in rows:
        fam = family(doc_id)
        docs[fam].append(doc_id)
        ftype.setdefault(fam, SAME_TYPE.get(ctype, ctype))
    return docs, ftype
```

*Python here: [`defaultdict` and `setdefault`](./py/phase-0d.md#py-3).*

Here, we:

1. Go through `(doc_id, contract_type)` rows. They must already be sorted by `doc_id`.
2. Add each `doc_id` to its family's list in `docs`.
3. Save the family's type only the first time we see the family (`setdefault`). So a mixed
   family gets the type of its first contract. The merged type name is used.

Checkpoint. Guess: how many families, and how many types after the merge?

```sh
uv run python -c "
import duckdb
from docintel.evals.datasets import group_families
con = duckdb.connect('data/docintel.duckdb', read_only=True)
rows = con.execute('SELECT doc_id, contract_type FROM contracts ORDER BY doc_id').fetchall()
docs, ftype = group_families(rows)
print(len(docs), len(set(ftype.values())), len(docs['cardlyticsinc']), ftype['lejuholdingsltd'])"
```

```text
463 25 4 Collaboration
```

463 families, as in 0c. 25 types: the three look-alikes are merged. Cardlytics keeps its 4 parts
together. LEJU (Collaboration and License_Agreements) counts as Collaboration.

### 4c: pick a side (you draft first)

Add this below `group_families`, and fill in the body from your rule in Step 3:

```python
def pick_side(in_type: dict[str, int], overall: dict[str, int], dev_share: float) -> str:
    """The side that is furthest below its share: first inside this type, then overall."""
    ...
```

`in_type` and `overall` look like `{"dev": 3, "test": 1}`. They count the contracts already
placed, in this type and in total.

Checkpoint. Guess all three answers before you run it:

```sh
uv run python -c "
from docintel.evals.datasets import pick_side
print(pick_side({'dev': 0, 'test': 0}, {'dev': 3, 'test': 1}, 0.5))
print(pick_side({'dev': 1, 'test': 0}, {'dev': 0, 'test': 9}, 0.5))
print(pick_side({'dev': 0, 'test': 0}, {'dev': 0, 'test': 0}, 0.5))"
```

```text
test
test
dev
```

1. The type is empty (a tie), so we look at the total. Dev is ahead overall, so test.
2. Inside this type, dev is ahead. That wins, even though test is far ahead overall.
3. Everything is tied, so dev.

<details><summary>Reference <code>pick_side</code> (open after you try)</summary>

```python
def pick_side(in_type: dict[str, int], overall: dict[str, int], dev_share: float) -> str:
    """The side that is furthest below its share: first inside this type, then overall."""
    for c in (in_type, overall):
        target = dev_share * (c["dev"] + c["test"])
        if c["dev"] < target:
            return "dev"
        if c["dev"] > target:
            return "test"
    return "dev"
```

Here, we look at the type counts first, then the overall counts. `target` is how many dev
contracts there should be. If dev is below it, dev gets the next family. If dev is above it,
test does. If dev is exactly on target, we try the next counts. If all are on target, dev.
</details>

### 4d: `make_splits` (you draft first)

Add this below `pick_side`. The comments are the steps. Write the code under each one:

```python
def make_splits(
    con: duckdb.DuckDBPyConnection, seed: int = 0, n_docs: int = 100, dev_share: float = 0.5
) -> dict[str, int]:
    """Pick about n_docs contracts, stratified by type; a whole family goes to one side."""
    # 1. Read (doc_id, contract_type) from contracts, sorted by doc_id.
    # 2. Group into families. Build type -> [family, ...], going through families in sorted order.
    # 3. Make rng = random.Random(seed), and counts = {"dev": 0, "test": 0}.
    # 4. For each type, in sorted order:
    #    a. Shuffle its families with rng.
    #    b. quota = n_docs times (contracts of this type / all contracts), rounded, at least 1.
    #    c. Take families until the type reaches its quota. Each family: pick_side, then put
    #       every doc of the family on that side, and update both counts.
    # 5. CREATE OR REPLACE TABLE splits (doc_id VARCHAR PRIMARY KEY, split VARCHAR),
    #    insert the rows sorted by doc_id, and return counts.
```

*Python here: [`random.Random(seed)`](./py/phase-0d.md#py-4) ·
[`executemany` with `?`](./py/phase-0d.md#py-5).*

Now update `main` at the bottom of `datasets.py`, so `make data` writes the splits too:

```python
def main() -> None:
    cuad_dir = download_cuad()
    with connect() as con:
        n_contracts, n_labels = load_cuad(con, cuad_dir)
        counts = make_splits(con)
    print(f"Loaded {n_contracts} contracts, {n_labels} label rows")
    print(f"Splits: {counts['dev']} dev, {counts['test']} test")
```

Here, `make_splits(con)` uses the defaults: seed 0, 100 docs, dev share 0.5. If your Step 2 and
Step 3 choices differ, change the defaults in the `def` line, not here. Then the defaults are the
one place that records your decision.

Checkpoint. Close the notebook connection first (Project setup). Run it twice:

```sh
make data
```

```text
uv run python -m docintel.evals.datasets
Loaded 510 contracts, 28031 label rows
Splits: 52 dev, 52 test
```

```sh
make data
```

```text
...
Splits: 52 dev, 52 test
```

52 + 52 = 104, not 100. Whole families can push a type over its quota. Your numbers can differ
if your rules differ. They must be the same in both runs.

<details><summary>Reference <code>make_splits</code> (open after you try)</summary>

```python
def make_splits(
    con: duckdb.DuckDBPyConnection, seed: int = 0, n_docs: int = 100, dev_share: float = 0.5
) -> dict[str, int]:
    """Pick about n_docs contracts, stratified by type; a whole family goes to one side."""
    rows = con.execute("SELECT doc_id, contract_type FROM contracts ORDER BY doc_id").fetchall()
    docs, ftype = group_families(rows)
    by_type = defaultdict(list)  # type -> [family, ...]
    for fam in sorted(docs):
        by_type[ftype[fam]].append(fam)

    rng = random.Random(seed)
    counts = {"dev": 0, "test": 0}
    split_of = {}  # doc_id -> "dev" | "test"
    for ctype in sorted(by_type):
        fams = by_type[ctype]
        rng.shuffle(fams)
        quota = max(1, round(n_docs * sum(len(docs[f]) for f in fams) / len(rows)))
        in_type = {"dev": 0, "test": 0}
        for fam in fams:
            if in_type["dev"] + in_type["test"] >= quota:
                break
            side = pick_side(in_type, counts, dev_share)
            for doc_id in docs[fam]:
                split_of[doc_id] = side
            counts[side] += len(docs[fam])
            in_type[side] += len(docs[fam])

    con.execute("CREATE OR REPLACE TABLE splits (doc_id VARCHAR PRIMARY KEY, split VARCHAR)")
    con.executemany("INSERT INTO splits VALUES (?, ?)", sorted(split_of.items()))
    return counts
```

Here, we:

1. Read the rows sorted by `doc_id` (Round 2), and group them into families.
2. Build `by_type` by going through families in sorted order, so the lists start the same every
   time.
3. Go through types in sorted order. Shuffle each type's families with our own `rng`.
4. Compute the quota from the type's share of all 510 contracts. `max(1, ...)` gives tiny types
   at least one contract.
5. Take families until the quota is full. The whole family goes to the side `pick_side` chose.
6. Replace the `splits` table and insert all rows at once.
</details>

### 4e: check the split in the notebook

Open the notebook again, and run cell 1 to reconnect. Add a heading "0d checks", then three
cells.

Sizes, types and tokens per side:

```python
con.sql("""
SELECT split, count(*) AS n_docs, count(DISTINCT contract_type) AS n_types,
    sum(n_chars // 4) AS tokens
FROM splits JOIN contracts USING (doc_id)
GROUP BY split
ORDER BY split
""")
```

```
┌─────────┬────────┬─────────┬────────┐
│  split  │ n_docs │ n_types │ tokens │
├─────────┼────────┼─────────┼────────┤
│ dev     │     52 │      26 │ 617340 │
│ test    │     52 │      24 │ 753218 │
└─────────┴────────┴─────────┴────────┘
```

`n_types` counts the folder names, before the merge, so it can go above 25.

The leakage check. Guess the number of rows:

```python
con.sql("""
SELECT lower(split_part(split_part(doc_id, '_', 1), ' - ', 1)) AS family
FROM splits
GROUP BY family
HAVING count(DISTINCT split) > 1
""")
```

```
┌─────────┐
│ family  │
│ varchar │
└─────────┘
  0 rows
```

Zero rows: no family has contracts on both sides.

Examples per field, **on dev only**:

```python
from docintel.evals.datasets import FIELDS

names = [f for group in FIELDS.values() for f in group]
query = """
WITH per_doc AS (
    SELECT doc_id, category, bool_or(is_present) AS present
    FROM labels JOIN splits USING (doc_id)
    WHERE split = 'dev' AND list_contains($names, category)
    GROUP BY doc_id, category
)
SELECT category, count(*) FILTER (WHERE present) AS dev_present
FROM per_doc
GROUP BY category
ORDER BY dev_present
"""
con.sql(query, params={"names": names})
```

```
┌────────────────────────────────────┬─────────────┐
│              category              │ dev_present │
├────────────────────────────────────┼─────────────┤
│ Notice Period To Terminate Renewal │           9 │
│ Change Of Control                  │          10 │
│ Ip Ownership Assignment            │          10 │
│ Non-Compete                        │          13 │
│ Non-Transferable License           │          14 │
│ Renewal Term                       │          20 │
│ License Grant                      │          22 │
│ Cap On Liability                   │          29 │
│ Anti-Assignment                    │          41 │
│ Governing Law                      │          45 │
│ Agreement Date                     │          48 │
│ Parties                            │          52 │
└────────────────────────────────────┴─────────────┘
```

*Python here: [query parameters in `con.sql`](./py/phase-0d.md#py-5).*

Here, we use `FIELDS` from the code, so the check follows your choice. `$names` gets its value
from `params`. We only look at dev. Test stays sealed: its sizes are fine to count, its labels
are not ours to study.

If a field has fewer than about 8 dev examples, go back to Step 1 or Step 2 now. After 1c, the
split is frozen.

<details><summary>Your full additions to <code>src/docintel/evals/datasets.py</code></summary>

Imports at the top:

```python
import csv
import hashlib
import json
import random
import re
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import duckdb
from pypdf import PdfReader

from docintel.evals.store import connect
```

Below `RAW_DIR`: the `FIELDS` dict (Step 1). Above `main`: `SAME_TYPE`, `family`,
`group_families`, `pick_side` and `make_splits`, as in 4a to 4d. At the bottom:

```python
def main() -> None:
    cuad_dir = download_cuad()
    with connect() as con:
        n_contracts, n_labels = load_cuad(con, cuad_dir)
        counts = make_splits(con)
    print(f"Loaded {n_contracts} contracts, {n_labels} label rows")
    print(f"Splits: {counts['dev']} dev, {counts['test']} test")


if __name__ == "__main__":
    main()
```
</details>

## Step 5: a test for the rules that must never break

**Why.** Three things must always be true:

1. The same seed gives the same table.
2. No family is on both sides.
3. Every row is `dev` or `test`, and the counts match the table.

If one breaks, every number after it is wrong, and nothing else would tell you. The test uses a
fake `contracts` table with 33 rows. It needs no CUAD files.

Put this in `tests/test_splits.py`:

```python
"""Split tests on a tiny fake `contracts` table: 3 types, 2 families with 2 docs each."""

import pytest

from docintel.evals.datasets import family, make_splits, pick_side
from docintel.evals.store import connect

DOCS = [(f"CO{i}_2020-EX-10-AGREEMENT", ["Supply", "Service", "Hosting"][i % 3]) for i in range(30)]
DOCS += [
    ("CO0_2020-EX-10-AGREEMENT_AMENDMENT", "Supply"),  # same family as CO0
    ("Beta Corp. - Supply Agreement", "Supply"),
    ("Beta Corp. - First Amendment", "Joint Venture _ Filing"),  # family crosses types
]


@pytest.fixture
def con():
    with connect(":memory:") as c:
        c.execute("CREATE TABLE contracts (doc_id VARCHAR, contract_type VARCHAR)")
        c.executemany("INSERT INTO contracts VALUES (?, ?)", DOCS)
        yield c


def _splits(con):
    return con.execute("SELECT doc_id, split FROM splits ORDER BY doc_id").fetchall()


def test_family_key():
    assert family("CO0_2020-EX-10-AGREEMENT_AMENDMENT") == "co0"
    assert family("Monsanto Company - SECOND A_R AGREEMENT") == "monsanto company"


def test_pick_side():
    assert pick_side({"dev": 0, "test": 0}, {"dev": 3, "test": 1}, 0.5) == "test"
    assert pick_side({"dev": 1, "test": 0}, {"dev": 0, "test": 9}, 0.5) == "test"


def test_same_seed_same_splits(con):
    make_splits(con, seed=7, n_docs=12)
    first = _splits(con)
    make_splits(con, seed=7, n_docs=12)
    assert _splits(con) == first


def test_family_on_one_side(con):
    for seed in range(20):
        make_splits(con, seed=seed, n_docs=12)
        sides = {}
        for doc_id, split in _splits(con):
            sides.setdefault(family(doc_id), set()).add(split)
        assert all(len(s) == 1 for s in sides.values()), f"seed {seed}"


def test_only_dev_and_test(con):
    counts = make_splits(con, seed=0, n_docs=12)
    rows = _splits(con)
    assert {split for _, split in rows} == {"dev", "test"}
    assert counts["dev"] + counts["test"] == len(rows)
```

*Python here: [sets](./py/phase-0d.md#py-6) ·
[keyword arguments](./py/phase-0d.md#py-7) · fixtures: [0b PY-8](./py/phase-0b.md#py-8).*

Here, we:

1. Build 30 one-contract families over 3 types, plus two 2-contract families. Beta's family
   crosses types, like the 11 real ones.
2. Make a fresh `:memory:` database with only the two columns `make_splits` reads.
3. Run `make_splits` twice with seed 7 and compare the tables.
4. Try 20 seeds and check that each family has only one side. One lucky seed proves little.
5. Check the values and the counts.

Checkpoint:

```sh
make lint && make test
```

```text
All checks passed!
9 files already formatted
...
tests/test_data_load.py ....                                             [ 40%]
tests/test_smoke.py .                                                    [ 50%]
tests/test_splits.py .....                                               [100%]

============================== 10 passed in 0.53s ==============================
```

Your project should now look like this:

```
src/docintel/evals/
├── datasets.py            + FIELDS, SAME_TYPE, family, group_families, pick_side, make_splits
└── store.py
tests/
├── test_data_load.py      4 tests
├── test_smoke.py
└── test_splits.py         5 tests
notebooks/
└── 00_explore.ipynb       6 findings + Fields, Subset, Split rules + 0d checks
data/
└── docintel.duckdb        contracts, labels, splits (104 rows)
```

## Break it on purpose

**Break 1: split per contract.** In `make_splits`, move `pick_side` inside the doc loop, and
count one contract at a time:

```python
            for doc_id in docs[fam]:
                side = pick_side(in_type, counts, dev_share)
                split_of[doc_id] = side
                counts[side] += 1
                in_type[side] += 1
```

Guess which test fails, then run `make test`:

```
E           AssertionError: seed 0
FAILED tests/test_splits.py::test_family_on_one_side - AssertionError: seed 0
========================= 1 failed, 9 passed in 0.59s ==========================
```

Run `make data` and the leakage query too. `make data` still prints `52 dev, 52 test`, so the
sizes look fine. But the leakage query now lists 8 families, Cardlytics among them. Change it
back, and run `make data` again.

**Break 2: the shared random generator.** Change `rng.shuffle(fams)` to `random.shuffle(fams)`.
Guess what happens:

```
E         At index 2 diff: ('CO12_2020-EX-10-AGREEMENT', 'dev') != ('CO0_2020-EX-10-AGREEMENT', 'test')
FAILED tests/test_splits.py::test_same_seed_same_splits - AssertionError: ass...
========================= 1 failed, 9 passed in 0.59s ==========================
```

Your diff line will look different. That is the point: `random.shuffle` uses Python's shared
generator, which nobody seeded, so every run is different. Change it back.

## Experiment

This part runs no model, so there is no `run_id`. The seed and the parameters take its place.

- **Command:** `make data`.
- **Produces:** the `splits` table, about 100 rows, `(doc_id, split)`.
- **Expect:** two rows from the sizes query (dev, test), zero rows from the leakage query, and 12
  rows of dev examples per field.

Fill in E0 in `EXPERIMENTS.md`, under its existing heading. Every line should point to a number
in your notebook:

```markdown
- **Date:** <today>
- **run_id(s):** none (no model). Split: seed 0, n_docs 100, dev_share 0.5
- **Contracts chosen (N, how sampled, why):** 104 of 510; stratified by type, whole families; <why>
- **12 fields (per group) + why:** <your 4 groups, one reason per field>
- **Presence rates per field:** <all 510, and dev examples per field>
- **Dev/test split rule + sizes:** <your 5 rules>; 52 dev / 52 test
- **Known limitations of the data:** <look-alike type names, family key over-groups, 9 to 13 dev
  examples for the rarest fields, one exact duplicate (ADUROBIOTECH)>
```

## Gotchas

- **Lock error on `make data`.** The notebook holds the file. Run `con.close()` in it, or shut
  down its kernel.
- **`make lint` checks the notebook too.** ruff reads `.ipynb` files. If it says "would
  reformat", run `make fmt`.
- **Old code in the notebook.** After you change `datasets.py`, restart the notebook kernel
  before you import `FIELDS` again. The kernel keeps the old version.
- **Changing the seed or `n_docs` later.** It builds a new test set, and every earlier number now
  belongs to a different split. Decide before 1c, then never change it.
- **Looking at test labels.** Counting test contracts is fine. Reading their spans, or picking a
  seed because the test numbers look nice, is tuning on test.

## Explain back, then commit

Explain each changed file to Claude in a few sentences (the rule in `PLAN.md`): `datasets.py`
(each new function), `test_splits.py` (each test), the notebook (each decision and its
evidence), and E0. Then:

```sh
git add src/docintel/evals/datasets.py tests/test_splits.py notebooks/00_explore.ipynb EXPERIMENTS.md
git commit -m "phase 0d: fields, subset, dev/test split, E0"
```

## Conclusion

What you have now:

- `FIELDS`: the 12 categories, each with a reason backed by a number.
- `make_splits`: about 100 contracts, stratified by type, whole families on one side, the same
  every time for the same seed. `make data` builds it.
- A test for the split rules, and the E0 data card.

Phase 0 is done: data loaded, fields chosen, split fixed, data card written.

Go back to the objectives. Check that you can do each one without notes. Then answer:

1. Why does `make_splits` sort the rows before it shuffles them, if it shuffles them anyway?
2. Cardlytics has 4 contracts. What goes wrong if 2 are in dev and 2 in test?

Want more practice? Try these (optional):

1. Run `make_splits` with seeds 0 to 9 in a scratch notebook cell. How much does the dev count for
   Notice Period move? (Use a `:memory:` copy, so the real table stays seed 0.)
2. Change `pick_side` to use only the overall counts. How even is the per-type mix now?
3. Add a fourth test: a type with one contract still gets into the subset.

Checklist (`../PLAN.md`): **dev/test split, leakage, stratification** (done). **DuckDB SQL:
GROUP BY, FILTER, CTE, JOIN, quantiles** (practiced again in the checks).
