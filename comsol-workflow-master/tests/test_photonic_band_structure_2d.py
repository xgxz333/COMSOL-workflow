import os
import sys
import json
import itertools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
from scipy.spatial import Delaunay

sys.path.append(os.path.join(os.path.dirname(__file__), "../comsol_workflow"))
from basis_utils import get_fourier_basis_min_nonzero_values, fourier_to_standard_basis
from geometry_utils import create_hexagon_design, visualize_hexagon_design
from simulation_utils import SimulationRun
from energy_recovery import interpolate_field, integrate_field
from runtime_paths import get_tests_out_path


# ---------------------------------------------------------------------------
# Design configuration  (identical to test_simulation)
# ---------------------------------------------------------------------------

def build_design_config():
    """Return the same design as test_simulation."""
    a = 0.82
    r_0 = 0.26
    b_0 = 0.23
    d = 0.01

    symmetry_config = {
        "r": 5, 
        "theta": None, 
        "b": 1, 
        "phi": None,
    }
    r_f0 = 1.0
    r_fs = 0.0
    theta_fs = 0.0
    b_square_f0 = 1.0
    b_square_fs = 0.0
    phi_fs = 0.0

    r_f = np.zeros(6)
    theta_f = np.zeros(6)
    b_square_f = np.zeros(6)
    phi_f = np.zeros(6)

    r_f[0] = 1.0
    b_square_f[0] = 1.0

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

    min_nz = get_fourier_basis_min_nonzero_values(6)
    r_f = r_0 * r_f
    b_square_f = b_0 * b_0 * b_square_f

    r = fourier_to_standard_basis(r_f / min_nz, 6)
    theta = fourier_to_standard_basis(theta_f / min_nz, 6)
    b_square = fourier_to_standard_basis(b_square_f / min_nz, 6)
    b = np.sqrt(np.maximum(b_square, 0.0))
    phi = fourier_to_standard_basis(phi_f / min_nz, 6)

    hole_params = np.stack([r, theta, b, phi], axis=0)
    return {"a": a, "r_0": r_0, "b_0": b_0, "d": d, "hole_params": hole_params}


# ---------------------------------------------------------------------------
# k-path
# ---------------------------------------------------------------------------

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


def make_k_path():
    """
    2D k-space: r in [0, 0.02, 0.04, 0.06, 0.08, 0.1],
    theta in 24 angles (0-345 deg, 15 deg step).
    Returns list of (r_str, theta_str) polar string tuples.
    r=0 (Gamma) is included only once.
    kx = r * cos(theta_rad), ky = r * sin(theta_rad) computed at each use site.
    """
    center = itertools.product(
        make_str_range("0", "0", "0.02", 4),
        make_str_range("0", "0", "15", 4),
    )

    around = itertools.product(
        make_str_range("0.02", "0.1", "0.02", 4),
        make_str_range("0", "359", "15", 4),
    )

    return sorted(set(list(itertools.chain(center, around))))


# ---------------------------------------------------------------------------
# Single k-point simulation
# ---------------------------------------------------------------------------

