# Python for Phase 2b3

This file explains the little new Python (and SQL) in Part 2b3. This part adds no code to `src/`. The
`gap` cell and its `rng.choices` are in 1d ([PY-2](./phase-1d.md#py-2)), and f-strings are in 1b
([PY-3](./phase-1b.md#py-3)).

<a id="py-1"></a>
## PY-1. Run names with f-strings

```python
RUN = "<run_id>"
print("E2.1 blank-v minus first:", gap(f"{RUN}-first-blank-v", f"{RUN}-first"))
```

1. `f"{RUN}-first"` puts the value of `RUN` in the text. With `RUN = "20261107-222125"`, it gives
   `"20261107-222125-first"`.
2. That is the same name `derive` made: `f"{parent}-{name}"`. So you type the `run_id` once.
3. `print` with commas prints each value with a space between them. In JS: `console.log(a, b)`.

In JS: `` `${RUN}-first` ``.

<a id="py-2"></a>
## PY-2. A `"""` string across many lines

```python
con.execute("""
    SELECT doc_id[:20], field, tp, fp FROM issues JOIN scores USING (run_id, doc_id, field)
    WHERE run_id = ? AND issues.rule = 'quote_missing'
""", [f"{RUN}-first"]).fetchall()
```

1. Three quotes start a string that can hold new lines. Three quotes end it.
2. The spaces and new lines are part of the string. SQL does not care about them.
3. The `?` is filled from the list after the string, like in every query since 0b.

In JS, it is a template string with backticks, but with no `${}` inside.

<a id="py-3"></a>
## PY-3. `doc_id[:20]` in DuckDB SQL

```sql
SELECT doc_id[:20], field, tp, fp FROM ...
```

DuckDB can slice text like Python. `doc_id[:20]` keeps the first 20 characters. It keeps the output
short, because CUAD names are long.

Example: `CORALGOLDRESOURCES,LTD_05_28_2020-EX-4.1-CONSULTING AGREEMENT` becomes
`CORALGOLDRESOURCES,L`. In standard SQL, it is `left(doc_id, 20)`, which DuckDB also has.

<a id="py-4"></a>
## PY-4. `issues.rule`: one name in two tables

```sql
FROM issues JOIN scores USING (run_id, doc_id, field)
WHERE run_id = ? AND issues.rule = 'quote_missing'
```

Both tables have a `rule` column. In `issues`, it is the check that fired. In `scores`, it is the
scoring rule (1b2). With only `rule`, DuckDB stops:

```text
_duckdb.BinderException: Binder Error: Ambiguous reference to column name "rule" (use: "issues.rule" or "scores.rule")
```

`issues.rule` says which one. The columns in `USING (...)` are shared, so `run_id` needs no table name.
