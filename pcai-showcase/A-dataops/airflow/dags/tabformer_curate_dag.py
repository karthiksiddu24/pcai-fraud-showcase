"""
DAG — tabformer_curate_dag

Submits a SparkApplication CR to clean & curate the TabFormer CSV.

Reads:    /mnt/shared/fraud-tabformer/raw/card_transaction.v1.csv (notebook view)
          /mounts/shared-volume/shared/fraud-tabformer/raw/...    (Spark pod view, same file)
Writes:   /mounts/shared-volume/shared/fraud-tabformer/curated/card_transactions/  (Parquet, year-partitioned)

Mirrors HPE's official tutorial pattern: registry_url Param defaults to AIRGAP_REGISTRY
env var, image path templated as {{ params.registry_url }}hpe-spark/spark:v3.5.5.2.1.

Trigger from the Airflow UI's ▶ button. No Git auto-sync, no FileSensor, no
auto-chained DAGs — manual UI flow per project requirements.
"""

from __future__ import annotations

import os

from airflow import DAG
from airflow.models.param import Param
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import (   # type: ignore[import-not-found]
    SparkKubernetesOperator,
)
from airflow.utils.dates import days_ago   # type: ignore[import-not-found]


default_args = {
    "owner": "haris-crimsoncloud.in",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "max_active_runs": 1,
    "retries": 0,
}


with DAG(
    dag_id="tabformer_curate_dag",
    default_args=default_args,
    schedule_interval=None,
    description="Phase A3 — clean TabFormer CSV → year-partitioned Parquet via Spark Operator",
    tags=["pcai-showcase", "phase-A", "fraud-detection", "spark"],
    params={
        # AIRGAP_REGISTRY env var is auto-injected into Airflow workers on PCAI
        # (default: 10.179.253.46/ezmeral-common/) per the global.airgap.registry config.
        "registry_url": Param(
            os.environ.get("AIRGAP_REGISTRY", "10.179.253.46/ezmeral-common/"),
            type="string",
            pattern=r"^\S+/$",
            description="Container registry URL (trailing slash required)",
        ),
    },
    render_template_as_native_obj=True,
    access_control={"All": {"can_read", "can_edit", "can_delete"}},
) as dag:

    # Submit the SparkApplication CR. Same DAG dir holds the YAML.
    submit = SparkKubernetesOperator(
        task_id="submit",
        application_file="tabformer_curate_app.yaml",
        delete_on_termination=False,           # keep the CR for inspection after success
        enable_impersonation_from_ldap_user=True,
        dag=dag,
    )
