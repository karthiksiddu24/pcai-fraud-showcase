"""
PySpark job: TabFormer CSV → year-partitioned Parquet on the shared PVC.

Submitted via tabformer_curate_dag.py + tabformer_curate_app.yaml.
Runs inside the HPE-curated Spark image (v3.5.5.2.1) on the cluster's
Spark Operator. Reads/writes the kubeflow-shared-pvc mounted at
/mounts/shared-volume/shared.

Drop this file at /mnt/shared/fraud-tabformer/scripts/ from a notebook;
SparkApplication picks it up via mainApplicationFile=local:///....

After this DAG completes, the curated Parquet is at
  /mnt/shared/fraud-tabformer/curated/card_transactions/year=YYYY/...
A separate step registers these files into the icebergfraud catalog
via EzPresto (CREATE TABLE + system.add_files).

Usage (in tabformer_curate_app.yaml's spec.arguments):
    --raw      file:///mounts/shared-volume/shared/fraud-tabformer/raw/card_transaction.v1.csv
    --curated  file:///mounts/shared-volume/shared/fraud-tabformer/curated/card_transactions
"""

import argparse
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType,
)


RAW_SCHEMA = StructType([
    StructField("user", StringType()),
    StructField("card", StringType()),
    StructField("year", IntegerType()),
    StructField("month", IntegerType()),
    StructField("day", IntegerType()),
    StructField("time", StringType()),
    StructField("amount", StringType()),
    StructField("use_chip", StringType()),
    StructField("merchant_name", StringType()),
    StructField("merchant_city", StringType()),
    StructField("merchant_state", StringType()),
    StructField("zip", StringType()),
    StructField("mcc", StringType()),
    StructField("errors", StringType()),
    StructField("is_fraud", StringType()),
])


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True, help="file:// URL to raw CSV")
    p.add_argument("--curated", required=True, help="file:// URL to curated Parquet output dir")
    return p.parse_args()


def main():
    args = parse_args()
    t0 = time.time()

    spark = (
        SparkSession.builder
        .appName("tabformer-curate")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    print(f"[info] reading {args.raw}")

    df = (
        spark.read
        .option("header", "true")
        .schema(RAW_SCHEMA)
        .csv(args.raw)
    )

    cleaned = (
        df
        .withColumn("amount",
                    F.regexp_replace(F.col("amount"), r"[\$,]", "").cast(DoubleType()))
        .withColumn("is_fraud",
                    F.when(F.col("is_fraud") == "Yes", 1).otherwise(0).cast(IntegerType()))
        .withColumn("zip",
                    F.when(F.col("zip").isNull() | (F.col("zip") == ""), "0")
                     .otherwise(F.col("zip")))
        .withColumn("merchant_state",
                    F.when(F.col("merchant_state").isNull() | (F.col("merchant_state") == ""), "XX")
                     .otherwise(F.col("merchant_state")))
        .withColumn("errors",
                    F.when(F.col("errors").isNull(), "").otherwise(F.col("errors")))
    )

    total = cleaned.count()
    fraud = cleaned.where(F.col("is_fraud") == 1).count()
    print(f"[info] total rows: {total:,}")
    print(f"[info] fraud rows: {fraud:,} ({100.0*fraud/total:.4f}%)")

    print(f"[info] writing year-partitioned Parquet → {args.curated}")
    (
        cleaned.write
        .mode("overwrite")
        .partitionBy("year")
        .format("parquet")
        .save(args.curated)
    )
    print(f"[info] elapsed {(time.time()-t0)/60:.1f} min")

    spark.stop()


if __name__ == "__main__":
    main()
