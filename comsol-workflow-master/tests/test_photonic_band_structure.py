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
    Line 1: M(0, 0.5) -> Gamma(0, 0)
    Line 2: Gamma(0, 0) -> K(1/sqrt(3), 0)
    """
    line1 = itertools.product(
        make_str_range("0.0", "0.0", "0.01", 3),
        make_str_range("0.0", "0.2", "0.01", 3),
    )
    line2 = itertools.product(
        make_str_range("0.0", "0.2", "0.01", 3),
        make_str_range("0.0", "0.0", "0.01", 3),
    )
    return sorted(set(list(itertools.chain(line1, line2))))


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

    k_points : list of (kx, ky) string tuples as returned by make_k_path().
    t is derived per point: Gamma->M arm (kx==0) uses t=-ky; Gamma->K arm uses t=kx.
    """
    for k in k_points:
        kx, ky = k
        print(f"\n=== Running k-point: kx={kx}, ky={ky} ===")
        k_save_path = os.path.join(save_path, f"kx={kx}_ky={ky}")
        run_k_point(k_save_path, a, triangles, (kx, ky))


# ---------------------------------------------------------------------------
# Load results
# ---------------------------------------------------------------------------

def load_band_data(save_path, k_points):
    results = []
    for i, (kx, ky) in enumerate(k_points):
        k_save_path = os.path.join(save_path, f"kx={kx}_ky={ky}")
        parsed_path = os.path.join(k_save_path, "eigenfrequencies_parsed.csv")
        if not os.path.exists(parsed_path):
            print(f"Warning: k-point {i} (kx={kx}, ky={ky}) missing, skipping.")
            continue
        df = pd.read_csv(parsed_path)
        results.append({
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
    Three scatter plots of eigenfrequencies vs k-path parameter t:
      1. raw_scatter_all.png      -> every mode, no validity distinction
      2. raw_scatter_validity.png -> valid in blue, invalid in red x
      3. raw_scatter_valid.png    -> valid modes only

    band_data : list of dicts as returned by load_band_data(), each with keys
                'kx', 'ky', and 'modes' (DataFrame with 're' and 'is_valid').
    t is derived per point: Gamma->M arm (kx==0) uses t=-ky; Gamma->K arm uses t=kx.
    """
    # Unpack band_data
    t_vals, all_re, all_is_valid = [], [], []
    for entry in band_data:
        kx, ky = entry["kx"], entry["ky"]
        t = -float(ky) if float(kx) == 0.0 else float(kx)
        t_vals.append(t)
        all_re.append(entry["modes"]["re"].values)
        all_is_valid.append(entry["modes"]["is_valid"].values.astype(bool))

    def _save(fig, path, title):
        ax = fig.axes[0]
        ax.set_title(title)
        ax.set_xlabel("k [G]")
        ax.set_ylabel("Frequency [THz]")
        _decorate(ax)
        fig.tight_layout()
        fig.savefig(path, dpi=500)
        plt.close(fig)
        print(f"Saved -> {path}")

    # 1. All modes
    fig, ax = plt.subplots(figsize=(6, 6))
    for t, freqs in zip(t_vals, all_re):
        ax.scatter([t] * len(freqs), freqs, color="steelblue", s=8, alpha=0.6)
    _save(fig, os.path.join(save_path, "raw_scatter_all.png"), "All Modes")

    # 2. Valid / invalid annotated
    fig, ax = plt.subplots(figsize=(6, 6))
    for t, freqs, valid in zip(t_vals, all_re, all_is_valid):
        if valid.any():
            ax.scatter([t] * valid.sum(),  freqs[valid],  color="steelblue",
                       s=8, alpha=0.6, label="valid")
        if (~valid).any():
            ax.scatter([t] * (~valid).sum(), freqs[~valid], color="red",
                       marker="x", s=20, linewidths=0.8, alpha=0.8, label="invalid")
    # Deduplicate legend entries
    handles, labels = ax.get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        seen.setdefault(l, h)
    ax.legend(seen.values(), seen.keys(), fontsize=9)
    _save(fig, os.path.join(save_path, "raw_scatter_validity.png"), "Valid / Invalid Annotated")

    # 3. Valid modes only
    fig, ax = plt.subplots(figsize=(6, 6))
    for t, freqs, valid in zip(t_vals, all_re, all_is_valid):
        if valid.any():
            ax.scatter([t] * valid.sum(), freqs[valid], color="steelblue", s=8, alpha=0.6)
    _save(fig, os.path.join(save_path, "raw_scatter_valid.png"), "Valid Modes Only")


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

    dist_gamma    = np.sqrt(kx_arr**2 + ky_arr**2)
    process_order = sorted(range(n_k), key=lambda i: dist_gamma[i])

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
            pred_kdir = os.path.join(save_path, f"kx={band_data[pred_pos]['kx']}_ky={band_data[pred_pos]['ky']}")
            curr_kdir = os.path.join(save_path, f"kx={band_data[pos]['kx']}_ky={band_data[pos]['ky']}")
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
    """Overlay markers on a band for problematic and conflict events.

    Problematic (suboptimal assignment): red star.
    Conflict (best candidate taken, band has a gap): orange X.
    """
    prob = band.get("problematic", [])
    t_all = _band_t(band)
    t_p   = t_all[np.array(prob, dtype=bool)] if prob else []
    f_p   = np.array(band["freq"])[np.array(prob, dtype=bool)] if prob else []
    if len(t_p):
        ax.scatter(t_p, f_p, marker="*", s=120, color="red",
                   edgecolors="darkred", linewidths=0.6, zorder=5)

    conflicts = band.get("conflicts", [])
    if conflicts:
        t_c = [(-c[1] if c[0] == 0.0 else c[0]) for c in conflicts]
        f_c = [c[3] for c in conflicts]
        ax.scatter(t_c, f_c, marker="X", s=80, color="darkorange",
                   edgecolors="saddlebrown", linewidths=0.6, zorder=5)


def plot_connected_bands(bands, save_path):
    """Line plot of all connected band segments, colour-coded by band_id.
    Problematic match points are marked with a red star; conflict events
    (best candidate taken) are marked with an orange X."""
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(6, 6))
    n_bands = len(bands)
    colors  = plt.cm.tab20(np.linspace(0, 1, max(n_bands, 1)))
    has_problematic = False
    has_conflict    = False

    for i, band in enumerate(bands):
        t_arr = _band_t(band)
        f_arr = np.array(band["freq"])
        order = np.argsort(t_arr)
        c = colors[i % len(colors)]
        ax.plot(t_arr[order], f_arr[order], "o-",
                color=c, markersize=3, linewidth=1.2, alpha=0.8,
                label=f"B{band['band_id']}")
        _mark_problematic(ax, band, c)
        if any(band.get("problematic", [])):
            has_problematic = True
        if band.get("conflicts"):
            has_conflict = True

    extra_handles = []
    if has_problematic:
        extra_handles.append(
            Line2D([0], [0], marker="*", color="w", markerfacecolor="red",
                   markersize=10, label="problematic match")
        )
    if has_conflict:
        extra_handles.append(
            Line2D([0], [0], marker="X", color="w", markerfacecolor="darkorange",
                   markersize=9, label="conflict (band gap)")
        )

    handles, _ = ax.get_legend_handles_labels()
    handles.extend(extra_handles)
    ax.legend(handles=handles, fontsize=7, ncol=2)

    ax.set_ylabel("Frequency [THz]")
    ax.set_title(f"Photonic Band Structure - Connected Bands ({n_bands} total, valid modes only)")
    _decorate(ax)
    plt.tight_layout()
    out = os.path.join(save_path, "connected_bands.png")
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"Saved connected bands -> {out}")


def plot_connected_band_mode_profiles(bands, save_path):
    """Save one Re/Im Hz mode-profile figure per assigned point in each band."""
    out_root = os.path.join(save_path, "connected_band_profiles")
    os.makedirs(out_root, exist_ok=True)

    for band in bands:
        band_id = band["band_id"]
        band_dir = os.path.join(out_root, f"band_{band_id:03d}")
        os.makedirs(band_dir, exist_ok=True)

        rows = []
        prob_list = band.get("problematic", [False] * len(band["freq"]))
        t_list = _band_t(band).tolist()
        for pos, t, freq, mode_idx, kx, ky, problematic in zip(
            band["k_idx"],
            t_list,
            band["freq"],
            band["mode_idx"],
            band["kx"],
            band["ky"],
            prob_list,
        ):
            k_dir = os.path.join(save_path, f"kx={kx:.3f}_ky={ky:.3f}")
            try:
                pts, hz = _load_hz_center(k_dir, mode_idx)
            except FileNotFoundError:
                print(
                    f"  Warning: missing Hz field for band {band_id}, "
                    f"k_idx={pos}, mode={mode_idx}; skipping profile plot."
                )
                continue

            re_hz = hz.real
            im_hz = hz.imag
            tri = Delaunay(pts)
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))

            re_lim = float(np.max(np.abs(re_hz)))
            im_lim = float(np.max(np.abs(im_hz)))
            re_lim = re_lim if re_lim > 0 else 1.0
            im_lim = im_lim if im_lim > 0 else 1.0

            re_plot = axes[0].tricontourf(
                pts[:, 0], pts[:, 1], tri.simplices, re_hz,
                levels=20, cmap="coolwarm", vmin=-re_lim, vmax=re_lim,
            )
            axes[0].triplot(pts[:, 0], pts[:, 1], tri.simplices, "k-",
                            linewidth=0.1, alpha=0.15)
            axes[0].set_title("Re[Hz]")
            axes[0].set_xlabel("x")
            axes[0].set_ylabel("y")
            axes[0].set_aspect("equal")
            plt.colorbar(re_plot, ax=axes[0])

            im_plot = axes[1].tricontourf(
                pts[:, 0], pts[:, 1], tri.simplices, im_hz,
                levels=20, cmap="coolwarm", vmin=-im_lim, vmax=im_lim,
            )
            axes[1].triplot(pts[:, 0], pts[:, 1], tri.simplices, "k-",
                            linewidth=0.1, alpha=0.15)
            axes[1].set_title("Im[Hz]")
            axes[1].set_xlabel("x")
            axes[1].set_ylabel("y")
            axes[1].set_aspect("equal")
            plt.colorbar(im_plot, ax=axes[1])

            fig.suptitle(
                f"Band {band_id} | k=({kx:.3f}, {ky:.3f}) | t={t:.3f} | "
                f"freq={freq:.3f} THz | mode={mode_idx}"
                + (" | problematic" if problematic else "")
            )
            plt.tight_layout()

            out_name = (
                f"k{pos:03d}_t{t:+.3f}_mode{mode_idx:02d}_"
                f"kx{kx:+.3f}_ky{ky:+.3f}.png"
            )
            out_path = os.path.join(band_dir, out_name)
            plt.savefig(out_path, dpi=200)
            plt.close()

            rows.append(
                {
                    "k_idx": int(pos),
                    "t": float(t),
                    "kx": kx,
                    "ky": ky,
                    "freq_THz": float(freq),
                    "mode_idx": int(mode_idx),
                    "problematic": bool(problematic),
                    "image": out_name,
                }
            )

        if rows:
            pd.DataFrame(rows).to_csv(os.path.join(band_dir, "index.csv"), index=False)

    print(f"Saved connected band mode profiles -> {out_root}")


def plot_filtered_bands(filtered_bands, save_path):
    """Line plot of filtered bands (≥ min_coverage) only."""
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(6, 6))
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(filtered_bands), 1)))
    has_prob = False
    has_conf = False

    for i, band in enumerate(filtered_bands):
        t_arr = _band_t(band)
        f_arr = np.array(band["freq"])
        order = np.argsort(t_arr)
        c = colors[i % len(colors)]
        ax.plot(t_arr[order], f_arr[order], "o-", color=c,
                markersize=3, linewidth=1.2, alpha=0.8, label=f"B{band['band_id']}")
        _mark_problematic(ax, band, c)
        if any(band.get("problematic", [])):
            has_prob = True
        if band.get("conflicts"):
            has_conf = True

    extra_handles = []
    if has_prob:
        extra_handles.append(Line2D([0], [0], marker="*", color="w",
                                    markerfacecolor="red", markersize=10,
                                    label="problematic match"))
    if has_conf:
        extra_handles.append(Line2D([0], [0], marker="X", color="w",
                                    markerfacecolor="darkorange", markersize=9,
                                    label="conflict (band gap)"))
    handles, _ = ax.get_legend_handles_labels()
    handles.extend(extra_handles)
    ax.legend(handles=handles, fontsize=7, ncol=2)

    ax.set_ylabel("Frequency [THz]")
    ax.set_title(f"Filtered Bands ({len(filtered_bands)} bands with ≥50% k-coverage)")
    _decorate(ax)
    plt.tight_layout()
    out = os.path.join(save_path, "filtered_bands.png")
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

if __name__ == "__main__":
    save_path = get_tests_out_path("test_photonic_band_structure")
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
    plot_connected_bands(connected_bands, save_path)
    # plot_connected_band_mode_profiles(connected_bands, save_path)

    # ── Step 3: filter bands spanning >= 50% of the k-range ──────────────────
    n_k = len(band_data)
    filtered = filter_full_range_bands(connected_bands, n_k, min_coverage=0.5)
    save_band_data(filtered, save_path, label="filtered")
    plot_filtered_bands(filtered, save_path)

    print(f"\nAll outputs -> {save_path}")