def run_k_point(save_path, a, triangles, k):
    eigenmodes_save_path = os.path.join(save_path, "eigenmodes")
    os.makedirs(save_path, exist_ok=True)
    os.makedirs(eigenmodes_save_path, exist_ok=True)

    parsed_path = os.path.join(save_path, "eigenfrequencies_parsed.csv")
    if os.path.exists(parsed_path):
        return pd.read_csv(parsed_path)

    with SimulationRun() as sim_run:
        kx, ky = k
        sim_run.build_and_run(a, triangles, {"kx": kx, "ky": ky})
        eigenfrequencies = sim_run.get_eigenfrequencies()
        df = pd.DataFrame(eigenfrequencies, columns=["re", "im", "q"])

        is_valid = []
        for mode_idx in range(len(df)):
            # Step 1: get normH and normE on xz and yz planes.
            # COMSOL returns coordinates only where each expression is defined,
            # so normH and normE may have different mesh point counts (e.g. normE
            # is undefined inside air-hole sub-domains). Each field therefore
            # carries its own coordinate array.
            coords_normH_xz, normH_xz = sim_run.get_2d_fields(mode_idx, "ewfd.normH", "xz")
            coords_normE_xz, normE_xz = sim_run.get_2d_fields(mode_idx, "ewfd.normE", "xz")
            coords_normH_yz, normH_yz = sim_run.get_2d_fields(mode_idx, "ewfd.normH", "yz")
            coords_normE_yz, normE_yz = sim_run.get_2d_fields(mode_idx, "ewfd.normE", "yz")

            # Step 2: assert domain z-range is sensible, then check confinement
            # coords[:, 1] is z for both xz and yz cut planes
            z_normH_xz = coords_normH_xz[:, 1]
            z_normE_xz = coords_normE_xz[:, 1]
            z_normH_yz = coords_normH_yz[:, 1]
            z_normE_yz = coords_normE_yz[:, 1]
            assert 2.0 < float(np.max(z_normH_xz)) < 3.0, (
                f"mode {mode_idx}: xz normH max-z={np.max(z_normH_xz):.3f} out of expected (2, 3) range"
            )
            assert 2.0 < float(np.max(z_normE_xz)) < 3.0, (
                f"mode {mode_idx}: xz normE max-z={np.max(z_normE_xz):.3f} out of expected (2, 3) range"
            )
            assert 2.0 < float(np.max(z_normH_yz)) < 3.0, (
                f"mode {mode_idx}: yz normH max-z={np.max(z_normH_yz):.3f} out of expected (2, 3) range"
            )
            assert 2.0 < float(np.max(z_normE_yz)) < 3.0, (
                f"mode {mode_idx}: yz normE max-z={np.max(z_normE_yz):.3f} out of expected (2, 3) range"
            )

            # Invalid if the normH/normE peak is above z=1 on either cut plane.
            # Each field uses its own coordinate array so the argmax index is valid.
            z_peakH_xz = float(z_normH_xz[np.argmax(normH_xz)])
            z_peakE_xz = float(z_normE_xz[np.argmax(normE_xz)])
            z_peakH_yz = float(z_normH_yz[np.argmax(normH_yz)])
            z_peakE_yz = float(z_normE_yz[np.argmax(normE_yz)])
            valid = (
                (z_peakH_xz <= 1.0) and 
                (z_peakE_xz <= 1.0) and 
                (z_peakH_yz <= 1.0) and
                (z_peakE_yz <= 1.0)
            )
            is_valid.append(valid)

            if not valid:
                continue

            # Step 3: export field data for valid modes
            # Hz (Re, Im) on center (xy) plane
            coords_re, reHz = sim_run.get_2d_fields(mode_idx, "ewfd.Hz", "center")
            coords_im, imHz = sim_run.get_2d_fields(mode_idx, "ewfd.Hz*(-i)", "center")
            pd.DataFrame({
                "x": coords_re[:, 0], "y": coords_re[:, 1],
                "re": reHz, "im": interpolate_field(coords_im, imHz, coords_re),
            }).to_parquet(
                os.path.join(eigenmodes_save_path, f"{mode_idx:02d}_Hz_center.parquet")
            )

            # Ex (Re, Im) on air (xy) plane
            coords_re, reEx = sim_run.get_2d_fields(mode_idx, "ewfd.Ex", "air")
            coords_im, imEx = sim_run.get_2d_fields(mode_idx, "ewfd.Ex*(-i)", "air")
            pd.DataFrame({
                "x": coords_re[:, 0], "y": coords_re[:, 1],
                "re": reEx, "im": interpolate_field(coords_im, imEx, coords_re),
            }).to_parquet(
                os.path.join(eigenmodes_save_path, f"{mode_idx:02d}_Ex_air.parquet")
            )

            # Ey (Re, Im) on air (xy) plane
            coords_re, reEy = sim_run.get_2d_fields(mode_idx, "ewfd.Ey", "air")
            coords_im, imEy = sim_run.get_2d_fields(mode_idx, "ewfd.Ey*(-i)", "air")
            pd.DataFrame({
                "x": coords_re[:, 0], "y": coords_re[:, 1],
                "re": reEy, "im": interpolate_field(coords_im, imEy, coords_re),
            }).to_parquet(
                os.path.join(eigenmodes_save_path, f"{mode_idx:02d}_Ey_air.parquet"),
            )

        # Step 4: attach validity column
        df["is_valid"] = is_valid

    # Step 5: atomic save, then return
    tmp_path = parsed_path + ".tmp"
    df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, parsed_path)
    return df


# ---------------------------------------------------------------------------
# Run all k-points
# ---------------------------------------------------------------------------

def run_band_structure(save_path, k_points, a, triangles):
    """Run Floquet simulations for all k-points, skipping completed ones.

    k_points : list of (r_str, theta_str) polar tuples as returned by make_k_path().
    """
    for k in k_points:
        r, theta = k
        theta_rad = float(theta) * np.pi / 180.0
        kx = float(r) * np.cos(theta_rad)
        ky = float(r) * np.sin(theta_rad)
        print(f"\n=== Running k-point: r={r}, theta={theta} ===")
        k_save_path = os.path.join(save_path, f"r={r}_theta={theta}")
        run_k_point(k_save_path, a, triangles, (kx, ky))


# ---------------------------------------------------------------------------
# Load results
# ---------------------------------------------------------------------------

def load_band_data(save_path, k_points):
    results = []
    for i, (r, theta) in enumerate(k_points):
        theta_rad = float(theta) * np.pi / 180.0
        kx = float(r) * np.cos(theta_rad)
        ky = float(r) * np.sin(theta_rad)
        k_save_path = os.path.join(save_path, f"r={r}_theta={theta}")
        parsed_path = os.path.join(k_save_path, "eigenfrequencies_parsed.csv")
        if not os.path.exists(parsed_path):
            print(f"Warning: k-point {i} (r={r}, theta={theta}) missing, skipping.")
            continue
        df = pd.read_csv(parsed_path)
        results.append({
            "r": r,
            "theta": theta,
            "kx": kx,
            "ky": ky,
            "modes": df,
        })

    return results


