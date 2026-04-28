# PCAI Fraud Detection Showcase

End-to-end DataOps + MLOps reference on **HPE Private Cloud AI / AI Essentials 1.9.x** using the IBM TabFormer dataset and the NVIDIA financial-fraud-detection blueprint.

## What this demonstrates

A complete pipeline running on PCAI's native services:

- **DataOps** — Land 24M-row TabFormer CSV in object storage, federate via EzPresto, orchestrate ETL with Airflow, GPU-accelerate transforms with Spark + RAPIDS, explore with cuDF
- **MLOps** — Train a GNN+XGBoost fraud model on a Kubeflow PyTorchJob (NVIDIA NGC image), track with MLflow, register versioned models
- **Serving** — Host the trained Triton container via HPE MLIS as a managed inference endpoint with JWT auth + canary rollout
- **Validation** — Reproduce upstream blueprint metrics through PCAI's MLIS endpoint

Phase 2 (separate effort): a custom Kafka-driven streaming app, imported into PCAI via Tools & Frameworks, that scores live transactions through the MLIS endpoint.

## Build order

| Phase | What | Time |
|---|---|---|
| **0** | Cluster prep — project, GPU quota, NGC creds, endpoint capture | ~30 min |
| **A** | DataOps — object store, EzPresto, Airflow DAGs, Spark+RAPIDS, cuDF EDA | ~half day |
| **B** | MLOps — GPU notebook, PyTorchJob training, MLflow registry | ~half day |
| **C** | Serving — custom Triton image, MLIS packaged model + deployment | ~2 hours |
| **D** | Validation — F1 reproduction + single-transaction inference + SHAP | ~1 hour |

Start at [00-bootstrap/PHASE-0-CHECKLIST.md](00-bootstrap/PHASE-0-CHECKLIST.md) and follow the numbered files in each phase directory.

## Repository layout

```
pcai-showcase/
├── 00-bootstrap/        # Phase 0 — admin tasks (project, GPU quota, NGC, .env)
├── A-dataops/           # Phase A — Airflow DAGs, Spark apps, EzPresto SQL, cuDF EDA notebook
├── B-mlops/             # Phase B — training notebook, PyTorchJob, MLflow wrapper, Import Framework chart
├── C-serving/           # Phase C — MLIS packaged model setup, KServe alt, validation notebook
├── E-streaming-app/     # Phase 2 (next iteration)
├── docs/                # Architecture, value-prop, demo script
└── README.md            # this file
```

## RAPIDS visibility

Three places the customer sees RAPIDS in action:
1. **Spark+RAPIDS Accelerator** — A3 curate DAG runs on GPU-Spark (`hpe-spark/spark-3.5.2:v3.5.2.1.1`)
2. **cuDF** — A4 EDA notebook does GPU-accelerated pandas-equivalent ops on 24M rows
3. **cuGraph** — B3 training image (`nvcr.io/nvidia/cugraph/financial-fraud-training:2.0.0`) builds the GNN on GPU

Plus cuDF inside the Triton Python backend at inference time (C-serving).

## Reused upstream code (not modified)

- `../financial-fraud-usage-v2.ipynb` — sibling reference notebook
- `preprocess_TabFormer_lp.py` (from upstream blueprint) — invoked verbatim by the Airflow preprocess pod
- `triton/Dockerfile` (from upstream blueprint) — copied to `B-mlops/triton/` and retagged
- NGC image `nvcr.io/nvidia/cugraph/financial-fraud-training:2.0.0`

## Plan reference

The full plan with reasoning, MLIS-vs-KServe decision, and verification criteria lives at:
`C:\Users\karth\.claude\plans\hpe-a00aie19hen-us-hpe-ai-essentials-so-zany-frog.md`
