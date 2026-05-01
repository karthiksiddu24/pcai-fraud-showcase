# Troubleshooting

Catch-all for known cluster-state issues we've encountered and need to resolve before specific phases.

---

## ❌ MLflow + Kubeflow Pipelines down (blocks Phase B, not Phase A)

**Symptoms (observed 2026-04-28 on `pcai2.genai2.hou`):**
- `mlflow-7d985d9ccb-q4sdc` — **Pending** (in `mlflow` namespace)
- `mlflow-postgresql-0` — **Pending** (in `mlflow` namespace)
- MLflow UI returns "no healthy upstream"
- `mysql-84b4687bfc-j65jb` (Kubeflow's MySQL) — **Pending** (in `kubeflow` namespace)
- `ml-pipeline-api-server` container — `not_ready`
- Kubeflow Dashboard "Recent Pipelines" / "Recent Pipeline Runs" panels show errors
- `metadata-grpc-deployment-5996f44df4-pk6mz` — CrashLoopBackOff (metadata/lineage)

**Hypothesis:** unbound PVCs (storage class missing, or PV pool exhausted). All three Pending pods are StatefulSets with persistent storage.

**Diagnostic (kubectl required — PCAI doesn't expose pod-level events in UI):**

```sh
# Check PVCs
kubectl -n kubeflow get pvc
kubectl -n mlflow get pvc

# Check default StorageClass (should have "(default)" annotation)
kubectl get storageclass

# Look at pod events for the unbound resource
kubectl -n kubeflow describe pod -l app=mysql 2>&1 | tail -40
kubectl -n mlflow describe pod mlflow-postgresql-0 2>&1 | tail -40
```

**Likely fixes (apply whichever matches diagnostic output):**

### Fix 1 — No default StorageClass

```sh
kubectl get storageclass
# If no class is annotated as (default), pick the right one and:
kubectl patch storageclass <CLASS_NAME> -p \
  '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
# Then bounce the Pending pods to retrigger PVC binding:
kubectl -n mlflow delete pod mlflow-postgresql-0
kubectl -n kubeflow delete pod -l app=mysql
```

### Fix 2 — PVC bound to wrong/missing class

```sh
# Look at what each PVC requested:
kubectl -n mlflow get pvc -o yaml | grep -E "(name:|storageClassName:|status:)"
# If storageClassName is wrong, edit the PVC (or recreate via Helm reinstall of the framework):
# UI path: Tools & Frameworks → MLflow tile → Configure → edit values.yaml's storage class
```

### Fix 3 — PV pool exhausted

```sh
kubectl get pv | wc -l
kubectl describe pv | grep -E "Capacity|Phase"
# If lots of "Released" PVs aren't being recycled, reclaim them or grow the pool.
```

**Verification once fixed:**
```sh
kubectl -n mlflow get pods   # both should be Running
kubectl -n kubeflow get pods -l app=mysql   # Running
```

Then UI: Tools & Frameworks → MLflow → Open should serve the MLflow dashboard without "no healthy upstream."

> When you hit this, paste the output of the diagnostic block back to your assistant and we'll write a targeted patch.

---

## (Add new issues below as we encounter them)