# ---------------------------------------------------------------------------
# Step 1 - Raw scatter plot
# ---------------------------------------------------------------------------

def plot_raw_scatter(band_data, save_path):
    """
    Three 3D scatter plots of eigenfrequencies vs (kx, ky):
      1. raw_scatter_all.png      -> every mode, no validity distinction
      2. raw_scatter_validity.png -> valid in blue, invalid in red x
      3. raw_scatter_valid.png    -> valid modes only

    band_data : list of dicts as returned by load_band_data(), each with keys
                'kx', 'ky', and 'modes' (DataFrame with 're' and 'is_valid').
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    # Unpack band_data
    kx_vals, ky_vals, all_re, all_is_valid = [], [], [], []
    for entry in band_data:
        kx_vals.append(float(entry["kx"]))
        ky_vals.append(float(entry["ky"]))
        all_re.append(entry["modes"]["re"].values)
        all_is_valid.append(entry["modes"]["is_valid"].values.astype(bool))

    def _save3d(fig, path, title):
        ax = fig.axes[0]
        ax.set_title(title)
        ax.set_xlabel("kx [G]")
        ax.set_ylabel("ky [G]")
        ax.set_zlabel("Frequency [THz]")
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        print(f"Saved -> {path}")

    # 1. All modes
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    for kx, ky, freqs in zip(kx_vals, ky_vals, all_re):
        ax.scatter([kx] * len(freqs), [ky] * len(freqs), freqs,
                   color="steelblue", s=8, alpha=0.6)
    _save3d(fig, os.path.join(save_path, "raw_scatter_all.png"), "All Modes")

    # 2. Valid / invalid annotated
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    for kx, ky, freqs, valid in zip(kx_vals, ky_vals, all_re, all_is_valid):
        if valid.any():
            ax.scatter([kx] * valid.sum(), [ky] * valid.sum(), freqs[valid],
                       color="steelblue", s=8, alpha=0.6, label="valid")
        if (~valid).any():
            ax.scatter([kx] * (~valid).sum(), [ky] * (~valid).sum(), freqs[~valid],
                       color="red", marker="x", s=20, alpha=0.8, label="invalid")
    handles, labels = ax.get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        seen.setdefault(l, h)
    ax.legend(seen.values(), seen.keys(), fontsize=9)
    _save3d(fig, os.path.join(save_path, "raw_scatter_validity.png"), "Valid / Invalid Annotated")

    # 3. Valid modes only
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    for kx, ky, freqs, valid in zip(kx_vals, ky_vals, all_re, all_is_valid):
        if valid.any():
            ax.scatter([kx] * valid.sum(), [ky] * valid.sum(), freqs[valid],
                       color="steelblue", s=8, alpha=0.6)
    _save3d(fig, os.path.join(save_path, "raw_scatter_valid.png"), "Valid Modes Only")


# ---------------------------------------------------------------------------
# Field overlap helpers  (used by band connection)
# ---------------------------------------------------------------------------

def _load_hz_center(k_dir, mode_idx):
    path = os.path.join(k_dir, "eigenmodes", f"{mode_idx:02d}_Hz_center.parquet")
    df  = pd.read_parquet(path)
    pts = df[["x", "y"]].values
    hz  = df["re"].values + 1j * df["im"].values
    return pts, hz


def _field_overlap(field1, field2):
    """
    Normalised |<hz_a | hz_b>| with hz_b interpolated onto the mesh of hz_a.

    Uses integrate_field which sums (area * mean_f) over Delaunay triangles;
    passing complex ``f`` works because numpy's mean preserves complex type.

    Returns a scalar in [0, 1], or 0.0 on any numerical degeneracy.
    """
    pts_a, hz_a = field1
    pts_b, hz_b = field2

    norm_a = float(np.real(integrate_field(pts_a, np.conj(hz_a) * hz_a)))
    if norm_a < 1e-60:
        return 0.0

    hz_b_on_a = (
        interpolate_field(pts_b, np.real(hz_b), pts_a)
        + 1j * interpolate_field(pts_b, np.imag(hz_b), pts_a)
    )
    norm_b = float(np.real(integrate_field(pts_a, np.conj(hz_b_on_a) * hz_b_on_a)))
    if norm_b < 1e-60:
        return 0.0

    inner = integrate_field(pts_a, np.conj(hz_a) * hz_b_on_a)
    return float(np.abs(inner) / np.sqrt(norm_a * norm_b))


# ---------------------------------------------------------------------------
# Step 2 - Band connection
# ---------------------------------------------------------------------------

def connect_bands(
    save_path,
    band_data,
    freq_tolerance,
    overlap_threshold,
):
    n_k = len(band_data)

    kx_arr   = np.array([float(e["kx"]) for e in band_data])
    ky_arr   = np.array([float(e["ky"]) for e in band_data])
    freq_tol = freq_tolerance

    process_order = sorted(range(n_k), key=lambda i: (float(band_data[i]["r"]), float(band_data[i]["theta"])))

    bands        = []
    active_at    = {}   # pos -> list of (band_id, mode_orig_idx)
    processed = set() 

    # ── Main loop ─────────────────────────────────────────────────────────
    for pos in process_order:
        print(
            f"Starting processing kx={band_data[pos]['kx']}, ky={band_data[pos]['ky']} at position {pos}. "
            f"{len(bands)} bands so far."
        )

        # extract modes
        df = band_data[pos]["modes"]
        df["band_id"] = -1   # default invalid
        valid_idxs = np.where(df["is_valid"].values)[0]

        if not processed:
            # ── Starting point: seed one band per valid mode in CSV order ──
            for mode_idx in valid_idxs:
                bid = len(bands)
                df.iat[mode_idx, df.columns.get_loc("band_id")] = bid
                bands.append({
                    "band_id":      bid,
                    "k_idx":        [pos],
                    "mode_idx":     [int(mode_idx)],
                    "freq":         [float(df.iat[mode_idx, df.columns.get_loc("re")])],
                    "kx":           [float(band_data[pos]["kx"])],
                    "ky":           [float(band_data[pos]["ky"])],
                    "problematic":  [False],
                    "conflicts":    [],
                })
            processed.add(pos)
            continue

        # Predecessor: closest already-processed k-point in k-space
        pred_pos = min(
            processed,
            key=lambda p: (kx_arr[p] - kx_arr[pos])**2 + (ky_arr[p] - ky_arr[pos])**2,
        )

        print(
            f"-> Predecessor kx={band_data[pred_pos]['kx']}, ky={band_data[pred_pos]['ky']} at position {pred_pos}. "
        )
        df_pred = band_data[pred_pos]["modes"]
        df_pred_valid = df_pred[df_pred["is_valid"]]
        taken = {}          # mode_orig_idx -> band_id that claimed it
        assigned_at_pos = []

        if (valid_idxs.size) and (not df_pred_valid.empty):
            pred_kdir = os.path.join(save_path, f"r={band_data[pred_pos]['r']}_theta={band_data[pred_pos]['theta']}")
            curr_kdir = os.path.join(save_path, f"r={band_data[pos]['r']}_theta={band_data[pos]['theta']}")
            ref_fields = {
                idx: _load_hz_center(pred_kdir, idx)
                for idx in df_pred_valid.index
            }
            cand_fields = {
                idx: _load_hz_center(curr_kdir, idx)
                for idx in valid_idxs
            }

            for bid in sorted(df_pred_valid["band_id"].unique()):
                if bid < 0:
                    continue
                pred_mode_idx = int(df_pred.index[df_pred["band_id"] == bid][0])
                pred_freq = df_pred.iat[pred_mode_idx, df_pred.columns.get_loc("re")]
                # Candidates: valid modes within freq_tol of this band's last freq
                cands = [
                    int(mode_idx)
                    for mode_idx in valid_idxs
                    if abs(df.iat[mode_idx, df.columns.get_loc("re")] - pred_freq) <= freq_tol
                ]
                if not cands:
                    print(f"-> Band {bid} with freq {pred_freq:.2f}THz at predecessor has no candidates.")
                    continue

                rf = ref_fields[pred_mode_idx]
                scores = {mode_idx: _field_overlap(rf, cand_fields[mode_idx]) for mode_idx in cands}
                ranked = sorted(cands, key=lambda mode_idx: scores[mode_idx], reverse=True)

                best_mode_idx = ranked[0]
                best_taken = best_mode_idx in taken.keys()
                print((
                    f"-> Band {bid} with freq {pred_freq:.2f}THz at predecessor has {len(ranked)} candidates, "
                    f"overlap: {[f'{scores[mode_idx]:.3f}' for mode_idx in ranked]}"
                ))
                chosen_mode_idx = None

                for best_mode_idx in ranked:
                    if scores[best_mode_idx] < overlap_threshold:
                        break
                    best_taken = best_mode_idx in taken.keys()
                    if not best_taken:
                        chosen_mode_idx = best_mode_idx
                        break

                if chosen_mode_idx is None:
                    if best_taken:
                        # kx, ky, mode_idx, freq
                        bands[bid]["conflicts"].append((
                            float(band_data[pos]["kx"]),
                            float(band_data[pos]["ky"]),
                            int(ranked[0]),
                            float(df.iat[ranked[0], df.columns.get_loc("re")]),
                        ))
                    continue

                freq = float(df.iat[chosen_mode_idx, df.columns.get_loc("re")])
                bands[bid]["k_idx"].append(pos)
                bands[bid]["mode_idx"].append(int(chosen_mode_idx))
                bands[bid]["freq"].append(freq)
                bands[bid]["kx"].append(float(band_data[pos]["kx"]))
                bands[bid]["ky"].append(float(band_data[pos]["ky"]))
                bands[bid]["problematic"].append(chosen_mode_idx != ranked[0])
                df.iat[chosen_mode_idx, df.columns.get_loc("band_id")] = bid
                taken[chosen_mode_idx] = bid

        # Remaining valid modes with no band -> seed new bands
        for mode_idx in valid_idxs:
            if mode_idx not in taken.keys():
                print((
                    f"-> Valid mode {mode_idx} with freq {df.iat[mode_idx, df.columns.get_loc('re')]:.2f}THz "
                    f"is not claimed by any predecessor band, create new band."
                ))
                bid = len(bands)
                df.iat[mode_idx, df.columns.get_loc("band_id")] = bid
                bands.append({
                    "band_id":      bid,
                    "k_idx":        [pos],
                    "mode_idx":     [int(mode_idx)],
                    "freq":         [float(df.iat[mode_idx, df.columns.get_loc("re")])],
                    "kx":           [float(band_data[pos]["kx"])],
                    "ky":           [float(band_data[pos]["ky"])],
                    "problematic":  [False],
                    "conflicts":    [],
                })

        processed.add(pos)

    n_conflicts = sum(len(b["conflicts"]) for b in bands)
    print(f"{len(bands)} bands in total with {n_conflicts} conflict events).")
    return bands


# ---------------------------------------------------------------------------
# Step 3 - Filter bands by coverage
# ---------------------------------------------------------------------------

def filter_full_range_bands(bands, n_k, min_coverage=0.5):
    """
    Keep bands that span at least ``min_coverage`` fraction of all k-points.

    Parameters
    ----------
    bands        : list of band dicts from connect_bands()
    n_k          : total number of k-points
    min_coverage : minimum fraction of k-points a band must cover (default 0.5)

    Returns
    -------
    filtered : list of band dicts sorted by median frequency
    """
    n_total = n_k

    filtered = []
    for band in bands:
        coverage = len(band["k_idx"]) / n_total
        if coverage >= min_coverage:
            filtered.append(band)

    # Sort by median frequency for cleaner labelling
    filtered.sort(key=lambda b: np.median(b["freq"]))

    print(
        f"Filtered to {len(filtered)} bands with coverage ≥ {min_coverage:.0%} "
        f"(from {len(bands)} total)."
    )
    return filtered


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _band_t(band):
    """Derive scalar k-path coordinate t from per-point kx/ky stored in a band dict."""
    kx = np.array(band["kx"])
    ky = np.array(band["ky"])
    return np.where(kx == 0.0, -ky, kx)


def _decorate(ax):
    """M/Gamma/K top labels and vertical reference lines — consistent across all band plots."""
    ax.axvline(0.0, color="gray",    linestyle="--", linewidth=0.8)
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks([0.0])
    ax2.set_xticklabels([r"M  $\longleftarrow$  $\Gamma$  $\longrightarrow$  K"])
    ax2.tick_params(length=0)
    ax.grid(True, alpha=0.3)


def _mark_problematic(ax, band, color):
    """Overlay 3D markers on a band for problematic and conflict events.

    Problematic (suboptimal assignment): red star.
    Conflict (best candidate taken, band has a gap): orange X.
    """
    prob = band.get("problematic", [])
    prob_mask = np.array(prob, dtype=bool) if prob else np.zeros(len(band["freq"]), dtype=bool)
    kx_arr = np.array(band["kx"])
    ky_arr = np.array(band["ky"])
    f_arr  = np.array(band["freq"])
    if prob_mask.any():
        ax.scatter(kx_arr[prob_mask], ky_arr[prob_mask], f_arr[prob_mask],
                   marker="*", s=120, color="red",
                   edgecolors="darkred", linewidths=0.6, zorder=5)

    conflicts = band.get("conflicts", [])
    if conflicts:
        kx_c = [c[0] for c in conflicts]
        ky_c = [c[1] for c in conflicts]
        f_c  = [c[3] for c in conflicts]
        ax.scatter(kx_c, ky_c, f_c, marker="X", s=80, color="darkorange",
                   edgecolors="saddlebrown", linewidths=0.6, zorder=5)


def _plot_band_surfaces(ax, bands, colors):
    """Render each band as a semi-transparent interpolated surface.

    Returns (has_problematic, has_conflict, legend_handles).
    """
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    from scipy.interpolate import griddata

    has_problematic = False
    has_conflict    = False
    legend_handles  = []

    for i, band in enumerate(bands):
        kx = np.array(band["kx"])
        ky = np.array(band["ky"])
        f  = np.array(band["freq"])
        c  = colors[i % len(colors)]

        if len(kx) >= 3:
            kx_lin = np.linspace(kx.min(), kx.max(), 60)
            ky_lin = np.linspace(ky.min(), ky.max(), 60)
            KX, KY = np.meshgrid(kx_lin, ky_lin)
            F = griddata((kx, ky), f, (KX, KY), method="linear")
            ax.plot_surface(KX, KY, F, color=c, alpha=0.65,
                            linewidth=0, antialiased=True)
        else:
            ax.scatter(kx, ky, f, color=c, s=20)

        legend_handles.append(Patch(facecolor=c, label=f"B{band['band_id']}"))
        _mark_problematic(ax, band, c)
        if any(band.get("problematic", [])):
            has_problematic = True
        if band.get("conflicts"):
            has_conflict = True

    if has_problematic:
        legend_handles.append(
            Line2D([0], [0], marker="*", color="w", markerfacecolor="red",
                   markersize=10, label="problematic match")
        )
    if has_conflict:
        legend_handles.append(
            Line2D([0], [0], marker="X", color="w", markerfacecolor="darkorange",
                   markersize=9, label="conflict (band gap)")
        )
    return has_problematic, has_conflict, legend_handles


def plot_connected_bands(bands, save_path, elev=30, azim=-60, suffix=""):
    """3D surface plot of all connected bands, colour-coded by band_id.
    Each band is interpolated onto a regular kx-ky grid and rendered as a
    semi-transparent surface.  Problematic points: red star; conflicts: orange X.

    elev  : elevation angle in degrees (default 30; use 90 for top-down, -90 for bottom-up)
    azim  : azimuth angle in degrees (default -60)
    suffix: appended before .png in the output filename (e.g. "_top", "_bottom")
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    n_bands = len(bands)
    colors  = plt.cm.tab20(np.linspace(0, 1, max(n_bands, 1)))

    _, _, legend_handles = _plot_band_surfaces(ax, bands, colors)
    ax.legend(handles=legend_handles, fontsize=7, ncol=2)
    ax.view_init(elev=elev, azim=azim)

    ax.set_xlabel("kx [G]")
    ax.set_ylabel("ky [G]")
    ax.set_zlabel("Frequency [THz]")
    ax.set_title(f"Photonic Band Structure - Connected Bands ({n_bands} total, valid modes only)")
    plt.tight_layout()
    out = os.path.join(save_path, f"connected_bands{suffix}.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"Saved connected bands -> {out}")


def plot_filtered_bands(filtered_bands, save_path, elev=30, azim=-60, suffix=""):
    """3D surface plot of filtered bands (≥ min_coverage), colour-coded by band_id.

    elev  : elevation angle in degrees (default 30; use 90 for top-down, -90 for bottom-up)
    azim  : azimuth angle in degrees (default -60)
    suffix: appended before .png in the output filename (e.g. "_top", "_bottom")
    """
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(filtered_bands), 1)))

    _, _, legend_handles = _plot_band_surfaces(ax, filtered_bands, colors)
    ax.legend(handles=legend_handles, fontsize=7, ncol=2)
    ax.view_init(elev=elev, azim=azim)

    ax.set_xlabel("kx [G]")
    ax.set_ylabel("ky [G]")
    ax.set_zlabel("Frequency [THz]")
    ax.set_title(f"Filtered Bands ({len(filtered_bands)} bands with ≥50% k-coverage)")
    plt.tight_layout()
    out = os.path.join(save_path, f"filtered_bands{suffix}.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"Saved filtered bands -> {out}")


# ---------------------------------------------------------------------------
# Save band data as CSV
# ---------------------------------------------------------------------------

def save_band_data(bands, save_path, label=""):
    """Write per-band per-k-point data to CSV."""
    rows = []
    for band in bands:
        b_id = band.get("band_id", -1)
        prob_list = band.get("problematic", [False] * len(band["freq"]))
        t_list = _band_t(band).tolist()
        for t, freq, k_idx, m_i, kx, ky, prob in zip(
            t_list, band["freq"], band["k_idx"], band["mode_idx"],
            band["kx"], band["ky"], prob_list
        ):
            rows.append(
                {
                    "band_id":     b_id,
                    "t":           t,
                    "freq_THz":    freq,
                    "k_idx":       k_idx,
                    "mode_idx":    m_i,
                    "kx":          kx,
                    "ky":          ky,
                    "problematic": bool(prob),
                }
            )
    df = pd.DataFrame(rows)
    name = f"bands_{label}.csv" if label else "bands.csv"
    path = os.path.join(save_path, name)
    df.to_csv(path, index=False)
    print(f"Saved band table -> {path}")
    return df


def load_connected_bands(csv_path):
    """Reconstruct the list of band dicts from a CSV saved by save_band_data.

    Returns the same structure as connect_bands(): a list of dicts with keys
    band_id, k_idx, mode_idx, freq, kx, ky, problematic, conflicts.
    Conflicts are not stored in the CSV, so they are restored as [].
    """
    df = pd.read_csv(csv_path)
    bands = []
    for band_id, grp in df.groupby("band_id", sort=True):
        grp = grp.reset_index(drop=True)
        bands.append({
            "band_id":     int(band_id),
            "k_idx":       grp["k_idx"].tolist(),
            "mode_idx":    grp["mode_idx"].tolist(),
            "freq":        grp["freq_THz"].tolist(),
            "kx":          grp["kx"].tolist(),
            "ky":          grp["ky"].tolist(),
            "problematic": grp["problematic"].tolist(),
            "conflicts":   [],
        })
    print(f"Loaded {len(bands)} bands from {csv_path}")
    return bands


# ---------------------------------------------------------------------------
# Step 4 – Polarization
# ---------------------------------------------------------------------------

def compute_polarization(save_path, band_data):
    """Compute Fourier-projected polarization (cx, cy) for every valid mode.

    For each valid mode at k = (kx, ky):
        cx = integrate(Ex * exp(i*kx*x + i*ky*y)) / sqrt(Area_x)
        cy = integrate(Ey * exp(i*kx*x + i*ky*y)) / sqrt(Area_y)

    where Ex, Ey are the complex fields on the air plane and Area_x/y is the
    total integration-domain area of each mesh.

    Results are cached in polarization.csv; existing file is reused.
    """
    pol_path = os.path.join(save_path, "polarization.csv")
    if os.path.exists(pol_path):
        print(f"Loaded existing polarization -> {pol_path}")
        return pd.read_csv(pol_path)

    rows = []
    for entry in band_data:
        r         = entry["r"]
        theta     = entry["theta"]
        kx        = float(entry["kx"])
        ky        = float(entry["ky"])
        k_dir     = os.path.join(save_path, f"r={r}_theta={theta}")
        df_modes  = entry["modes"]
        valid_idxs = np.where(df_modes["is_valid"].values)[0]

        for mode_idx in valid_idxs:
            ex_path = os.path.join(k_dir, "eigenmodes", f"{int(mode_idx):02d}_Ex_air.parquet")
            ey_path = os.path.join(k_dir, "eigenmodes", f"{int(mode_idx):02d}_Ey_air.parquet")
            if not os.path.exists(ex_path) or not os.path.exists(ey_path):
                continue

            df_ex = pd.read_parquet(ex_path)
            df_ey = pd.read_parquet(ey_path)

            pts_ex  = df_ex[["x", "y"]].values
            ex_comp = df_ex["re"].values + 1j * df_ex["im"].values

            pts_ey  = df_ey[["x", "y"]].values
            ey_comp = df_ey["re"].values + 1j * df_ey["im"].values

            phase_ex = np.exp(1j * (kx * pts_ex[:, 0] + ky * pts_ex[:, 1]))
            phase_ey = np.exp(1j * (kx * pts_ey[:, 0] + ky * pts_ey[:, 1]))

            area_x = float(np.real(integrate_field(pts_ex, np.ones(len(pts_ex)))))
            area_y = float(np.real(integrate_field(pts_ey, np.ones(len(pts_ey)))))

            cx = integrate_field(pts_ex, ex_comp * phase_ex) / np.sqrt(area_x)
            cy = integrate_field(pts_ey, ey_comp * phase_ey) / np.sqrt(area_y)

            rows.append({
                "r": r, "theta": theta, "kx": kx, "ky": ky,
                "mode_idx": int(mode_idx),
                "cx_re": float(np.real(cx)), "cx_im": float(np.imag(cx)),
                "cy_re": float(np.real(cy)), "cy_im": float(np.imag(cy)),
            })

    df = pd.DataFrame(rows)
    tmp = pol_path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, pol_path)
    print(f"Saved polarization -> {pol_path}")
    return df


