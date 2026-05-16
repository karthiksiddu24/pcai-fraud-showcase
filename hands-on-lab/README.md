# Hands-On Lab — Train Your Own Fraud Detection Model on HPE PCAI

A self-contained Jupyter notebook lab for **up to 8 participants** at a time, running on HPE Private Cloud AI 1.9+.

Each participant trains NVIDIA's open-source fraud-detection blueprint end-to-end on their own GPU, logs the result to MLflow under their own name, and watches their registered model appear in the Model Registry. At the end the instructor demos MLIS deployment using one participant's model — closing the loop.

---

## Files in this folder

| File | What it is | Audience |
|---|---|---|
| [`lab.ipynb`](./lab.ipynb) | The lab notebook — 39 cells, fully self-explanatory, runs top-to-bottom | **Each participant** opens this in their own PCAI notebook server |
| [`INSTRUCTOR-SETUP.md`](./INSTRUCTOR-SETUP.md) | One-time pre-lab setup runbook + run-of-show + troubleshooting | **Instructor**, before the lab |
| `README.md` (this file) | Overview, what the lab does, when to use it | **You**, deciding whether to run this lab |

---

## What this lab demonstrates

Sections of the lab map directly to PCAI value-props that pre-sales should know:

| Section | What participants do | PCAI value-prop demonstrated |
|---|---|---|
| 1-2 | Set student ID, verify environment | Per-tenant namespace, GPU allocation, shared PVC |
| 3 | `pip install` cuDF + MLflow | Self-service Python env from any notebook |
| 4-5 | Download + peek at TabFormer raw CSV | Shared PVC as the data plane |
| 6 | **cuDF vs pandas timed comparison** | **NVIDIA RAPIDS — 10-30× speedups out of the box** |
| 7 | Clone NVIDIA's blueprint from public GitHub | "Use partner blueprints unchanged" — NGC catalog integration story |
| 8 | NGC key → `kubectl create secret` | Self-service secret creation in own namespace, no admin |
| 9 | Build `training_config.json` | Config-as-code |
| 10-11 | **Submit K8s Job, watch image pull + training logs stream** | **The production MLOps pattern, observable end-to-end** |
| 12 | Verify trained model artifacts on PVC | Persistent shared storage |
| 13-14 | **Log to MLflow as `student-N-fraud-detection`** | **Governance-grade tracking with auto-injected auth** |
| 15 | Find run in MLflow UI | Registry → audit → promotion workflow |

---

## When to run this lab

This lab is the **hands-on companion** to the Phase 1 showcase. Use it when:

