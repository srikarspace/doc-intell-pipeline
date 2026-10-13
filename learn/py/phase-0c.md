# Python for Phase 0c

This file explains the notebook and the SQL in Part 0c. Read one section when the main doc links
to it. The JS examples use lodash (`_`), a JS helper library for lists and objects.

<a id="py-1"></a>
## PY-1. Jupyter cells and the kernel

A notebook is a list of cells. When you run a cell, the code goes to the **kernel**. The kernel is
one Python program that stays alive while the notebook is open. So variables live on between
cells:

```python
con = duckdb.connect("../data/docintel.duckdb", read_only=True)   # cell 1
con.sql("SELECT count(*) AS n_contracts FROM contracts")          # cell 2 uses con
```

Things to know:

- **The last line is shown.** If the last line of a cell is a value, Jupyter prints it below the
  cell. In JS, it is like the browser console printing the value of the last expression.
- **Order matters, not position.** If you run cell 5 before cell 1, `con` does not exist yet. The
  number left of a cell (`[3]`) shows the order you ran it in.
- **Restart to check.** "Restart Kernel and Run All Cells" runs everything from the top, fresh.
  If it works, your notebook works for anyone.
- **The folder.** The kernel starts in the notebook's folder (`notebooks/`). That is why the path
  starts with `../`.
- **Your code changes.** If you change a file in `src/` after you imported it, restart the
  kernel. The kernel keeps the old version in memory.

<a id="py-2"></a>
## PY-2. DuckDB from Python

There are two ways to run a query. You already used both in 0b.

```python
con.sql("SELECT count(*) AS n_contracts FROM contracts")              # a table you can look at
con.execute("SELECT count(*) FROM contracts").fetchone()               # (510,), a Python tuple
```

- `con.sql(...)` gives a **relation**. It prints as a nice table. Use it to look at data.
- `con.execute(...).fetchall()` gives a list of tuples. Use it when Python code needs the values.
  `fetchone()` gives only the first row.
- `.show(max_rows=50)` prints a relation with more rows. By default you see 20.

`read_only=True` opens the file for reading only. Many readers can share a file. A writer must be
alone, so `make data` cannot start while any notebook holds the file.

`"""..."""` is a string that can span many lines. Like a JS template string with backticks, but
without `${}`. We use it to write SQL over several lines.

<a id="py-3"></a>
## PY-3. GROUP BY and aggregates

`GROUP BY` puts rows with the same value in one group. Then each aggregate (`count`, `avg`, `max`,
`sum`) runs once per group. You get one row per group.

```sql
SELECT contract_type, count(*) AS n
FROM contracts
GROUP BY contract_type
```

The same in JS with lodash:

```js
_.countBy(contracts, c => c.contract_type)        // { Maintenance: 34, ... }
```

For anything other than counting, think `_.groupBy` then `_.mapValues`:

```js
_.mapValues(_.groupBy(rows, r => r.category), g => _.meanBy(g, 'n_spans'))
```

The rule from Break 2: every column in `SELECT` must be in `GROUP BY` or inside an aggregate.
Otherwise DuckDB does not know which value of that column to show.

Order of the parts in a query: `SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY
... LIMIT`. You can leave parts out, but not change the order.

<a id="py-4"></a>
## PY-4. FILTER and bool_or

**`FILTER (WHERE ...)`** makes one aggregate look at only some rows. The other aggregates in the
same query still see all rows.

```sql
count(*) FILTER (WHERE n_chars // 4 <= 32000) AS fits_32k,
count(*) FILTER (WHERE n_chars // 4 > 32000) AS over_32k,
```

In JS: `_.filter(contracts, c => c.n_chars / 4 <= 32000).length`, but two of them in one pass.

**`bool_or(x)`** is true if at least one row in the group has `x` true. In JS: `_.some(group,
'is_present')`. Its partner `bool_and` is `_.every`.

```sql
SELECT doc_id, category, bool_or(is_present) AS present
FROM labels
GROUP BY doc_id, category
```

**`present::INT`** changes the type: `true` becomes 1, `false` becomes 0. `::` is DuckDB's way to
convert a value. Then `avg` of 1s and 0s is the share of 1s.

<a id="py-5"></a>
## PY-5. CTEs: `WITH name AS (...)`

A CTE gives a name to a middle result. The main query then reads from it like a table. It lives
only inside this one query.

```sql
WITH per_doc AS (
    SELECT doc_id, category, bool_or(is_present) AS present
    FROM labels
    GROUP BY doc_id, category
)
SELECT category, round(100 * avg(present::INT), 1) AS pct_present
FROM per_doc
GROUP BY category
```

In JS, it is like naming a step with `const`:

```js
const perDoc = groupByDocAndCategory(labels)       // the CTE
const result = rateByCategory(perDoc)              // the main query
```

You can chain several CTEs with commas: `WITH fam AS (...), sizes AS (... FROM fam ...)`. Each
one can read the ones before it. Use a CTE when you need to group twice, like "per contract, then
per category".

<a id="py-6"></a>
## PY-6. JOIN USING and HAVING

**`JOIN ... USING (doc_id)`** matches each row on the left to the rows on the right with the same
`doc_id`, and puts their columns side by side. `doc_id` shows up only once in the result.

```sql
FROM fam JOIN contracts USING (doc_id)
```

In JS with lodash:

```js
const byId = _.keyBy(contracts, 'doc_id')
fam.map(f => ({ ...f, ...byId[f.doc_id] }))
```

Rows with no match on the other side are dropped. That is an **inner join**, the default.

**`HAVING`** filters groups, after `GROUP BY`. `WHERE` filters rows, before `GROUP BY`. So `WHERE`
cannot use `count(...)`, but `HAVING` can:

```sql
GROUP BY family
HAVING n_types > 1
```

In JS: `_.pickBy(groups, g => countTypes(g) > 1)`.

<a id="py-7"></a>
## PY-7. Quantiles: median and p90

A quantile sorts the values and picks the one at a given place. 0.5 is the middle (median). 0.9
is 90% of the way up.

```sql
quantile_cont(n_chars // 4, [0.5, 0.9])::INT[] AS p50_p90
```

In JS, roughly:

```js
const s = _.sortBy(tokens)
const p90 = s[Math.floor(0.9 * (s.length - 1))]
```

Things to know:

- `quantile_cont` can give a value between two real values (it mixes them). That is why we cast
  with `::INT`. `quantile_disc` always picks a real value.
- Give one number to get one value. Give a list `[0.5, 0.9]` to get a list.
- `median(x)` is the same as `quantile_cont(x, 0.5)`.
- Why not `avg`? One 338k-character contract moves the average a lot. It moves the median very
  little.

<a id="py-8"></a>
## PY-8. String functions

The ones we use in 0c, next to JS:

| DuckDB | JS |
|---|---|
| `split_part(doc_id, '_', 1)` | `doc_id.split('_')[0]` (DuckDB counts from 1) |
| `lower(x)` | `x.toLowerCase()` |
| `length(span_text)` | `span_text.length` |
| `doc_id LIKE 'FEDERATED%'` | `doc_id.startsWith('FEDERATED')` |
| `n_chars // 4` | `Math.floor(n_chars / 4)` |

`LIKE` patterns: `%` means "any text, any length". `_` means "exactly one character". So
`LIKE 'Affiliate_%'` would also match `Affiliate Agreement`, because `_` matches the space.

Strings in SQL use single quotes: `'Supply'`. Double quotes mean a column name.