def load_polarization(csv_path):
    """Load polarization CSV produced by compute_polarization()."""
    df = pd.read_csv(csv_path)
    print(f"Loaded polarization from {csv_path}")
    return df


def plot_band_polarization(bands, pol_df, save_path, normalize=True, suffix=""):
    """Plot polarization ellipses for each band on a 2D (kx, ky) map.

    For each k-point in the band the Jones vector (cx, cy) defines the field:
        E(t) = Re[ cx * exp(i*t) ] x_hat + Re[ cy * exp(i*t) ] y_hat
    which traces an ellipse.

    normalize : if True  (default) all ellipses share the same size (35% of the
                median nearest-neighbour k-spacing), so shape differences are
                easy to compare.
                if False the ellipse size is proportional to sqrt(|cx|^2+|cy|^2),
                normalised so the largest ellipse in the band equals the fixed scale.

    Colour encodes the Stokes-V helicity  V/I  in [-1, 1] using a custom
    red-black-blue colormap:
        red   = left-circular   (V/I = +1)
        black = linear          (V/I =  0)
        blue  = right-circular  (V/I = -1)

    suffix: appended before .png in the output filename.
    """
    from scipy.spatial import KDTree

    # Estimate display scale from the k-grid of available polarization data
    pts_all = pol_df[["kx", "ky"]].drop_duplicates().values
    if len(pts_all) > 1:
        tree = KDTree(pts_all)
        dists, _ = tree.query(pts_all, k=2)
        k_scale = 0.35 * float(np.median(dists[:, 1]))
    else:
        k_scale = 0.005

    t = np.linspace(0, 2 * np.pi, 200)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("RdBlBu", ["blue", "black", "red"])
    norm_h = plt.Normalize(-1, 1)

    for band in bands:
        fig, ax = plt.subplots(figsize=(7, 6))

        # Pre-collect amplitudes for relative scaling when normalize=False
        amp_max = 0.0
        if not normalize:
            for mode_idx, kx, ky in zip(band["mode_idx"], band["kx"], band["ky"]):
                mask = (
                    (np.abs(pol_df["kx"] - float(kx)) < 1e-9) &
                    (np.abs(pol_df["ky"] - float(ky)) < 1e-9) &
                    (pol_df["mode_idx"] == int(mode_idx))
                )
                rows = pol_df[mask]
                if not rows.empty:
                    row = rows.iloc[0]
                    cx = row["cx_re"] + 1j * row["cx_im"]
                    cy = row["cy_re"] + 1j * row["cy_im"]
                    amp_max = max(amp_max, float(np.sqrt(abs(cx)**2 + abs(cy)**2)))
            if amp_max < 1e-30:
                amp_max = 1.0

        for mode_idx, kx, ky in zip(band["mode_idx"], band["kx"], band["ky"]):
            kx_f = float(kx)
            ky_f = float(ky)

            mask = (
                (np.abs(pol_df["kx"] - kx_f) < 1e-9) &
                (np.abs(pol_df["ky"] - ky_f) < 1e-9) &
                (pol_df["mode_idx"] == int(mode_idx))
            )
            rows = pol_df[mask]
            if rows.empty:
                ax.scatter(kx_f, ky_f, c="gray", s=10, zorder=2)
                continue

            row = rows.iloc[0]
            cx = row["cx_re"] + 1j * row["cx_im"]
            cy = row["cy_re"] + 1j * row["cy_im"]

            I = abs(cx) ** 2 + abs(cy) ** 2
            V = 2.0 * float(np.imag(cx * np.conj(cy)))
            helicity = V / I if I > 1e-30 else 0.0

            amp = float(np.sqrt(I))
            if amp < 1e-30:
                ax.scatter(kx_f, ky_f, c="gray", s=10, zorder=2)
                continue

            # Scale: normalised (unit amplitude) or proportional to actual amplitude
            if normalize:
                scale = k_scale
                ex_t = np.real(cx * np.exp(1j * t)) / amp * scale
                ey_t = np.real(cy * np.exp(1j * t)) / amp * scale
            else:
                scale = k_scale * amp / amp_max
                ex_t = np.real(cx * np.exp(1j * t)) / amp * scale
                ey_t = np.real(cy * np.exp(1j * t)) / amp * scale

            color = cmap(norm_h(helicity))
            ax.plot(kx_f + ex_t, ky_f + ey_t,
                    color=color, linewidth=0.8, alpha=0.85)

        ax.set_xlabel("kx [G]")
        ax.set_ylabel("ky [G]")
        ax.set_aspect("equal")
        norm_label = "normalised" if normalize else "proportional"
        ax.set_title(f"Band {band['band_id']} \u2013 Polarization Ellipses ({norm_label})")
        ax.grid(True, alpha=0.6)

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm_h)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label="Helicity  V/I  (red=LCP, black=linear, blue=RCP)")

        plt.tight_layout()
        out = os.path.join(save_path, f"polarization_band_{band['band_id']:02d}{suffix}.png")
        plt.savefig(out, dpi=200)
        plt.close()
        print(f"Saved polarization plot -> {out}")


