-- Register the raw TabFormer CSV at /mnt/shared/fraud-tabformer/raw/ as an
-- external EzPresto table (hivefraud catalog, raw schema).
--
-- Run via: PCAI UI > Data Engineering > Query Editor.
--
-- Prerequisites:
--   - Phase A1 complete: card_transaction.v1.csv is at
--     /mnt/shared/fraud-tabformer/raw/card_transaction.v1.csv
--   - The 'hivefraud' Hive catalog is wired up in EzPresto
--     (see A2-EZPRESTO-CATALOG.md "Step 1" — uses the cluster's preinstalled
--     Hive Metastore at thrift://hive-metastore.ezdata-system.svc.cluster.local:9083)
--
-- Naming note: EzPresto rejects underscores in catalog/schema names with certain
-- configs; we use 'hivefraud' (no underscore).

CREATE SCHEMA IF NOT EXISTS hivefraud.raw
WITH (location = 'file:///mnt/shared/fraud-tabformer/raw/');

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
    is_fraud         VARCHAR         -- "Yes"/"No"; cleaned in A3a
)
WITH (
    format = 'CSV',
    external_location = 'file:///mnt/shared/fraud-tabformer/raw/',
    skip_header_line_count = 1
);
