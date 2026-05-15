import os
import sys
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay

sys.path.append(os.path.join(os.path.dirname(__file__), "../comsol_workflow"))
from simulation_utils import SimulationRun
from geometry_utils import create_hexagon_design, visualize_hexagon_design
from basis_utils import fourier_to_standard_basis, get_fourier_basis_min_nonzero_values
from energy_recovery import interpolate_field, integrate_field
from runtime_paths import get_tests_out_path


def assert_fields_equal(sim_run, mode_idx, expr, expr_name, eigenmodes_save_path, plane):
    """
    Compare export_2d_fields (file-based) vs get_2d_fields (in-memory) for the
    same eigenmode.
    """
    # --- file-based: load pre-exported txt files ---
    def load_txt(name):
        return pd.read_csv(
            os.path.join(eigenmodes_save_path, f"{mode_idx:02d}_{name}_{plane}_2d.txt"),
            sep=r"\s+", comment="%", header=None,
        )

    df = load_txt(expr_name)
    pts_file = df.iloc[:, :2].values
    x_file = df.iloc[:, 2].values

    pts_mem, x_mem = sim_run.get_2d_fields(mode_idx, expr, plane)

    x_mem_file_interp = interpolate_field(pts_mem, x_mem, pts_file)
    x_file_mem_interp = interpolate_field(pts_file, x_file, pts_mem)

    inner_product_file = integrate_field(pts_file, np.conj(x_file) * x_mem_file_interp)
    inner_product_mem = integrate_field(pts_mem, np.conj(x_mem) * x_file_mem_interp)

    norm_file = np.sqrt(integrate_field(pts_file, np.abs(x_file) ** 2))
    norm_mem  = np.sqrt(integrate_field(pts_mem, np.abs(x_mem) ** 2))

    sim_file = np.abs(inner_product_file) / (norm_file * norm_mem)
    sim_mem  = np.abs(inner_product_mem)  / (norm_file * norm_mem)

    # --- plot: triangulation + field magnitude for file and mem side by side ---
    tri_file = Delaunay(pts_file)
    tri_mem  = Delaunay(pts_mem)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"Mode {mode_idx} | {expr_name} | {plane}\n"
        f"sim_file={sim_file:.4f}  sim_mem={sim_mem:.4f}  "
        f"norm_file={norm_file:.3e}  norm_mem={norm_mem:.3e}",
        fontsize=10,
    )

    for col, (pts, tri, x, label) in enumerate([
        (pts_file, tri_file, x_file, "file"),
        (pts_mem,  tri_mem,  x_mem,  "mem"),
    ]):
        # row 0: triangulation
        ax = axes[0, col]
        ax.triplot(pts[:, 0], pts[:, 1], tri.simplices, "b-", linewidth=0.4, alpha=0.3)
        ax.plot(pts[:, 0], pts[:, 1], "r.", markersize=1)
        ax.set_title(f"Triangulation ({label})")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        ax.set_aspect("equal"); ax.grid(True, alpha=0.3)

        # row 1: field magnitude
        ax = axes[1, col]
        field_mag = np.abs(x)
        tcf = ax.tricontourf(
            pts[:, 0], pts[:, 1], tri.simplices, field_mag,
            levels=20, cmap="coolwarm",
        )
        ax.triplot(pts[:, 0], pts[:, 1], tri.simplices, "k-", linewidth=0.2, alpha=0.2)
        ax.set_title(f"Field magnitude ({label})")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        ax.set_aspect("equal")
        plt.colorbar(tcf, ax=ax, label=f"|{expr_name}|")

    plt.tight_layout()
    plot_path = os.path.join(
        eigenmodes_save_path,
        f"{mode_idx:02d}_{expr_name}_{plane}_compare.png",
    )
    plt.savefig(plot_path, dpi=500)
    plt.close()

    assert sim_file >= 0.95, (
        f"Mode {mode_idx} [{expr_name}, {plane}]: similarity on file grid = {sim_file:.6f} < 0.99"
    )
    assert sim_mem >= 0.95, (
        f"Mode {mode_idx} [{expr_name}, {plane}]: similarity on mem grid = {sim_mem:.6f} < 0.99"
    )
    assert np.isclose(norm_file, norm_mem, rtol=5e-2), (
        f"Mode {mode_idx} [{expr_name}, {plane}]: norm mismatch: file={norm_file:.6e}, mem={norm_mem:.6e}"
    )