if __name__ == "__main__":
    save_path = get_tests_out_path("test_photonic_band_structure_2d")
    os.makedirs(save_path, exist_ok=True)

    # ── design ──────────────────────────────────────────────────────────────
    design = build_design_config()
    a = design["a"]
    hexagon, holes, info = create_hexagon_design(a, design["hole_params"].T)
    triangles = [h.tolist() for h in holes]

    visualize_hexagon_design(
        hexagon, holes, info,
        filename=os.path.join(save_path, "design.png"),
        annotate=False,
    )
    visualize_hexagon_design(
        hexagon, holes, info, 
        filename=os.path.join(save_path, "design_annotated.png"), 
        annotate=True
    )

    # ── k-path ───────────────────────────────────────────────────────────────
    k_points = make_k_path()
    print(f"k-path: {len(k_points)} total points")

    # ── run simulations ───────────────────────────────────────────────────────
    run_band_structure(save_path, k_points, a, triangles)

    # ── load data ─────────────────────────────────────────────────────────────
    band_data = load_band_data(save_path, k_points)
    print(f"Loaded {len(band_data)} k-points.")

    # ── Step 1: raw scatter ───────────────────────────────────────────────────
    plot_raw_scatter(band_data, save_path)

    # ── Step 2: connect bands ─────────────────────────────────────────────────
    # connected_bands = connect_bands(
    #     save_path, 
    #     band_data, 
    #     freq_tolerance=5,
    #     overlap_threshold=0.0,
    # )
    # save_band_data(connected_bands, save_path, label="connected")
    connected_bands = load_connected_bands(os.path.join(save_path, "bands_connected.csv"))
    # plot_connected_bands(connected_bands, save_path, elev=30,  azim=-60, suffix="")
    # plot_connected_bands(connected_bands, save_path, elev=-30, azim=-60, suffix="_bottom")

    # ── Step 3: filter bands spanning >= 50% of the k-range ──────────────────
    n_k = len(band_data)
    filtered = filter_full_range_bands(connected_bands, n_k, min_coverage=0.5)
    # save_band_data(filtered, save_path, label="filtered")
    # plot_filtered_bands(filtered, save_path, elev=30,  azim=-60, suffix="")
    # plot_filtered_bands(filtered, save_path, elev=-30, azim=-60, suffix="_bottom")

    # ── Step 4: polarization ──────────────────────────────────────────────────
    pol_df = compute_polarization(save_path, band_data)
    plot_band_polarization(filtered, pol_df, save_path, normalize=True,  suffix="")
    plot_band_polarization(filtered, pol_df, save_path, normalize=False, suffix="_prop")

    print(f"\nAll outputs -> {save_path}")
