# Server Codex Handoff

## Goal

Continue validation and refinement of a 2D COMSOL workflow for a switchable
bilayer grating. The device hypothesis is:

- the lower and upper silicon gratings are geometrically identical;
- PCM exists only above the upper silicon ridge;
- an upper SiO2 encapsulation surrounds/covers the PCM;
- changing PCM state should switch the preferred radiation direction:
  amorphous upward, crystalline downward.

The project is inspired by Zhang et al., *Laser & Photonics Reviews* 18,
2301233 (2024). Read `docs/paper_to_model.md` before altering physical
assumptions.

## Current Implementation

- `bilayer_workflow/geometry.py`: parameterized 2D unit-cell rectangles.
- `bilayer_workflow/comsol_2d.py`: MPh/JPype COMSOL eigenfrequency backend.
- `bilayer_workflow/metrics.py`: two-state objective using Q, upward/downward
  flux directionality, target frequency, and state frequency matching.
- `bilayer_workflow/workflow.py`: candidate evaluation and optimization loop.
- `scripts/run_single.py`: single candidate execution.
- `scripts/scan_kx.py`: Bloch-wave-vector calibration scan.
- `scripts/run_search.py`: Nevergrad optimization.

The local development machine did not have COMSOL. Pure-Python tests and mock
pipeline tests passed, but the COMSOL API tags and expressions have not yet
been exercised against an installed COMSOL environment.

## First Server Actions

From the cloned repository root:

```bash
cd bilayer-grating-workflow
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
which comsol
python scripts/run_single.py --backend comsol
```

Then open the generated `.mph` files under `workspaces/single_seed/` and
check:

1. Material assignment: both Si ridges are identical, PCM is upper-only, and
   SiO2 caps do not overlap the PCM material region.
2. Domain/boundary selections: top and bottom PMLs, Floquet sides, open
   boundaries, and power monitor lines select the intended entities.
3. Polarization: the selected resonance branch is TE-like and physically
   relevant to the paper mechanism.
4. Sign convention: `P_up/P_down` gives positive directionality for an
   upward-radiating state.

After single-run validation:

```bash
python scripts/scan_kx.py --backend comsol --start 0.08 --stop 0.16 --points 17
python scripts/run_search.py --backend comsol
```

The `kx` scan precedes expensive optimization because the reference paper
finds UGR behavior near `kx*a/(2*pi) = 0.0954-0.1422`.

## Prompt For A New Codex Thread

Start Codex from the repository root, then provide:

```text
Continue the bilayer PCM grating COMSOL workflow in bilayer-grating-workflow.
First read README.md, docs/paper_to_model.md, and docs/SERVER_HANDOFF.md.
The local machine created the 2D model and optimization framework but could
not run COMSOL. On this server, begin by running the non-COMSOL tests and a
single COMSOL seed simulation. Inspect and fix any MPh/COMSOL geometry,
selection, boundary-condition, material-assignment, or power-flux expression
issues. Do not launch the full Nevergrad search until a-GST/c-GST single runs
and the kx scan yield physically sensible upward/downward directionality.
```
