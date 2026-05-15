import os
import json
import time
import shutil
import numpy as np
import pandas as pd
from loguru import logger

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../comsol_workflow"))
from basis_utils import get_fourier_basis_min_nonzero_values, fourier_to_standard_basis
from geometry_utils import create_hexagon_design, visualize_hexagon_design
from simulation_utils import SimulationRun
from ask_tell_wrappers import OptimizationStorage, make_optimizer
from energy_recovery import fourier_subspace_energies_field
from run_manager import RunManager
from runtime_paths import get_workspaces_path

# def clip_min_abs(x, eps):
#     # If |x| is smaller than eps, set it to +eps or -eps (keep sign)
#     if abs(x) < eps:
#         return eps if x >= 0 else -eps
#     return x

def evaluate(
    basic_config,
    symmetry_config,
    params,
    workspace_path
):
    os.makedirs(workspace_path, exist_ok=True)
    # basic config
    a = basic_config["a"]
    r_0 = basic_config["r_0"]
    b_0 = basic_config["b_0"]
    d = basic_config["d"]
    # params
    r_f0 = params.get("r_f0", 0.95)
    r_fs = params.get("r_fs", 0.0)
    theta_fs = params.get("theta_fs", 0.0)
    b_square_f0 = params.get("b_square_f0", 1.0)
    b_square_fs = params.get("b_square_fs", 0.0)
    phi_fs = params.get("phi_fs", 0.0)
    # Fourier basis
    r_f = np.zeros(6)
    theta_f = np.zeros(6)
    b_square_f = np.zeros(6)
    phi_f = np.zeros(6)

    r_f[0] = r_f0
    if symmetry_config["r"] is not None:
        # r_fs = clip_min_abs(r_fs, 0.05)
        r_f[int(symmetry_config["r"])] = r_fs

    if symmetry_config["theta"] is not None:
        # theta_fs = clip_min_abs(theta_fs, 3.0)
        theta_f[int(symmetry_config["theta"])] = theta_fs

    b_square_f[0] = b_square_f0
    if symmetry_config["b"] is not None:
        # b_square_fs = clip_min_abs(b_square_fs, 0.05)
        b_square_f[int(symmetry_config["b"])] = b_square_fs

    if symmetry_config["phi"] is not None:
        # phi_fs = clip_min_abs(phi_fs, 3.0)
        phi_f[int(symmetry_config["phi"])] = phi_fs
    
    r_f = r_0 * r_f
    b_square_f = b_0 * b_0 * b_square_f

    r = fourier_to_standard_basis(r_f / get_fourier_basis_min_nonzero_values(6), 6)
    theta = fourier_to_standard_basis(theta_f / get_fourier_basis_min_nonzero_values(6), 6)
    b_square = fourier_to_standard_basis(b_square_f / get_fourier_basis_min_nonzero_values(6), 6)
    b = np.sqrt(np.maximum(b_square, 0.0))
    phi = fourier_to_standard_basis(phi_f / get_fourier_basis_min_nonzero_values(6), 6)

    hole_params = np.stack([r, theta, b, phi], axis=0)

    config = {
        "basic_config": {
            "a": a,
            "r_0": r_0,
            "b_0": b_0,
            "d": d,
        },
        "symmetry_config": symmetry_config,
        "params": {
            "r_f0": r_f0,
            "r_fs": r_fs,
            "theta_fs": theta_fs,
            "b_square_f0": b_square_f0,
            "b_square_fs": b_square_fs,
            "phi_fs": phi_fs,
        },
        "hole_params": hole_params.tolist(),
    }
    # Design
    hexagon, holes, info = create_hexagon_design(a, hole_params.T)
    r_valid = bool(((r > 0.3*r_0).all()) and ((r < 1.7*r_0).all()))
    b_valid = bool(((b > 0.3*b_0).all()) and ((b < 1.7*b_0).all()))
    min_dist = float(min([x['min_dist'] for x in info]))
    d_valid = min_dist >= d
    
    r_violation = float(max(0, 0.3*r_0 - r.min(), r.max() - 1.7*r_0) / r_0)
    b_violation = float(max(0, 0.3*b_0 - b.min(), b.max() - 1.7*b_0) / b_0)
    d_violation = float(max(0, d - min_dist) / b_0)
    violation = r_violation + b_violation + d_violation
    is_valid = violation == 0.0

    visualize_hexagon_design(
        hexagon, holes, info, 
        filename=os.path.join(workspace_path, "geometry.png"), 
        annotate=False
    )
    visualize_hexagon_design(
        hexagon, holes, info, 
        filename=os.path.join(workspace_path, "geometry_annotated.png"), 
        annotate=True
    )
    config.update({
        "hexagon": hexagon.tolist(),
        "triangles": [h.tolist() for h in holes],
        "is_valid": is_valid,
        "violation": violation,
        "info": info
    })
    with open(os.path.join(workspace_path, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    
    if not is_valid:
        score = 0 - violation
        return {
            "result": {
                "objective": score,
            }
        }

    # Simulation
    with open(os.path.join(workspace_path, "config.json"), "r") as f:
        config = json.load(f)
    
    sim_run = SimulationRun()

    sim_run.build_and_run(config["basic_config"]["a"], config["triangles"])
    os.makedirs(workspace_path, exist_ok=True)
    sim_run.model.save(os.path.join(workspace_path, "design.mph"))
    sim_run.model.save(os.path.join(workspace_path, "design.java"))
    sim_run.export_eigenfrequencies(workspace_path)
    eigenfrequencies = pd.read_csv(
        os.path.join(workspace_path, "eigenfrequencies.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )
    num_eigenmodes = len(eigenfrequencies)
    eigenmodes_save_path = os.path.join(workspace_path, "eigenmodes")
    os.makedirs(eigenmodes_save_path, exist_ok=True)
    fourier_energies = np.zeros((num_eigenmodes, 4)) # columns: E_dc, E_pair1, E_pair2, E_nyquist
    for mode_idx in range(num_eigenmodes):
        sim_run.export_2d_fields(mode_idx, "ewfd.normH", "normH", eigenmodes_save_path)
        sim_run.export_2d_fields(mode_idx, "ewfd.Hz", "ReHz", eigenmodes_save_path)
        sim_run.export_2d_fields(mode_idx, "ewfd.Hz*(-i)", "ImHz", eigenmodes_save_path)

        df_re_hz = pd.read_csv(
            os.path.join(eigenmodes_save_path, f"{mode_idx:02d}_ReHz_2d.txt"),
            sep=r"\s+", comment="%", header=None,
        )
        df_im_hz = pd.read_csv(
            os.path.join(eigenmodes_save_path, f"{mode_idx:02d}_ImHz_2d.txt"),
            sep=r"\s+", comment="%", header=None,
        )
        res = fourier_subspace_energies_field(df_re_hz, df_im_hz, N=6)
        total_energy = res['total_energy']
        fourier_energies[mode_idx, :] = np.concatenate(
            [[res['E_dc']], res['E_pairs'], [res['E_nyquist']] if res['E_nyquist'] is not None else []]
        ) / total_energy

    # Parse eigenfrequencies
    s = eigenfrequencies.iloc[:, 0].astype("string").str.strip().str.replace("i", "j", regex=False)
    eig = s.map(lambda z: complex(z))  # e.g. "180.6+0.05j" -> complex

    re = np.real(eig.to_numpy(dtype=np.complex128))
    im = np.imag(eig.to_numpy(dtype=np.complex128))

    # Q = Re / (2 * Im)
    q = re / (np.abs(2 * im) + 1e-15)
    log_q = np.log10(q)
    
    fmin, fmax = 190.0, 220.0
    # Calculate distance from [fmin, fmax]
    freq_dist = np.maximum(0, fmin - re) + np.maximum(0, re - fmax)

    df = pd.DataFrame({
        "re": re,
        "im": im,
        "q": q,
        "log_q": log_q,
        "freq_dist": freq_dist,
    })
    df[["fourier_E_dc", "fourier_E_pair1", "fourier_E_pair2", "fourier_E_nyquist"]] = fourier_energies
    df["dominant_subspace"] = np.argmax(fourier_energies, axis=1)

    # # Check band inversion: we don't want band inversion
    # band_gap = 0
    # valid_modes = df[df["log_q"] > 1]
    # # Find second 1-subspace mode (dominant_subspace == 1)
    # subspace_1_modes = valid_modes[valid_modes["dominant_subspace"] == 1]
    # # Find first 2-subspace mode (dominant_subspace == 2)
    # subspace_2_modes = valid_modes[valid_modes["dominant_subspace"] == 2]
    
    # if len(subspace_1_modes) >= 2 and len(subspace_2_modes) >= 2:
    #     band_gap = subspace_2_modes.iloc[0]["re"] - subspace_1_modes.iloc[1]["re"]

    mode = symmetry_config["mode"]
    def score_func(row, mode=mode):
        # check symmetry
        if (row["fourier_E_pair2"] + row["fourier_E_nyquist"]) > 0.8:
            return 0.0
        if mode is not None:
            if mode == 0: # dc
                if row["fourier_E_dc"] < 0.4:
                    return 0.0
            elif mode == 1: # pair 1
                if row["fourier_E_pair1"] < 0.4:
                    return 0.0
            else:
                raise ValueError(f"Invalid mode {mode}")
        # score = log_q
        if row["freq_dist"] == 0:
            return max(0.0, row["log_q"])
        else:
            # punished log q, cap at 7, penalize by dist/30, floor at 0
            return max(0.0, min(row["log_q"], 7) - row["freq_dist"] / 30.0)

    df["score"] = df.apply(score_func, axis=1)
    df.to_csv(os.path.join(workspace_path, "scores.csv"), index=False)

    # export BIC modes
    bic_mode_indices = np.where(df["score"] > 7)[0]
    for mode_idx in bic_mode_indices:
        sim_run.export_2d_fields(mode_idx, "ewfd.normH", "normH", workspace_path)
        sim_run.export_2d_fields(mode_idx, "ewfd.Hz", "ReHz", workspace_path)
        sim_run.export_2d_fields(mode_idx, "ewfd.Hz*(-i)", "ImHz", workspace_path)

    sim_run.clear()

    return {
        "result": {
            "objective": df["score"].max()
        },
        "attrs": {
            "dominant_subspace": df.loc[df["score"].idxmax()]["dominant_subspace"],
        },
    }


def run_search(search_config):
    # basic config
    basic_config = {
        "a": 0.82,
        "r_0": 0.82/3, # a/3: double dirac cone
        "b_0": 0.23,
        "d": 0.01
    }

    symmetry_config = search_config["symmetry_config"]

    method = "NevergradNGOpt"
    n_iterations = 50
    batch_size = 4
    
    workspace_path = search_config["workspace_path"]
    os.makedirs(workspace_path, exist_ok=True)

    bounds = {}
    if symmetry_config["r0"]:
        bounds["r_f0"] = [0.5, 0.95] # relative value
    if symmetry_config["r"] is not None:
        bounds["r_fs"] = [-0.5, 0.5] # relative change

    if symmetry_config["theta"] is not None:
        bounds["theta_fs"] = [0, 30] # absolute value

    if symmetry_config["b0"]:
        bounds["b_square_f0"] = [0.5, 1.5] # relative value
    if symmetry_config["b"] is not None:
        bounds["b_square_fs"] = [-0.5, 0.5] # relative change

    if symmetry_config["phi"] is not None:
        bounds["phi_fs"] = [-60, 60] # absolute value

    storage = OptimizationStorage(workspace_path, "run_info")

    history = storage.get_valid_runs()
    opt = make_optimizer(method, bounds, batch_size, history)
    for iteration in range(n_iterations):
        base_run_id = len(storage.get_all_runs())
        # Ask
        suggestions = opt.ask()
        
        objectives = []
        # Evaluate
        for idx, suggestion in enumerate(suggestions):
            run_id = base_run_id + idx
            run_workspace = os.path.join(workspace_path, f"runs/run_{run_id:05d}")
            eval_result = evaluate(
                basic_config=basic_config,
                symmetry_config=symmetry_config,
                params=suggestion.params,
                workspace_path=run_workspace,
            )
            objective = eval_result["result"]["objective"]
            storage.write([
                {
                    "meta": {"run_id": run_id, "optimizer": opt.name},
                    "params": suggestion.params,
                } | eval_result
            ])
            best_idx, best_run = storage.get_best_run()
            logger.info(f"Run {run_id}: Objective = {objective:.4f}, Best run: {best_idx} with objective {best_run.get(('result', 'objective'), None):.4f}")
            is_best = best_idx == run_id
            # only keep runs with objective > 7 to save space
            if (not is_best) and (objective <= 7):
                shutil.rmtree(run_workspace, ignore_errors=True)
            objectives.append(objective)
        
        # Tell
        opt.tell(suggestions, objectives)

    best_idx, best_run = storage.get_best_run()
    best_objective = best_run.get(('result', 'objective'), None)
    logger.info(f"Best run: {best_idx} with objective {best_objective:.4f}")
    return best_objective


if __name__ == "__main__":
    symmetry_config_base = {
        'r0': 0, # 0 or 1
        'r': None, # none, 1-5
        'theta': None, # none, 0-5
        'b0': 1, # 0 or 1
        'b': None, # none, 1-5
        'phi': None, # none, 0-5
        'mode': 1, # 0 for dc, 1 for pair 1, None for don't care
    }
    workspace_path_base = get_workspaces_path("search_runs")

    # modulation_options = {
    #     "r": list(range(1, 6)),
    #     "theta": list(range(6)),
    #     "b": list(range(1, 6)),
    #     "phi": list(range(6)),
    # }
    modulation_options = {
        "theta": [5],
        "b": [3, 4],
        "phi": [5],
    }

    num_search_runs = 0
    max_search_runs = 1
    for search_idx in range(2): # repeat n times
        for modulation, options in modulation_options.items():
            for option in options:
                if num_search_runs >= max_search_runs:
                    # no more search runs
                    continue
                manager = RunManager(
                    save_path=workspace_path_base,
                    file_name="search_info",
                    config_cols = ["modulation", "option", "search_idx"],
                    restart_timeout="6h",
                )
                config = {
                    "modulation": modulation,
                    "option": option,
                    "search_idx": search_idx,
                }
                register_result = manager.register_start(config)
                if not register_result["can_run"]:
                    continue
                
                info = {}
                
                logger.info(f"Starting search with modulation={modulation} option={option} search_idx={search_idx}")
                # run this configuration
                symmetry_config = {**symmetry_config_base, modulation: option}
                identifier = "_".join([f"{k}={v}" for k,v in symmetry_config.items()])
                workspace_path = os.path.join(workspace_path_base, identifier, f"search_{search_idx}")
                shutil.rmtree(workspace_path, ignore_errors=True) # clear previous results if exist

                try:
                    best_objective = run_search({
                        "symmetry_config": symmetry_config,
                        "workspace_path": workspace_path,
                    })
                    info["best_objective"] = best_objective
                    manager.report_done(config, info, status="done")
                except Exception as e:
                    logger.error(f"Error in search with modulation={modulation} option={option} search_idx={search_idx}: {e}")
                    shutil.rmtree(workspace_path, ignore_errors=True)
                    manager.report_done(config, info, status="failed")
                    logger.info("Waiting 2 hours before continuing...")
                    time.sleep(2 * 60 * 60)  # 2 hours in seconds
                
                num_search_runs += 1
