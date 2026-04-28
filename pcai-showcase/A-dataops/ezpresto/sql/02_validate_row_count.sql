-- Validate Phase A1 + A2.
-- Expected: total_rows ≈ 24,386,900 (full IBM TabFormer dataset).

-- 1. Row count
SELECT COUNT(*) AS total_rows
FROM hivefraud.raw.card_transactions_csv;

-- 2. Sample rows
SELECT *
FROM hivefraud.raw.card_transactions_csv
LIMIT 10;

-- 3. Yearly fraud distribution sanity check
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

-- 4. Predicate-pushdown evidence — look for Filter / ScanFilter in plan output
EXPLAIN
SELECT COUNT(*)
FROM hivefraud.raw.card_transactions_csv
WHERE year = 2018;
