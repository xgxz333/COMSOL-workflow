import os
import json
import time
import shutil
import numpy as np
import pandas as pd
from loguru import logger
from tqdm import tqdm
from multiprocessing import freeze_support, get_context

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../comsol_workflow"))
from basis_utils import get_fourier_basis_min_nonzero_values, fourier_to_standard_basis
from geometry_utils import create_hexagon_design, visualize_hexagon_design
from simulation_utils import SimulationRun
from ask_tell_wrappers import OptimizationStorage, make_optimizer
from energy_recovery import fourier_subspace_energies_field
from run_manager import RunManager
from runtime_paths import get_max_processes, get_workspaces_path, make_workspace_temp_dir

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
    r_f0 = params["r_f0"]
    r_fs = params.get("r_fs", 0.0)
    theta_fs = params.get("theta_fs", 0.0)
    b_square_f0 = params["b_square_f0"]
    b_square_fs = params.get("b_square_fs", 0.0)
    phi_fs = params.get("phi_fs", 0.0)
    # Fourier basis
    r_f = np.zeros(6)
    theta_f = np.zeros(6)
    b_square_f = np.zeros(6)
    phi_f = np.zeros(6)

    r_f[0] = 1
    b_square_f[0] = 1

    if symmetry_config["r"] is not None:
        r_f[int(symmetry_config["r"])] = r_fs
    r_f *= r_f0

    if symmetry_config["theta"] is not None:
        theta_f[int(symmetry_config["theta"])] = theta_fs

    if symmetry_config["b"] is not None:
        b_square_f[int(symmetry_config["b"])] = b_square_fs
    b_square_f *= b_square_f0

    if symmetry_config["phi"] is not None:
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
        return {}

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
        # sim_run.export_2d_fields(mode_idx, "ewfd.normH", "normH", eigenmodes_save_path)
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

    df_p = df.loc[(df["dominant_subspace"] == 1) & (df["re"] <= 280), :]
    if df_p.empty:
        eval_results = {
            "q_p": float("nan"),
            "log_q_p": float("nan"),
            "freq_p": float("nan")
        }
    else:
        p_idx = df_p["q"].idxmax()
        eval_results = {
            "q_p": df_p.loc[p_idx, "q"],
            "log_q_p": df_p.loc[p_idx, "log_q"],
            "freq_p": df_p.loc[p_idx, "re"]
        }

    df.to_csv(os.path.join(workspace_path, "scores.csv"), index=False)

    # export BIC modes
    # bic_mode_indices = np.where(df["score"] > 7)[0]
    # for mode_idx in bic_mode_indices:
    #     # sim_run.export_2d_fields(mode_idx, "ewfd.normH", "normH", workspace_path)
    #     sim_run.export_2d_fields(mode_idx, "ewfd.Hz", "ReHz", workspace_path)
    #     sim_run.export_2d_fields(mode_idx, "ewfd.Hz*(-i)", "ImHz", workspace_path)

    sim_run.clear()

    return eval_results

def make_str_range(start, stop, step, decimals):
    """
    Generate a list of fixed-width decimal strings over an inclusive range.

    The function uses only integer arithmetic internally to avoid floating-point
    rounding issues. Input values are provided as strings, converted to scaled
    integers using the requested decimal resolution, and then formatted back
    into aligned decimal strings.

    Args:
        start: Inclusive start value as a decimal string, for example "-1",
            "0", or "2.5".
        stop: Inclusive stop value as a decimal string.
        step: Step size as a decimal string. Must not be "0". May be positive
            or negative.
        decimals: Number of digits after the decimal point in the output.
            This also defines the internal scaling factor and output alignment.

    Returns:
        A list of strings representing the values from start to stop, inclusive
        when exactly reachable by step, formatted with exactly `decimals`
        fractional digits.

    Raises:
        ValueError: If `step` is zero.

    Examples:
        >>> make_str_range("-1", "1", "0.001", 3)[:5]
        ['-1.000', '-0.999', '-0.998', '-0.997', '-0.996']

        >>> make_str_range("2.5", "3.0", "0.125", 3)
        ['2.500', '2.625', '2.750', '2.875', '3.000']

        >>> make_str_range("1.0", "-1.0", "-0.5", 1)
        ['1.0', '0.5', '0.0', '-0.5', '-1.0']
    """
    scale = 10 ** decimals

    def to_scaled_int(s):
        s = s.strip()
        sign = -1 if s.startswith("-") else 1
        if s[0] in "+-":
            s = s[1:]

        if "." in s:
            whole, frac = s.split(".", 1)
        else:
            whole, frac = s, ""

        frac = (frac + "0" * decimals)[:decimals]
        return sign * (int(whole) * scale + int(frac or "0"))

    def to_fixed_str(n):
        sign = "-" if n < 0 else ""
        n = abs(n)
        return f"{sign}{n // scale}.{n % scale:0{decimals}d}"

    a = to_scaled_int(start)
    b = to_scaled_int(stop)
    d = to_scaled_int(step)

    if d == 0:
        raise ValueError("step must not be 0")

    values = []

    if d > 0:
        for n in range(a, b + 1, d):
            values.append(to_fixed_str(n))
    else:
        for n in range(a, b - 1, d):
            values.append(to_fixed_str(n))

    return values

