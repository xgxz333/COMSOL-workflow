#!/usr/bin/env bash
# Legacy Linux / Slurm helper. This script is not part of the primary Windows workflow.
set -euo pipefail

echo "=============================="
echo " Slurm Cluster Quick Overview "
echo "=============================="
echo "User: $USER"
echo "Time: $(date)"
echo

# Helper: run a command only if it exists
run_if() {
  local cmd="$1"; shift
  if command -v "$cmd" >/dev/null 2>&1; then
    "$cmd" "$@" || true
  else
    echo "(missing command: $cmd)"
  fi
}

echo "== PARTITIONS =="
run_if sinfo -o "%20P %10a %10l %6D %12F %8c %10m %15G"
echo

echo "== NODES (top 40) =="
run_if sinfo -N -o "%20N %10P %8t %8c %10m %12G %20f" | head -n 40
echo

echo "== QUEUE (top 40) =="
run_if squeue -o "%.10i %.9P %.20j %.8u %.2t %.10M %.10l %.6D %R" | head -n 40
echo

echo "== YOUR JOBS =="
run_if squeue -u "$USER" -o "%.10i %.9P %.20j %.2t %.10M %.10l %R"
echo

echo "== YOUR SLURM LIMITS (if allowed) =="
run_if sacctmgr show assoc user="$USER" format=User,Account,Partition,QOS,GrpTRES,MaxTRES,MaxJobs 2>/dev/null
echo
