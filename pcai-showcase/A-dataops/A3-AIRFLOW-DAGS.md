# Phase A3 — Airflow + Spark Operator (airgap-friendly)

**Goal:** Trigger a Spark+RAPIDS curate job from Airflow's UI. Clean the raw CSV, produce a year-partitioned Hive/Parquet table for EzPresto and downstream training.

**Time:** ~30 min for first-time setup; 5 min per re-trigger.
**Inputs required:**
- A1 + A2 complete (CSV at `/mnt/shared/fraud-tabformer/raw/`, queryable via EzPresto)
- A free GitHub account (any account works — you'll create a tiny public repo)
- The cluster's `AIRGAP_REGISTRY` env var auto-set (already present per your Airflow config: `10.179.253.46/ezmeral-common/`)

---

## What we're doing & why

Your cluster is airgapped, but **GitHub IS reachable** (verified via the working `spark_read_csv_write_parquet_fts` tutorial DAG). PCAI's Airflow pulls DAGs from a Git URL — we just need to point it at our repo instead of the HPE tutorial repo.

We're **not** using:
- Internal Git server (you don't have one)
- Custom Docker images on Harbor (you don't have push access)
- KFP / KubernetesPodOperator with non-HPE images (airgap risk)
- FileSensor (Airflow workers don't mount `/mnt/shared`)

We **are** using:
- The cluster's existing HPE-curated Spark image at `${AIRGAP_REGISTRY}hpe-spark/spark:v3.5.5.2.1`
- The cluster's existing `kubeflow-shared-pvc` (mounted at `/mounts/shared-volume/shared` in Spark pods, same as `/mnt/shared` in your notebook)
- One PySpark script you drop on the shared PVC via JupyterLab
- One Airflow DAG + one SparkApplication YAML pushed to GitHub

---

## Step 1 — Create your GitHub repo (UI, ~2 min)

1. Go to https://github.com (sign up if you don't have an account — free, 30 sec).
2. Click **+** (top right) → **New repository**.
3. Name: `pcai-fraud-showcase`
4. Visibility: **Public** (simplest — no auth tokens needed). Private works too but adds a PAT step.
5. **Don't** add README, .gitignore, or license — leave the repo empty.
6. **Create repository**.
7. Copy the URL: `https://github.com/<your-username>/pcai-fraud-showcase.git`

## Step 2 — Push your DAGs (terminal, ~2 min)

On your laptop:

```powershell
cd f:\hpe\fraud_detection
git init
git add pcai-showcase/
git commit -m "PCAI fraud detection showcase — Phase A"
git branch -M main
git remote add origin https://github.com/<your-username>/pcai-fraud-showcase.git
git push -u origin main
```

If git asks for auth, use a personal access token (GitHub Settings → Developer settings → Personal access tokens → Generate → `repo` scope).

Confirm by visiting your repo URL in browser — you should see the `pcai-showcase/` folder with `A-dataops/airflow/dags/tabformer_curate_dag.py` inside.

## Step 3 — Drop the PySpark script on the shared PVC (UI, ~30 sec)

The DAG tells SparkApplication to read its mainApplicationFile from `/mounts/shared-volume/shared/fraud-tabformer/scripts/tabformer_csv_to_iceberg.py`. That's the same place your notebook sees as `/mnt/shared/fraud-tabformer/scripts/`.

In the JupyterLab terminal:

```bash
mkdir -p /mnt/shared/fraud-tabformer/scripts
cp /home/jovyan/<wherever-you-cloned>/pcai-showcase/A-dataops/airflow/spark-apps/tabformer_csv_to_iceberg.py \
   /mnt/shared/fraud-tabformer/scripts/

# Or simpler: drag-and-drop the .py file from Windows Explorer into JupyterLab
# pointed at /mnt/shared/fraud-tabformer/scripts/
ls -lh /mnt/shared/fraud-tabformer/scripts/
```

You should see `tabformer_csv_to_iceberg.py` listed.

## Step 4 — Point PCAI Airflow at your repo (UI, ~2 min)

1. PCAI left nav → **Tools & Frameworks**.
2. **Airflow** tile → **⋮** → **Configure**.
3. The values.yaml editor opens. Find the `dags.git` block (under `airflow-cluster-ua.airflowCluster.dags.git`). Change:

   ```yaml
   dags:
     git:
       repo: "https://github.com/<your-username>/pcai-fraud-showcase.git"
       branch: "main"
       subDir: "pcai-showcase/A-dataops/airflow/dags"
       # Leave proxy/cred/certificate as empty defaults
   ```

   Three changes: `repo`, `branch` (`main` instead of `aie-1.9.0`), `subDir`.

4. Click **Configure** at the bottom.
5. Wait ~30–60 s. PCAI Airflow re-syncs.
6. PCAI → **Tools & Frameworks** → **Airflow** → **Open**.
7. The DAG list should now show **`tabformer_curate_dag`** (the HPE tutorial DAGs are gone — they came from the HPE repo we just replaced).

> If `tabformer_curate_dag` doesn't appear within 2 min, click the small **🔄 refresh** button on the Airflow page header. If still missing, check the troubleshooting section.

## Step 5 — Trigger the DAG (UI)

1. In Airflow → click `tabformer_curate_dag`.
2. Top-right: click the ▶ **Trigger DAG** button.
3. In the Trigger DAG popup, the form shows the `registry_url` Param pre-filled with `10.179.253.46/ezmeral-common/`. Leave it as-is.
4. Click **Trigger**.
5. Click the new run → **Graph** view → click the `submit` task → **Logs** tab to follow.

**What happens behind the scenes:**
- Airflow renders `tabformer_curate_app.yaml` with your registry URL substituted in
- Submits the SparkApplication CR to the cluster's Spark Operator (HPE custom: `sparkoperator.hpe.com/v1beta2`)
- Spark Operator pulls the HPE-curated Spark image from your airgap registry
- Driver + 2 executors come up, mount the shared PVC, read the CSV, write Parquet
- DAG task completes when SparkApplication is in COMPLETED state

**Expected runtime:** 3–8 minutes on CPU (RAPIDS GPU acceleration is commented out in the YAML — see "Enable GPU later" below).

## Step 6 — Watch & verify (UI, parallel)

While the DAG runs, in another tab open **Tools & Frameworks → Spark Operator → Open**. You'll see the `tabformer-curate-<timestamp>` SparkApplication. Click into it → driver/executor pods listed, logs visible.

After the DAG goes green, verify in EzPresto Query Editor:

```sql
SELECT COUNT(*) FROM hivefraud.curated.card_transactions;
SELECT year, COUNT(*) AS n, SUM(is_fraud) AS fraud
FROM hivefraud.curated.card_transactions
GROUP BY year ORDER BY year;
```

Expected: ~24,386,900 rows; per-year breakdown with `is_fraud` now an INTEGER (0/1) and `amount` a DOUBLE (no `$`).

Also from the notebook terminal:

```bash
ls /mnt/shared/fraud-tabformer/curated/card_transactions/
# Should show year=2002/, year=2003/, ... directories with .parquet files inside
```

---

## Phase A3b — Preprocess (notebook cell)

Why notebook instead of DAG: a custom preprocess Docker image needs a Harbor we can push to, which we don't have. Running the upstream blueprint code directly in the notebook avoids the image build entirely. **No PCAI value lost** — the same pandas/sklearn code runs, just in a different pod.

### Step 6a — Clone the upstream blueprint code into shared PVC

In the JupyterLab terminal:

```bash
mkdir -p /mnt/shared/fraud-tabformer/blueprint-src
cd /mnt/shared/fraud-tabformer/blueprint-src
git clone --depth 1 https://github.com/NVIDIA-AI-Blueprints/financial-fraud-detection.git .
ls src/preprocess_TabFormer_lp.py
```

(Your laptop's git push to GitHub already proved github.com works from this network. If the cluster's notebook can't clone directly, do this on your laptop and drag the `src/` folder into JupyterLab.)

### Step 6b — Run preprocess as a notebook cell

Create a new notebook `A3b_preprocess.ipynb` in your `~/` (home) folder. Paste:

```python
# Cell 1 — install missing deps if not already present
!pip install -q torch-geometric pyarrow

# Cell 2 — set up paths the upstream code expects
import os, shutil, sys
from pathlib import Path

WORK = Path.home() / "preprocess-work"
RAW = WORK / "data" / "TabFormer" / "raw"
GNN_OUT = WORK / "data" / "TabFormer" / "gnn"
RAW.mkdir(parents=True, exist_ok=True)

# Reassemble curated Parquet → single CSV at the path the upstream code expects.
# (preprocess_TabFormer_lp reads card_transaction.v1.csv specifically)
import pandas as pd, glob
parts = sorted(glob.glob("/mnt/shared/fraud-tabformer/curated/card_transactions/year=*/*.parquet"))
print(f"reassembling {len(parts)} curated Parquet parts")
csv_path = RAW / "card_transaction.v1.csv"
write_header = True
total = 0
with csv_path.open("w") as fh:
    for p in parts:
        df = pd.read_parquet(p)
        df.to_csv(fh, index=False, header=write_header)
        write_header = False
        total += len(df)
print(f"wrote {total:,} rows to {csv_path}")

# Cell 3 — call upstream preprocess_data() unchanged
sys.path.insert(0, "/mnt/shared/fraud-tabformer/blueprint-src/src")
from preprocess_TabFormer_lp import preprocess_data
user_mask, mx_mask, tx_mask = preprocess_data(str(WORK / "data" / "TabFormer"))
print(f"feature masks — user={len(user_mask)} merchant={len(mx_mask)} tx={len(tx_mask)}")

# Cell 4 — copy outputs to shared PVC so training/eval can find them
import shutil
DEST = Path("/mnt/shared/fraud-tabformer/gnn")
if DEST.exists():
    shutil.rmtree(DEST)
shutil.copytree(GNN_OUT, DEST)
print(f"copied GNN heterograph → {DEST}")
print(list(DEST.iterdir()))
```

**Expected runtime:** 5–10 min. Pandas peaks at ~12 GiB; if your notebook OOMs, increase memory in the Kubeflow notebook spec (Stop → edit → 24Gi → Start).

### Verify

```bash
ls -lhR /mnt/shared/fraud-tabformer/gnn/ | head -30
```

You should see `nodes/`, `edges/`, `test_gnn/` subfolders with CSVs.

---

## Done?

✅ When `hivefraud.curated.card_transactions` shows ~24M rows AND `/mnt/shared/fraud-tabformer/gnn/edges/user_to_merchant.csv` exists, Phase A3 is complete.

**Next:** [`A4-CUDF-EDA.md`](A4-CUDF-EDA.md) — RAPIDS showcase #2: GPU-accelerated EDA with cuDF on the curated dataset.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Airflow shows no DAGs after Step 4 | Wrong `subDir`, or repo private without PAT | Re-open Configure; verify `subDir: "pcai-showcase/A-dataops/airflow/dags"` matches your repo layout |
| `submit` task fails: ImagePullBackOff | Spark image tag wrong on this cluster | Open the working `spark_read_csv_write_parquet_fts` DAG → Code tab; copy the exact image path; update `tabformer_curate_app.yaml` |
| `submit` task fails: "kubeflow-shared-pvc not found" | PVC has different name on this install | `kubectl get pvc -n <your-namespace>`; replace `claimName` in YAML |
| Spark driver fails: "no such file" on raw CSV | `/mnt/shared` and `/mounts/shared-volume/shared` don't actually share storage | Run `mount \| grep shared` in notebook + Spark driver pod logs to compare; may need different PVC mount |
| Spark fails: Hive Metastore connection refused | Hive metastore service has different DNS name | Check Spark Operator's example tutorial YAML for the right `hive.metastore.uris` |
| EzPresto Query Editor: `hivefraud.curated.card_transactions` not visible | Hive metastore catalog cache | In Query Editor: `CALL system.refresh_metadata('hive.curated.card_transactions')` or wait 60 s |
| Notebook OOMs during preprocess (Cell 3) | 24M rows + pandas peaks ~12 GiB | Stop notebook → edit → bump Memory to 24Gi → Start |

### Enable GPU+RAPIDS later

`tabformer_curate_app.yaml` has the GPU+RAPIDS sparkConf block commented out at the bottom. Once you've confirmed the HPE Spark image at `v3.5.5.2.1` includes the RAPIDS jars (`docker run --rm $IMAGE ls /opt/sparkRapidsPlugin/` on a node), uncomment those lines, re-push to your repo, and re-trigger the DAG. Expect 3–10× speedup on the CSV scan.

If the image doesn't include RAPIDS jars, ask your cluster admin if there's a different image tag for the GPU variant — common HPE convention is `<image>:<tag>-gpu` or a separate path.
