# Phase A1 — Stage TabFormer in your notebook PVC

**Goal:** Get the IBM TabFormer credit-card transaction dataset into your project's persistent volume so all downstream phases (Spark, preprocess, training, serving) can read it via standard POSIX paths.

**Time:** ~30 min (plus dataset download time).
**Inputs required:** Phase 0 complete (project ready, Tools & Frameworks tiles green).

> **Why PVC and not S3?** Original plan used S3, but the cluster's user-token rotator isn't refreshing — local-s3 proxy rejects per-user uploads. We pivoted to PVC-only Phase 1. Same demo value for all phases except cross-bucket federation. See the README's "Storage strategy" note.

---

## Step 1 — Download the TabFormer dataset to your laptop

The dataset is on IBM Box (linked from https://github.com/IBM/TabFormer):

1. Open https://ibm.ent.box.com/v/tabformer-data/folder/130747715605
2. Download `transactions.tgz` (~266 MB compressed).
3. Untar locally — using PowerShell:

   ```powershell
   New-Item -ItemType Directory -Force -Path f:\hpe\fraud_detection\data\TabFormer\raw
   cd f:\hpe\fraud_detection\data\TabFormer\raw
   tar -xzvf $HOME\Downloads\transactions.tgz
   ```

   This produces `card_transaction.v1.csv` (~2.4 GB uncompressed).

4. Verify size:

   ```powershell
   Get-Item .\card_transaction.v1.csv | Select-Object Name, @{N='SizeGB';E={[math]::Round($_.Length/1GB,2)}}
   ```

   Expected: **~2.4 GB**.

## Step 2 — Open a Kubeflow notebook with a generous PVC

The dataset is large; we need a workspace volume that can hold the raw CSV (2.4 GB) + curated Parquet (~1 GB) + GNN files (~500 MB) + headroom = aim for **8 GiB**.

### UI clicks

1. PCAI left nav → **Tools & Frameworks** → click **Open** on the **Kubeflow** tile.
2. In Kubeflow Central Dashboard → **Notebooks** (left nav).
3. Click **+ New Notebook** (top-right).
4. Form:
   - **Name:** `fraud-pipeline` (lowercase, dashes only)
   - **Image:** `jupyter-data-science:<latest>` (CPU only — saves GPU quota for training)
   - **CPU:** 2
   - **Memory:** `4Gi`
   - **GPUs:** 0
   - **Workspace Volume:**
     - Type: **New**
     - Name: `fraud-pipeline-workspace`
     - Size: **`10Gi`** (the default is too small for 2.4 GB CSV + intermediates)
     - Mount path: `/home/jovyan` (default, leave as-is)
   - **Data Volumes:** none for now
5. Click **Launch**. Wait for **Running**, click **Connect**.

> **If your project already has a notebook from earlier debugging:** stop and delete it (its workspace PVC is too small, only 1 Gi by default). Recreate with the 10Gi PVC above. The new notebook will be your home for the entire pipeline.

## Step 3 — Drag the CSV into the notebook (UI)

In JupyterLab:

1. In the left file-browser, you're in `/home/jovyan` by default. Make a `data/` folder:
   - File browser → right-click empty area → **New Folder** → name `data`
   - Double-click into `data` → make subfolder `raw`
2. **Drag and drop** `card_transaction.v1.csv` (2.4 GB) from your Windows File Explorer **into the JupyterLab file browser** (while inside `data/raw/`).
3. Wait for the upload progress bar (bottom of JupyterLab) to complete. ~5–20 min depending on your link.

**Alternative if drag-drop is slow/flaky:** Click the **Upload** button (up-arrow icon at the top of the file browser) and select the file. Same result, more robust for large files.

## Step 4 — Verify the file is in place

In the JupyterLab terminal (File → New → Terminal):

```bash
ls -lh ~/data/raw/
echo "---"
md5sum ~/data/raw/card_transaction.v1.csv
echo "---"
head -2 ~/data/raw/card_transaction.v1.csv
```

You should see:
- File size ~2.4 GB
- A header row + one data row at the end (`User,Card,Year,Month,Day,...`)

## Step 5 — Replicate to /mnt/shared so DAGs & Spark pods can read it

The notebook's `/home/jovyan` is mounted from a personal PVC that's **only accessible to your notebook pod**. Spark Operator and Airflow KubernetesPodOperator pods run in the same namespace but mount **different** volumes — they can read from the project's `/mnt/shared` directory, which is the canonical "Data Volume" location HPE tutorials use.

In the JupyterLab terminal:

```bash
# /mnt/shared is mounted in every PCAI notebook + Spark/preprocess pod by default
ls /mnt/shared/

# Make a project folder under shared
mkdir -p /mnt/shared/fraud-tabformer/raw

# Copy (the data needs to live under /mnt/shared so DAG pods can see it)
cp ~/data/raw/card_transaction.v1.csv /mnt/shared/fraud-tabformer/raw/

# Verify
ls -lh /mnt/shared/fraud-tabformer/raw/
```

**This is the canonical path for Phase A onwards:** `/mnt/shared/fraud-tabformer/{raw,curated,gnn,models}/` — analogous to bucket prefixes but POSIX.

> **What if `/mnt/shared` doesn't exist?** Some PCAI installs name it differently (`/mounts/shared`, `/shared`). Run `mount | grep -E "shared|nfs|datafabric"` to find the equivalent path on your install. Tell me what comes up if it's not standard.

---

## Done?

✅ When `ls -lh /mnt/shared/fraud-tabformer/raw/card_transaction.v1.csv` shows ~2.4 GB, A1 is complete.

**Next:** [`A2-EZPRESTO-CATALOG.md`](A2-EZPRESTO-CATALOG.md) — register the CSV in EzPresto via a Data Volume connection (UI), confirm ~24M rows.

---

## What's different from the original S3-based plan

For your reference (and so future you can re-do this with S3 once the cluster's auth fixes):

- **No boto3 calls** — file is on a real filesystem
- **No `AUTH_TOKEN` needed** — POSIX permissions handle it
- **No Data Source UI registration for object stores** — the data lives where Spark/Airflow already look
- **Path translation:** mentally substitute `s3://fraud-tabformer/<prefix>/<key>` → `/mnt/shared/fraud-tabformer/<prefix>/<key>` everywhere downstream
