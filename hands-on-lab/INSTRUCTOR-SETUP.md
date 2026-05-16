# Instructor Setup Runbook

Everything you need to do **before** the lab so that when the participants walk in, they can run [`lab.ipynb`](./lab.ipynb) top-to-bottom with no friction.

**Estimated total prep time:** ~45 min (mostly hosting `transactions.tgz`)

---

## Overview of what's happening

Each participant gets:
- Their own PCAI Notebook server, 1× L40s, named `student-1` through `student-N`
- Access to a public URL where `transactions.tgz` and `lab.ipynb` are hosted (your own GitHub repo)
- An NGC API key from you (whiteboard / sticky note / one-time chat message)

During the lab, each participant:
- Opens `lab.ipynb`
- Types their student number into Cell 1
- Runs cells in order — downloads data, runs cuDF speedup, submits a K8s Job that pulls NVIDIA's training image and trains the model, logs to MLflow as `student-N-fraud-detection`

Nothing pre-staged on shared storage. Each participant's work lives at `/mnt/shared/lab-student-N/`.

---

## Setup checklist — do all these before the lab

### 1. Host `transactions.tgz` at a stable URL

The IBM Box URL is dynamically signed and expires. Mirror it once to your own infrastructure.

**Easiest option — GitHub Release on your `pcai-fraud-showcase` repo:**

```bash
# On your local workstation, first download transactions.tgz from IBM Box once:
#   https://ibm.ent.box.com/v/tabformer-data → credit_card folder → transactions.tgz
# (~266 MB)

# Then upload as a release asset:
gh release create lab-v1 transactions.tgz \
  --title "Hands-on lab assets v1" \
  --notes "TabFormer dataset hosted for the PCAI fraud-detection hands-on lab" \
  --repo YOUR-ORG/pcai-fraud-showcase
```

The resulting public download URL will look like:

```
https://github.com/YOUR-ORG/pcai-fraud-showcase/releases/download/lab-v1/transactions.tgz
```

**Edit `lab.ipynb` Section 4** to replace `TRANSACTIONS_TGZ_URL` with your URL.

> Alternative hosting options if you don't want to use a GitHub Release:
> - A public S3 bucket (`s3://your-bucket/lab/transactions.tgz` → `https://your-bucket.s3.amazonaws.com/lab/transactions.tgz`)
> - HPE's own internal CDN / artifact server
> - Any HTTPS-reachable URL with a stable path
>
> The only requirements: stable URL (no expiry), public-read or basic-auth that you can encode in the curl command.

### 2. Push `lab.ipynb` to your public repo

Commit the lab notebook to your `pcai-fraud-showcase` repo at a discoverable path, e.g.:

```
pcai-fraud-showcase/hands-on-lab/lab.ipynb
```

The raw download URL for participants will be:

```
https://raw.githubusercontent.com/YOUR-ORG/pcai-fraud-showcase/main/hands-on-lab/lab.ipynb
```

You'll share this URL with each participant for them to `wget` (or you can pre-drop it into their pod — your choice).

### 3. Generate one NGC API key for the lab

You only need *one* key for the whole room — every student uses the same key to create their own `ngc-secret`. (Or each student creates their own key; either works.)

```
https://ngc.nvidia.com → top-right user menu → Setup → Personal Keys → + Generate Personal Key
```

- Key name: `pcai-lab-2026` (or anything)
- Expiration: 30 days minimum
- Services included: **NGC Catalog** AND **Private Registry** (both checkboxes!)
- Copy the `nvapi-...` string immediately — it's shown only once

**Have this ready to share with the room** at the start of the lab (whiteboard, sticky note, group chat). They will paste it into Cell 11 (Section 8) of the lab notebook.

### 4. Verify GPU capacity

