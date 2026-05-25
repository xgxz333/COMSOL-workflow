# 2D Bilayer Grating PCM Switching Workflow

This project is a sibling workflow to `comsol-workflow-master`. It searches
for a vertically switchable, high-Q resonance in a two-layer one-dimensional
silicon grating. The proposed device has identical lower and upper Si grating
ridges, an upper-only phase-change-material (PCM) cap, and SiO2 layers.

The workflow is motivated by Zhang et al., *Laser & Photonics Reviews* 18,
2301233 (2024). A paper-to-model summary is available in
[`docs/paper_to_model.md`](docs/paper_to_model.md).

## Device model

The first model is a fast 2D `x-z` periodic eigenmode calculation:

```text
              top PML / open boundary
        upper SiO2 encapsulation/cap
              PCM cap on ridge only
             upper Si grating ridge
                background gap
             lower Si grating ridge
             lower radiating cladding
             bottom PML / open boundary
```

The lower and upper silicon ridges are generated from the same `duty_cycle`
and `si_thickness_um`, so they cannot accidentally drift apart during
optimization. The PCM cap is embedded without overlap in an upper SiO2
encapsulation region. Only the upper PCM/cap environment breaks vertical
symmetry.

The default gap between the two gratings uses the configured background
material. A solid spacer can be added later if the fabrication stack requires
one; it is deliberately not assumed in the initial model.

## Optimization objective

Each geometry is simulated twice, using the amorphous and crystalline PCM
indices. Mode pairs are scored using:

- the smaller of the two `log10(Q)` values;
- upward directionality for amorphous PCM;
- downward directionality for crystalline PCM;
- a penalty for missing the target frequency;
- a penalty when the two state frequencies are far apart.

Directionality is calculated as:

```text
D = 10 * log10(P_up / P_down)
```

The default configuration uses GST anchors reported in the paper:

```text
a-GST: n + ik = 4.724 + 0.05i
c-GST: n + ik = 5.96  + 0.30i
target frequency: 183.5 THz
```

The article's complete geometric dimensions are in its Supporting
Information, not in the supplied main PDF. The geometry values in
`configs/default_search.json` are starting points for optimization.

## Layout

```text
bilayer_workflow/
  geometry.py       Parameterized identical bilayer geometry and preview
  metrics.py        Q/direction-switching mode-pair objective
  optimizers.py     Sobol and Nevergrad ask/tell interfaces
  storage.py        Search records and progress plot
  backends.py       Backend selection and pipeline-only mock backend
  comsol_2d.py      MPh-driven COMSOL 2D eigenmode backend
  workflow.py       Candidate evaluation and search loop
configs/
  default_search.json
scripts/
  preview_geometry.py
  run_single.py
  scan_kx.py
  run_search.py
tests/
```

## Quick checks without COMSOL

From this project directory:

```powershell
python tests\test_geometry.py
python tests\test_metrics.py
python tests\test_workflow_mock.py
python scripts\preview_geometry.py
python scripts\run_single.py --backend mock
python scripts\scan_kx.py --backend mock
python scripts\run_search.py --backend mock --method Random --iterations 3 --batch-size 2
```

The `mock` backend validates file flow and optimization logic only; it does
not predict electromagnetic performance.
Geometry previews and progress plots are generated when `matplotlib` from
`requirements.txt` is installed; missing plotting support does not block
simulation records or optimization.

## COMSOL run

Install the same Python dependencies as the existing project and ensure
COMSOL is available on `PATH`:

```powershell
pip install -r requirements.txt
where comsol
python scripts\run_single.py --backend comsol
python scripts\scan_kx.py --backend comsol --start 0.08 --stop 0.16 --points 17
python scripts\run_search.py --backend comsol
```

The COMSOL backend builds a 2D unit cell with Floquet side boundaries and
top/bottom PMLs. It extracts `Q`, upward power, and downward power for every
eigenmode in both PCM states, and saves the solved `.mph` and exported `.java`
model for inspection.

## Required first COMSOL calibration

Before spending time on a full automated search:

1. Run one seed geometry and open the saved `.mph` models.
2. Confirm that geometric selections assigned to silicon, PCM, SiO2, PML,
   periodic sides, and monitor lines are correct after COMSOL forms the union.
3. Confirm the selected branch is the intended TE-like guided resonance.
4. Run a short `kx_norm` scan around `0.095` to `0.142`, the range indicated
   by the paper, and verify that upward/downward flux signs are consistent.
5. Only then expand to an optimizer search and later to a finite grating
   propagation model for radiation efficiency.