def test_simulation(save_path, k):
    eigenmodes_save_path = os.path.join(save_path, "eigenmodes")
    # basic config
    a = 0.82
    r_0 = 0.26
    b_0 = 0.23
    d = 0.01
    # symmetry config
    symmetry_config = {
        'r': 5,
        'theta': None,
        'b': 1,
        'phi': None,
    }
    # params 
    r_f0 = 1. # relative value, [0.5, 1.5]
    r_fs  = 0. # relative change, [-0.5, 0.5]
    theta_fs = 0. # absolute value, [-30, 30]
    b_square_f0 = 1. # relative value, [0.5, 1.5]
    b_square_fs = 0. # relative change, [-0.5, 0.5]
    phi_fs = 0. # absolute value, [-60, 60]
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
    min_dist = min([x['min_dist'] for x in info])
    is_valid = min_dist >= d
    violation = abs(d - min_dist) / b_0 if not is_valid else 0.0

    visualize_hexagon_design(
        hexagon, holes, info, 
        filename=os.path.join(save_path, "design.png"), 
        annotate=False
    )
    visualize_hexagon_design(
        hexagon, holes, info, 
        filename=os.path.join(save_path, "design_annotated.png"), 
        annotate=True
    )
    config.update({
        "hexagon": hexagon.tolist(),
        "triangles": [h.tolist() for h in holes],
        "min_dist": min_dist,
        "is_valid": is_valid,
        "violation": violation,
        "info": info
    })
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    
    if not is_valid:
        score = 0 - violation
        assert False, f"Design is invalid with violation {violation:.3e}, score={score:.3e}"
    else:
        # Simulation
        with open(os.path.join(save_path, "config.json"), "r") as f:
            config = json.load(f)
        
        sim_run = SimulationRun()

        sim_run.build_and_run(config["basic_config"]["a"], config["triangles"], k)
        os.makedirs(save_path, exist_ok=True)
        sim_run.model.save(os.path.join(save_path, "design.mph"))
        sim_run.model.save(os.path.join(save_path, "design.java"))
        sim_run.export_eigenfrequencies(save_path)
        eigenfrequencies = sim_run.get_eigenfrequencies()

        re = eigenfrequencies[:, 0]
        im = eigenfrequencies[:, 1]

        # Q = Re / (2 * Im)
        q = re / (np.abs(2 * im) + 1e-15)
        log_q = np.log10(q)
        
        fmin, fmax = 190.0, 220.0
        # Calculate distance from [fmin, fmax]
        freq_dist = np.maximum(0, fmin - re) + np.maximum(0, re - fmax)

        # Calculate adjusted log Q
        # If in range (dist=0), use log_q
        # If out of range, cap at 7, penalize by dist/20, floor at 0
        log_q_adj = np.where(
            freq_dist == 0, 
            log_q, 
            np.minimum(log_q, 7) - freq_dist / 20.0
        )
        log_q_adj = np.maximum(log_q_adj, 0)
        df = pd.DataFrame({
            "re": re,
            "im": im,
            "q": q,
            "log_q": log_q,
            "freq_dist": freq_dist,
            "log_q_adj": log_q_adj
        })
        df.to_csv(os.path.join(save_path, "eigenfrequencies_parsed.csv"), index=False)
        
        for plane in ["center", "yz"]:
            for mode_idx in range(len(eigenfrequencies)):
                sim_run.export_2d_fields(mode_idx, "ewfd.Hz", "ReHz", eigenmodes_save_path, plane=plane)
                assert_fields_equal(sim_run, mode_idx, "ewfd.Hz", "ReHz", eigenmodes_save_path, plane=plane)

                sim_run.export_2d_fields(mode_idx, "ewfd.Hz*(-i)", "ImHz", eigenmodes_save_path, plane=plane)
                assert_fields_equal(sim_run, mode_idx, "ewfd.Hz*(-i)", "ImHz", eigenmodes_save_path, plane=plane)

        
        for plane in ["air", "xz"]:
            for mode_idx in range(len(eigenfrequencies)):
                sim_run.export_2d_fields(mode_idx, "ewfd.normE", "normE", eigenmodes_save_path, plane=plane)
                assert_fields_equal(sim_run, mode_idx, "ewfd.normE", "normE", eigenmodes_save_path, plane=plane)

        sim_run.clear()

if __name__ == "__main__":
    save_path = get_tests_out_path("test_simulation_data_export")
    test_cases = [
        {'kx': 0.0, 'ky': 0.0},
        {'kx': 0.1, 'ky': 0.0},
        {'kx': 0.0, 'ky': 0.1},
    ]
    for i, k in enumerate(test_cases):
        case_path = os.path.join(save_path, f"case_{i:02d}")
        print(f"\n=== Test case {i}: k={k} ===")
        test_simulation(case_path, k)
        print(f"Test case {i} passed.")
    print("\nAll test cases passed.")