- ✅ You have a roomful of pre-sales engineers / SEs / customers who want to *touch* PCAI, not just watch a demo
- ✅ You have access to a PCAI 1.9+ cluster with at least **16 vGPUs** of headroom (or ≥1 GPU per participant if you're OK with training Jobs queueing)
- ✅ You have an NGC API key (free from ngc.nvidia.com)
- ✅ You have ~45 min for setup + ~30-40 min for the lab itself

**Don't run this lab if:**
- ❌ You're trying to demo *MLIS deployment* — that's the closing moment the instructor does, not what participants do (giving everyone an MLIS deployment uses too much GPU + creates ops complexity)
- ❌ Your audience has zero Python familiarity — they don't have to *write* code but the notebook outputs are Python-flavored
- ❌ Your cluster has fewer than ~1 GPU per participant — Jobs will serialize too aggressively

---

## Timing

| Phase | Wall-clock | Notes |
|---|---|---|
| Instructor setup (one-time) | ~45 min | Mostly downloading TabFormer + hosting it |
| Per-lab spin-up of N notebooks | ~5 min | PCAI Notebooks UI |
| Lab introduction + walkthrough | ~5 min | Instructor explains the structure |
| Participant Section 1-6 (setup, EDA, cuDF speedup) | ~5 min | |
| Participant Section 7-11 (NGC + submit Job + watch image pull + training) | ~10-20 min | **First student per node** spends ~5-10 min on image pull. Subsequent: ~2 min. |
| Participant Section 12-15 (MLflow log + UI inspection) | ~5 min | |
| Instructor closing MLIS demo | ~10 min | Pick one student's model, walk through MLIS deployment |
| **Total** | **~45-60 min** | |

---

## What each participant walks away with

1. **A real trained model** of their own — `student-N-fraud-detection v1` in MLflow's Model Registry
2. **An MLflow run** showing every parameter, metric, and artifact, named after them
3. **Working knowledge of the production MLOps pattern** on PCAI — Job submission, image pull, GPU scheduling, MLflow logging
4. **Concrete answers** to "what does PCAI actually do?" — they touched the pieces themselves

The model in MLflow is theirs to keep. If you give them ongoing PCAI access, they can promote it, retrain it, deploy it via MLIS, anything.

---

## Architecture in one diagram

```
                            ┌──────────────────────────┐
                            │  Your public GitHub repo │
                            │  pcai-fraud-showcase     │
                            │  - lab.ipynb             │
                            │  - transactions.tgz (rel)│
                            └────────────┬─────────────┘
                                         │
                  ┌──────────────────────┼─────────────────────┐
                  │                      │                     │
                  ▼                      ▼                     ▼
       ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
       │ Notebook pod     │  │ Notebook pod     │  │ Notebook pod     │
       │ student-1, 1 GPU │  │ student-2, 1 GPU │  │ ...   8, 1 GPU   │
       │                  │  │                  │  │                  │
       │ /mnt/shared/     │  │ /mnt/shared/     │  │ /mnt/shared/     │
       │ lab-student-1/   │  │ lab-student-2/   │  │ lab-student-N/   │
       └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                │ kubectl apply       │                     │
                │ ngc-secret + Job    │                     │
                ▼                     ▼                     ▼
       ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
       │ K8s Job pod      │  │ K8s Job pod      │  │ K8s Job pod      │
       │ student-1 train  │  │ student-2 train  │  │ ...   N train    │
       │ 1 GPU            │  │ 1 GPU            │  │ 1 GPU            │
       │                  │  │                  │  │                  │
       │ image: nvcr.io/  │  │ image: nvcr.io/  │  │ image: nvcr.io/  │
       │   nvidia/cugraph │  │   nvidia/cugraph │  │   nvidia/cugraph │
       │   /...training   │  │   /...training   │  │   /...training   │
       │                  │  │                  │  │                  │
       │ preprocess+train │  │ preprocess+train │  │ preprocess+train │
       └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                │ trained model       │                     │
                ▼                     ▼                     ▼
                              ┌─────────────────┐
                              │   MLflow        │
                              │   (one experi-  │
                              │    ment per     │
                              │    student)     │
                              │                 │
                              │  student-1-...  │
                              │  student-2-...  │
                              │  ...            │
                              │  student-N-...  │
                              └─────────┬───────┘
                                        │ artifacts
                                        ▼
                              ┌─────────────────┐
                              │   local-s3      │
                              │  mlflow.pcai1   │
                              └─────────────────┘
```

Notice:
- **Each student is its own column.** No shared state between students at runtime.
- **The shared PVC `kubeflow-shared-pvc`** is the only shared resource — each student has their own subdir on it, no collisions.
- **MLflow + local-s3** are shared services, but each student has their own experiment + their own artifact path. Hard-isolated by name.

---

## Next steps

1. Read [`INSTRUCTOR-SETUP.md`](./INSTRUCTOR-SETUP.md) end-to-end before your first run
2. Do the one-time setup (host `transactions.tgz`, generate NGC key, create the 8 student notebooks)
3. Open [`lab.ipynb`](./lab.ipynb) yourself and run it once as a dry-run — gives you confidence on the timing and shows you exactly what the participants will see
4. Schedule the lab session
5. Run it
6. Iterate

If anything in the lab needs adjustment for your specific PCAI cluster (different namespace pattern, different MLflow URL, different image pull policy, etc.), the notebook is plain Python — easy to edit.

---

## Relationship to the rest of this repo

| Folder | Purpose | Audience |
|---|---|---|
| `phase1-deliverable/` | Phase 1 walkthrough — single engineer trains + deploys end-to-end | Solo engineer, ~90 min |
| `phase2-deliverable/` | Phase 2 streaming app — Kafka + Redis + Streamlit + LLM on top of Phase 1 endpoint | Solo engineer, ~1 engineer-day |
| **`hands-on-lab/`** (you are here) | **Group lab** — N participants train in parallel, instructor demos closing MLIS deploy | **Roomful of pre-sales / SEs / customers** |

All three rest on the same underlying showcase: NVIDIA's fraud-detection blueprint, deployed on HPE PCAI. The hands-on lab is the **interactive variant** of Phase 1.
