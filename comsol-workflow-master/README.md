# COMSOL Workflow

Windows is now the default development and execution environment for this repository.
The Python solver flow continues to use `MPh + JPype` to start COMSOL from Python.

## Windows Setup

Use a Python 3.10 conda environment.

```powershell
conda create -n comsol_env python=3.10
conda activate comsol_env
pip install -r requirements.txt
```

Before running any COMSOL-dependent script, confirm:

```powershell
where comsol
where comsolbatch
python -c "import mph, jpype; print('OK')"
```

If `SimulationRun()` fails, the usual causes are:

- `MPh` is not installed in the active environment
- `jpype1` is not installed in the active environment
- COMSOL is not on the Windows `PATH`

## Default Output Layout

The repository now writes outputs to repo-relative directories by default:

- `.out/`: reports, test artifacts, matched pair tables
- `workspaces/`: COMSOL run directories and sweep workspaces
- `workspaces/_tmp/`: temporary workspace directories

You can override the default roots with environment variables:

```powershell
$env:COMSOL_WORKFLOW_OUT_DIR = "E:\\my_out"
$env:COMSOL_WORKFLOW_WORKSPACES_DIR = "E:\\my_workspaces"
$env:COMSOL_WORKFLOW_MAX_PROCESSES = "12"
```

Relative override values are resolved from the repository root.

## Common Commands

Run pure-Python checks:

```powershell
python tests\test_fourier_basis.py
python tests\test_geometry.py
python tests\test_run_manager.py
```

Run COMSOL-dependent scripts after COMSOL and Python dependencies are ready:

```powershell
python tests\test_simulation.py
python tests\test_simulation_data_export.py
python scripts\sweep\process_sweep.py
python scripts\mode_decomp.py <simulation_save_path>
```

## COMSOL Java Files

Check COMSOL installation:

```powershell
where comsol
Get-Command comsol
```

Compile a `.java` file to `.class`:

```powershell
comsolcompile MyModel.java
```

Run a compiled model:

```powershell
comsolbatch -inputfile MyModel.class -outputfile MyModel.mph
```

## Legacy Linux / Slurm Scripts

The following files are kept for legacy Linux or Slurm usage only and are not the primary Windows workflow:

- `cluster_state.sh`
- `scripts/launch.sbatch`
- `scripts/touch_scratch.sbatch`
- `scripts/sync_checkpoints.sh`
