# Phase A2 — Register the CSV in EzPresto via a Data Volume

**Goal:** Make the TabFormer CSV at `/mnt/shared/fraud-tabformer/raw/` queryable via SQL through EzPresto, and confirm ~24M rows.

**Time:** ~15 min.
**Inputs required:** A1 complete (CSV at `/mnt/shared/fraud-tabformer/raw/card_transaction.v1.csv`).

> EzPresto can query data from object stores *or* mounted file volumes. We use the file-volume path (Hive on local filesystem) since A1 staged the CSV on `/mnt/shared`.

---

## Step 1 — Open the Query Editor (UI)

1. PCAI left nav → **Data Engineering** → **Query Editor**.
2. The editor loads with three panels: catalog tree (left), SQL editor (middle), results (bottom).
3. In the catalog tree, expand the existing `hive` (or `iceberg`, depending on your install) catalog. We'll create a schema and table here over the local filesystem.

> **If there's no `hive` or `iceberg` catalog visible** — your EzPresto needs a Hive Metastore wiring. UI: **Data Engineering** → **Data Sources** → **Structured Data** → **Hive** tile → **Create Connection**. Use:
> - Name: `hivefraud` (no underscores)
> - Hive Metastore URI: `thrift://hive-metastore.ezdata-system.svc.cluster.local:9083` (default on PCAI 1.9)
> - Leave S3 fields blank or set to placeholder — we're using local filesystem
>
> Click Connect. Catalog `hivefraud` should now appear in the Query Editor tree.

## Step 2 — Run the schema + table DDL

In the Query Editor, paste each block, **run one at a time** (Ctrl/Cmd+Enter):

### 2a. Schema rooted at the local filesystem path

```sql
CREATE SCHEMA IF NOT EXISTS hivefraud.raw
WITH (location = 'file:///mnt/shared/fraud-tabformer/raw/');
```

> **Why `file:///`** — EzPresto on PCAI supports `file://` URIs when its workers can read the path. On PCAI 1.9, EzPresto worker pods auto-mount `/mnt/shared` (same as notebooks and Spark). This is the same pattern HPE's *Financial Time Series* tutorial uses.

### 2b. External table over the CSV

The TabFormer CSV has 15 columns. Schema below matches what `preprocess_TabFormer_lp.py` expects:

```sql
CREATE TABLE IF NOT EXISTS hivefraud.raw.card_transactions_csv (
    user             VARCHAR,
    card             VARCHAR,
    year             INTEGER,
    month            INTEGER,
    day              INTEGER,
    "time"           VARCHAR,
    amount           VARCHAR,        -- "$" prefix preserved; cleaned in A3a
    use_chip         VARCHAR,
    merchant_name    VARCHAR,
    merchant_city    VARCHAR,
    merchant_state   VARCHAR,
    zip              VARCHAR,
    mcc              VARCHAR,
    errors           VARCHAR,
    is_fraud         VARCHAR
)
WITH (
    format = 'CSV',
    external_location = 'file:///mnt/shared/fraud-tabformer/raw/',
    skip_header_line_count = 1
);
```

### 2c. Validate the row count

```sql
SELECT COUNT(*) AS total_rows FROM hivefraud.raw.card_transactions_csv;
```

**Expected:** `total_rows = 24,386,900` (full TabFormer dataset).

> **First run is slow** (~30–90 s) because EzPresto scans the full CSV. Subsequent queries against derived tables in A3 will be much faster.

### 2d. Sample rows

```sql
SELECT *
FROM hivefraud.raw.card_transactions_csv
LIMIT 10;
```

You should see 10 rows: realistic credit-card-transaction shape, `amount` has `$` prefixes (cleaned later in A3a), `is_fraud` is `Yes`/`No`.

### 2e. Yearly fraud distribution sanity check

```sql
SELECT
    year,
    COUNT(*)                                            AS row_count,
    SUM(CASE WHEN is_fraud = 'Yes' THEN 1 ELSE 0 END)   AS fraud_count,
    ROUND(
      100.0 * SUM(CASE WHEN is_fraud = 'Yes' THEN 1 ELSE 0 END) / COUNT(*),
      4
    )                                                   AS fraud_pct
FROM hivefraud.raw.card_transactions_csv
GROUP BY year
ORDER BY year;
```

Expected: ~24M rows distributed across 2002–2020, fraud rate around 0.13% per year (TabFormer is highly imbalanced — the "real-world fraud detection" challenge).

### 2f. Predicate-pushdown evidence (optional but a great demo cell)

```sql
EXPLAIN
SELECT COUNT(*)
FROM hivefraud.raw.card_transactions_csv
WHERE year = 2018;
```

In the plan output, look for **`Filter`** and **`ScanFilter`** nodes — that's predicate pushdown engaging.

## Step 3 — Save your queries

PCAI's Query Editor lets you save query history:
- Click the bookmark/save icon next to a query, OR
- Use the **History** tab on the side panel to find prior runs

This is also a good demo moment: you've gone from "raw CSV file" to "SQL-queryable data warehouse" in two clicks.

---

## Done?

✅ When `SELECT COUNT(*)` returns ~24,386,900 and the yearly distribution looks credit-card-transaction-y, A2 is complete.

**Next:** [`A3-AIRFLOW-DAGS.md`](A3-AIRFLOW-DAGS.md) — orchestrate the Spark curate + preprocess pipeline via Airflow DAGs that read from `/mnt/shared/fraud-tabformer/raw/` and write to `.../curated/` and `.../gnn/`.

---

## What's different from the original S3-based plan

For reference:

- **`location = 'file:///mnt/shared/...'`** instead of `s3a://fraud-tabformer/raw/`
- No S3 endpoint, access key, or secret key in the connection
- `hive` catalog over local files instead of `iceberg` over S3 (Iceberg-on-PVC is supported but less commonly demonstrated)
- Otherwise identical SQL — `SELECT * FROM hivefraud.raw.card_transactions_csv` vs `icebergfraud.raw.card_transactions_csv`
