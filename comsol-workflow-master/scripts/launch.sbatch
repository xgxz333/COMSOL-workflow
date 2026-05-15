#!/bin/bash
# Legacy Linux / Slurm helper. This script is retained for cluster usage only.
#SBATCH --job-name=tune                   # Job name
#SBATCH --output=./.slurm_out/job_%j.txt   # Output file (job ID and task number)
#SBATCH --error=./.slurm_out/job_%j.txt    # Error file (job ID and task number)
#SBATCH --nodes=1                         # Number of nodes
#SBATCH --ntasks=1                        # Number of tasks (1 for single task)
#SBATCH --cpus-per-task=15               # Number of CPU cores per task
#SBATCH --mem-per-cpu=4G                        # Memory allocation
#SBATCH --time=6:00:00                    # Time limit

# Print detailed job metadata
JOB_TIME_LIMIT=$(squeue -j $SLURM_JOB_ID -h --Format TimeLimit)
CURRENT_TIMESTAMP_FULL=$(date --utc)
CURRENT_TIMESTAMP_SHORT=$(date --utc -d "$CURRENT_TIMESTAMP_FULL" +"%Y%m%d_%H%M%S")
echo "================== JOB METADATA =================="
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "User ID: $SLURM_JOB_USER"
echo "Job Submit Directory: $SLURM_SUBMIT_DIR"
echo "Node List: $SLURM_JOB_NODELIST"
echo "Partition: $SLURM_JOB_PARTITION"
echo "Number of Nodes: $SLURM_JOB_NUM_NODES"
echo "CPUs per Task: $SLURM_CPUS_PER_TASK"
echo "Memory Allocated: $SLURM_MEM_PER_NODE"
echo "GPUs Allocated: $SLURM_GPUS"
echo "Time Limit: $JOB_TIME_LIMIT"
echo "Job Start Time: $CURRENT_TIMESTAMP_FULL"
echo "==================================================="

# sbatch  --array=1-8 ./scripts/launch.sbatch

# Start Exec
START_LINE="$(date -u +"%s|%Y-%m-%dT%H:%M:%SZ")"
START_EPOCH="${START_LINE%%|*}"
START_ISO="${START_LINE#*|}"
echo "Starting Execution at $START_ISO"

module load comsol/6.3
# /cluster/home/jiayli/miniconda3/envs/comsol_env/bin/python /cluster/home/jiayli/projects/comsol-workflow/scripts/run.py
# /cluster/home/jiayli/miniconda3/envs/comsol_env/bin/python /cluster/home/jiayli/projects/comsol-workflow/scripts/run_detail.py
# /cluster/home/jiayli/miniconda3/envs/comsol_env/bin/python /cluster/home/jiayli/projects/comsol-workflow/scripts/sweep/param_sweep.py
/cluster/home/jiayli/miniconda3/envs/comsol_env/bin/python /cluster/home/jiayli/projects/comsol-workflow/scripts/sweep/run_pairs.py

END_LINE="$(date -u +"%s|%Y-%m-%dT%H:%M:%SZ")"
END_EPOCH="${END_LINE%%|*}"
END_ISO="${END_LINE#*|}"

ELAPSED_SECONDS=$(( END_EPOCH - START_EPOCH ))
ELAPSED_HOURS="$(awk -v s="$ELAPSED_SECONDS" 'BEGIN { printf "%.6f", s/3600 }')"

echo "Finished Execution at $END_ISO"
echo "==================================================="
echo "Execution time: $ELAPSED_HOURS hours ($ELAPSED_SECONDS seconds)"
echo "==================================================="