def sweep_region(r_f0_list, b_square_f0_list, modulation_options):
    # basic config
    basic_config = {
        "a": 0.82,
        "r_0": 0.82/3, # a/3: double dirac cone
        "b_0": 0.23,
        "d": 0.02
    }
    # symmetry config
    symmetry_config_base = {
        'r': None, # none, 1-5
        'theta': None, # none, 0-5
        'b': None, # none, 1-5
        'phi': None, # none, 0-5
    }
    workspace_path_base = get_workspaces_path("param_sweep_runs")

    total_runs = len(r_f0_list) * len(b_square_f0_list) * sum(len(v) for v in modulation_options.values())

    logger.info(
        f"Sweep {total_runs} runs -- r_f0 {r_f0_list[0]} -> {r_f0_list[-1]} ({len(r_f0_list)}), "
        f"b_square_f0 {b_square_f0_list[0]} -> {b_square_f0_list[-1]} ({len(b_square_f0_list)}), "
        + ", ".join(f"{m} {o[0]} -> {o[-1]} ({len(o)})" for m, o in modulation_options.items())
    )

    manager = RunManager(
        save_path=workspace_path_base,
        file_name="sweep_info",
        config_cols = ["r_f0", "b_square_f0", "modulation", "option"],
        restart_timeout="10min",
    )

    for _ in range(2): # retries
        for r_f0 in r_f0_list:
            for b_square_f0 in b_square_f0_list:
                for modulation, options in modulation_options.items():
                    for option in options:
                        config = {
                            "r_f0": r_f0,
                            "b_square_f0": b_square_f0,
                            "modulation": modulation,
                            "option": option,
                        }
                        register_result = manager.register_start(config)
                        if not register_result["can_run"]:
                            continue
                        
                        info = {}
                        
                        logger.info(f"Starting run with {' '.join([f'{k}={v}' for k,v in config.items()])}")
                        # run this configuration
                        modulation_param, modulation_symmetry = modulation.split("-")
                        params = {
                            "r_f0": float(r_f0), 
                            "b_square_f0": float(b_square_f0),
                            f"{modulation_param}_fs": float(option),
                        }
                        symmetry_config = {
                            **symmetry_config_base, 
                            modulation_param if modulation_param != "b_square" else "b": int(modulation_symmetry)
                        }
                        workspace_path = make_workspace_temp_dir(prefix="param_sweep_")
                        # shutil.rmtree(workspace_path, ignore_errors=True)

                        try:
                            result = evaluate(
                                basic_config=basic_config,
                                symmetry_config=symmetry_config,
                                params=params,
                                workspace_path=workspace_path,
                            )
                            
                            info |= result
                            manager.report_done(config, info, status="done")
                            shutil.rmtree(workspace_path, ignore_errors=True)
                        except Exception as e:
                            logger.error(f"Error in search with {' '.join([f'{k}={v}' for k,v in config.items()])}: {e}")
                            manager.report_done(config, info, status="failed")
                            shutil.rmtree(workspace_path, ignore_errors=True)
                            return

def main():
    regions = [
        # big coarse region
        {
            "r_f0_list": make_str_range("0.95", "0.97", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "r-3": make_str_range("-0.15", "0.15", "0.005", 4),
                "theta-4": make_str_range("-15", "15", "0.5", 3),
            },
        },
        # r = 0.95
        {
            "r_f0_list": make_str_range("0.95", "0.95", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "r-3": make_str_range("-0.115", "-0.105", "0.001", 4) + make_str_range("0.125", "0.135", "0.001", 4),
                "theta-4": make_str_range("-10", "-8.5", "0.1", 3),
            },
        },
        # r = 0.96
        {
            "r_f0_list": make_str_range("0.96", "0.96", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "r-3": make_str_range("-0.1", "-0.085", "0.001", 4) + make_str_range("0.09", "0.11", "0.001", 4),
                "theta-4": make_str_range("-8.5", "-7", "0.1", 3) + make_str_range("11.5", "13", "0.1", 3),
            },
        },
        # r = 0.97
        {
            "r_f0_list": make_str_range("0.97", "0.97", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "r-3": make_str_range("-0.08", "-0.065", "0.001", 4) + make_str_range("0.065", "0.075", "0.001", 4),
                "theta-4": make_str_range("-6.5", "-5.5", "0.1", 3) + make_str_range("8", "9", "0.1", 3),
            },
        },
        # big coarse region
        {
            "r_f0_list": make_str_range("1.03", "1.05", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "r-3": make_str_range("-0.15", "0.15", "0.005", 4),
                "theta-4": make_str_range("-15", "15", "0.5", 3),
            },
        },
        # r = 1.03
        {
            "r_f0_list": make_str_range("1.03", "1.03", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "r-3": make_str_range("-0.08", "-0.065", "0.001", 4) + make_str_range("0.06", "0.07", "0.001", 4),
                "theta-4": make_str_range("-6.5", "-5.5", "0.1", 3) + make_str_range("7", "9", "0.1", 3),
            },
        },
        # r = 1.04
        {
            "r_f0_list": make_str_range("1.04", "1.04", "0.01", 3),
            "b_square_f0_list": make_str_range("0.7", "1.3", "0.01", 4),
            "modulation_options": {
                "theta-4": make_str_range("-8.5", "-7", "0.1", 3) + make_str_range("11.5", "12.5", "0.1", 3),
            },
        },
    ]
    for region in regions:
        sweep_region(**region)

if __name__ == "__main__":
    freeze_support()
    num_processes = get_max_processes(12)
    if num_processes <= 1:
        main()
    else:
        context = get_context("spawn")
        with context.Pool(processes=num_processes) as pool:
            results = [pool.apply_async(main) for _ in range(num_processes)]
            for idx in range(len(results)):
                results[idx] = results[idx].get()
