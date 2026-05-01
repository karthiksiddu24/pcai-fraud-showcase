# Phase 0 — Cluster prep (UI-first)

You do this once. Everything in Phases A–D depends on these prerequisites.

**Time:** ~30 min.
**Role required:** Private Cloud AI Administrator (you have this — confirmed).
**Pre-filled assumptions** (override in `.env` if your cluster differs):
- Project: `user-haris-crimsoncl-f7ced444` (your private project)
- Domain: `home.pcai2.genai2.hou`
- Object store: PCAI's built-in `local-s3`

---

## ✅ Step 1 — Confirm sign-in & role  *(done)*

You're signed in as `haris-crimsoncloud.in` with **Owner + Admin** on the private project. Skip.

## ✅ Step 2 — Project ready  *(done)*

`user-haris-crimsoncl-f7ced444` is your private project. We use this for the Phase 1 dry-run (HPE tutorials require private projects). Later we replicate in a shared project.

## Step 3 — Verify Tools & Frameworks tiles

**UI clicks:**
1. Left nav → **Tools & Frameworks**.
2. Scan the tiles. You confirmed these are **Ready** (green):
   - ✅ Airflow
   - ✅ EzPresto
   - ✅ HPE MLIS
3. Now check these (we need them too):
   - ❓ **Kubeflow** — required for Phase B. If not green, install: see Step 3a below.
   - ❓ **Spark Operator** — required for Phase A3a. Often auto-installed alongside Airflow.
   - ❓ **MLflow** — required for Phase B tracking. Often auto-installed alongside Kubeflow.
   - ❓ **Superset** *(optional — only for A5 dashboard)*

### Step 3a — Install missing frameworks (UI)

If any of Kubeflow / Spark Operator / MLflow are *not* shown as Ready:

1. Left nav → **Administration** → **Settings** → **Tools & Frameworks** tab.
2. Find the framework in the list.
3. Click the menu icon (three dots) → **Install**.
4. Confirm the prompt. Wait for status to flip to **Ready** (a few minutes per framework).
5. Refresh the Tools & Frameworks page; the tile should now appear in green.

> **HPE doc reference:** "Installing Included Frameworks Post HPE AI Essentials Software Installation."

## Step 4 — Configure NGC API key

Needed for Phase B to pull `nvcr.io/nvidia/cugraph/financial-fraud-training:2.0.0`.

**UI clicks:**
1. Get an NGC API key from https://ngc.nvidia.com/setup/api-key (sign up if you don't have an NGC account).
2. PCAI UI → Left nav → **Tools & Frameworks** → find the **Model Catalog** / **NVIDIA AI Enterprise** tile.
3. (Or alternatively) Left nav → **Administration** → **Settings** → look for "NGC API Key" field.
4. Paste the API key, click Save.
5. **Also save the key to `.env`** as `NGC_API_KEY=` — we need it again when we create the Kubernetes pull secret in Phase B.

> **HPE doc reference:** "Configuring NGC API Key for AI-Essentials-NGC-Catalog."

## Step 5 — Generate an Auth Token (JWT) for yourself

This is the JWT you'll use as `AWS_ACCESS_KEY_ID` for boto3 against PCAI's local-s3 proxy, and as the Bearer token for MLIS endpoint calls.

**UI clicks:**
1. Click your profile avatar (top-right of any PCAI page).
2. Choose **Access Tokens** (or **Profile** → **Access Tokens** depending on UI version).
3. Click **Generate New Token** (or **New Token**).
4. Copy the token immediately — it's shown once. Treat it like a password.
5. Paste it into `.env` as `AUTH_TOKEN=`.

> **Tokens expire** (default ~7 days for refresh tokens). When uploads or MLIS calls suddenly start returning 401, regenerate this token and re-paste into `.env`.

## Step 6 — Fill in the .env file

```powershell
cd f:\hpe\fraud_detection\pcai-showcase\00-bootstrap
Copy-Item .env.template .env
notepad .env
```

Most fields are pre-filled for your cluster. The blanks you must fill:

| Variable | Where to find it |
|---|---|
| `EZPRESTO_JDBC_URL` | UI → **Administration** → **Settings** → **Configurations** tab → **JDBC Endpoint** section. Format: `jdbc:presto://...:8080/<catalog>`. |
| `NGC_API_KEY` | From Step 4. |
| `AUTH_TOKEN` | From Step 5. |

Save the file.

## Step 7 — Sanity check

Two ways to do this — pick whichever you have available.

### Option A (UI-only): Confirm GPUs are visible to your project

1. Left nav → **Notebooks** → **New Notebook Server**.
2. In the GPU section of the form: dropdown should let you pick **NVIDIA**, **Number of GPUs ≥ 1**.
3. If the dropdown is empty/disabled, your project doesn't have GPU quota — go back to project Settings and request quota.
4. **Don't actually launch the server yet** — just confirm the form lets you pick a GPU. Click Cancel.

### Option B (kubectl, optional): Confirm operators installed

If you have a terminal with `kubectl` configured for the cluster (or use a notebook terminal later):

```sh
kubectl get crds | grep -E "(sparkapplications|notebooks.kubeflow|pytorchjobs|inferenceservices)"
```

You want to see all four CRDs listed. If any are missing, the corresponding framework isn't installed — go back to Step 3a.

---

## Done?

When all of these are checked:

- [ ] Tools & Frameworks: Airflow, EzPresto, MLIS, Kubeflow, Spark Operator, MLflow all green
- [ ] NGC API key saved to `.env` and pasted into PCAI Settings
- [ ] Auth Token generated and pasted into `.env`
- [ ] `.env` file complete (no blank required fields)
- [ ] Notebook form shows GPU is pickable

You're ready for Phase A.

**Next:** [`A-dataops/A1-LAND-DATA.md`](../A-dataops/A1-LAND-DATA.md)

---

## Cheat sheet — what each value is for

| `.env` var | Used by |
|---|---|
| `PCAI_DOMAIN` | Import Framework chart `values.yaml`, ingress URLs, MLIS external endpoint URLs |
| `PROJECT_NAME` | Every `kubectl -n <ns>` command, ConfigMap/Secret names, ServiceAccount references |
| `S3_PROXY_URL` | boto3 `endpoint_url`, Spark `fs.s3a.endpoint`, MLflow `MLFLOW_S3_ENDPOINT_URL` |
| `MLFLOW_TRACKING_URI` | `mlflow.set_tracking_uri()` in the training notebook + wrapper |
| `EZPRESTO_JDBC_URL` | External tool connections (Tableau, DBeaver) — not needed if you only use the in-PCAI Query Editor |
| `NGC_API_KEY` | Created as a `dockerconfigjson` Kubernetes Secret in your namespace; referenced as `imagePullSecret` |
| `AUTH_TOKEN` | boto3 access-key, MLIS Bearer token, kubectl auth in some scripts |