Your project quota (`user-haris` or equivalent) needs at least:
- **N × 1 GPU** for the N notebook pods (held continuously)
- **N × 1 GPU** of headroom for the training Jobs (held for ~5-10 min while they're running)

**Conservative calculation:** 8 students → need 16 GPUs project quota → confirmed available on your PCAI 1 setup.

If your cluster has fewer free GPUs than `2 × N`, the lab still works — training Jobs queue up `Pending` until GPUs free, and clear as previous Jobs finish (~40 sec actual training time per Job). **Worst case: lab takes ~15 min instead of ~5 min for the training phase.** Never blocks.

> **Tip:** if your existing MLIS fraud-detection deployment is holding GPU(s) you don't need during the lab, **scale it to zero from the MLIS UI** for the duration. Free GPUs for participants. Restart after.

### 5. Create the 8 student notebook servers

For each `N = 1..8`:

1. PCAI → left-nav → **Notebooks** → **+ New Notebook Server**
2. Name: `student-N` (no zero-padding — match what they'll type as `STUDENT_ID`)
3. **Image:** any current `jupyter-pytorch-cuda-full` (or equivalent — the lab notebook pip-installs anything else it needs)
4. **CPU:** 4 request → 8 limit
5. **Memory:** 16 GiB request → 32 GiB limit
6. **GPU:** **1× Nvidia** (L40s)
7. **Volumes:** confirm `kubeflow-shared-pvc` is added with mount path `/mnt/shared`
8. **Launch**

**Important:** each notebook MUST have `kubeflow-shared-pvc` mounted at `/mnt/shared`. The lab uses this for the working directory (`/mnt/shared/lab-student-N/`) and the training Job mounts the same PVC. If it's missing, the lab will fail at Section 2.

While the 8 notebooks spin up (~2 min total), proceed to step 6.

### 6. Decide how participants get `lab.ipynb` into their notebook

Three options, pick one:

**Option A (recommended) — pre-drop the file**

For each student notebook, click **Connect**, open the terminal, run:
```bash
wget https://raw.githubusercontent.com/YOUR-ORG/pcai-fraud-showcase/main/hands-on-lab/lab.ipynb -O lab.ipynb
```
Now when participants connect, the notebook is already there. Zero setup for them.

**Option B — instruct participants to wget it themselves**

At the start of the lab, give the room a single command to paste into their notebook's terminal:
```bash
wget https://raw.githubusercontent.com/YOUR-ORG/pcai-fraud-showcase/main/hands-on-lab/lab.ipynb
```
Cleaner pedagogically (they've earned it from the start), but adds 30 seconds of friction.

**Option C — upload via JupyterLab's file-upload UI**

If your participants are very non-technical, you can pre-upload the .ipynb file into each pod via JupyterLab's drag-and-drop file browser. Tedious for 8 pods but works.

---

## Run-of-show — what to do during the lab

**T-15 min:**
- Confirm all 8 notebooks show Running in PCAI UI
- Confirm `lab.ipynb` exists in each (if you went with Option A above)
- Pre-warm: in your own admin notebook, do a `kubectl get nodes -l nvidia.com/gpu.present=true` and note the GPU node names — useful for the narration

**T-0 (lab begins):**
1. Introduce the lab: *"You're going to do exactly what the showcase team did — train a fraud-detection model end-to-end on PCAI, in 30 minutes."*
2. Walk the room to PCAI → Notebooks → each opens **their assigned `student-N` notebook**, connects, opens `lab.ipynb`
3. **Share the NGC API key.** Write it on a whiteboard, or pin in a chat. *"Paste this into Section 8 when you get there. Don't worry, it's a throwaway key for this lab."*
4. Tell them: *"Read the markdown above each cell, then run the cell. Don't skip ahead — I'll narrate as you go."*

**During the lab (~30 min):**
- Section 1-6: participants whip through these in ~5 min (the cuDF speedup is the visceral moment — wait for the room to react to the 10-30× speedup numbers)
- Section 7-9: participants paste the NGC key, submit the Job
- **Section 11 (Job watching):** *this is where the magic happens.* The first student per GPU node will wait ~5-10 min for image pull. Use that time to narrate. Show what's happening in real time across the room:
  - *"Look — student-3 just submitted their Job. Their pod is Pending. Kubelet is pulling NVIDIA's 12 GB image. That's a one-time thing per node. Student-5 already had her image cached because she's on the same GPU node — her training is already running. Watch her cell output."*
  - Walk between students' screens. Point at the Pending → ContainerCreating → Pulling image → Running transitions.
  - Once everyone's training is underway, the F1 numbers start to tick: `Epoch 0, validation f1: 0.5722` … `Epoch 2: 0.6880 ← best` … `Training Completed.`
- Section 12-15: MLflow logging (~1 min), MLflow UI inspection (~3-5 min)

**At the end (~5 min):**
- Bring up MLflow UI on the main screen
- Show all 8 student experiments listed
- Pick one student's run (let them be the lucky one — *"let's use student-5's model"*)
- Switch to MLIS UI
- Walk through Packaged Model creation pointing at their `student-5-fraud-detection v1` registered model
- Hit the live endpoint, show the prediction + SHAP output
- *"That. That's what you just produced. Trained, registered, deployable in two UI clicks. That's the PCAI MLOps story."*

---

## Troubleshooting (things that go wrong, in order of likelihood)

### `Failed to pull image: unauthorized: authentication required`

The NGC key in Section 8 is wrong, expired, or doesn't have **Private Registry** scope enabled.

**Fix:** Have the student regenerate `ngc-secret`:
```python
NGC_API_KEY = "nvapi-..."   # paste a fresh key (with Private Registry scope checked)
# re-run the create-secret cell
```

If multiple students fail at once, your one shared key might have been revoked or doesn't have the right scopes. Regenerate at ngc.nvidia.com and re-share.

### `pod has unbound immediate PersistentVolumeClaims`

The student's notebook doesn't have `kubeflow-shared-pvc` mounted, OR it's mounted but in a different access mode. Verify in PCAI Notebooks → Edit → Volumes that `kubeflow-shared-pvc` is listed at mount path `/mnt/shared`.

### `Insufficient nvidia.com/gpu` (Job stays Pending)

All cluster GPUs are taken. The Job sits Pending until a GPU frees. Two options:
1. Wait — when another student's Job finishes (~40 sec), GPU frees and this one runs
2. If you have a stale MLIS deployment holding GPUs, scale it to zero

### Student's pod can't `wget` `transactions.tgz` (DNS / network policy)

The student's namespace might have an egress NetworkPolicy blocking external HTTPS. Options:
1. Pre-download `transactions.tgz` into each student's `/mnt/shared/lab-student-N/raw/` directory before the lab (one-time per student)
2. Mirror to local-s3 and have the lab notebook download from there
3. Have admin temporarily allow egress to your hosting domain

### MLflow `401 Unauthorized` when logging

The token at `/etc/secrets/ezua/.auth_token` rotated. Have the student re-run Section 13 (`Set up MLflow auth`) — it re-reads the token. Should be fresh.

### `Module not found: cudf` in Section 6 (cuDF speedup cell)

The `%pip install cudf-cu12==25.4.0` in Section 3 failed for that student. Symptom: PyPI was slow or NVIDIA's pip index timed out. Have them re-run Section 3.

---

## Cleanup after the lab

```bash
# Delete all student notebook servers (frees GPUs)
for i in 1 2 3 4 5 6 7 8; do
  kubectl delete notebook student-${i} -n project-user-${i}-* 2>/dev/null
done

# Each student's MLflow experiments + registered models REMAIN.
# That's the take-home for them.

# Each student's /mnt/shared/lab-student-N/ directory also remains.
# Optional cleanup if you want to recover the shared PVC space:
#   rm -rf /mnt/shared/lab-student-* (from an admin notebook)
# But each student's data is only ~3 GB so it's not urgent.

# Restart your MLIS fraud-detection deployment (if you scaled it down for the lab)
# In MLIS UI: Deployments → fraud-detection → Edit → replicas: 1 → Save
```

---

## What you take away

After the lab you have:
- **8 trained, registered fraud-detection models** in MLflow, each named after a participant
- A roomful of people who **just touched the PCAI MLOps stack hands-on** and saw it work
- A **demo-ready closing moment**: pick one of their models, walk through MLIS deployment, show the live endpoint

That's the showcase.
