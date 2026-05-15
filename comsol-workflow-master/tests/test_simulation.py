import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../comsol_workflow"))
from basis_utils import get_fourier_basis_matrix, get_fourier_basis_min_nonzero_values, fourier_to_standard_basis, standard_to_fourier_basis
from geometry_utils import create_hexagon_design, visualize_hexagon_design
from simulation_utils import SimulationRun
from energy_recovery import get_complex_field, compute_autocorrelation_field, fourier_subspace_energies_field
from energy_recovery import get_standard_basis_field, field_to_vector, interpolate_field, integrate_field
from runtime_paths import get_tests_out_path

def test_triangulation(pts, field_complex, save_dir):
    """
    Test Delaunay triangulation and visualize points and field.
    
    Args:
        pts: (N, 2) array of points
        field_complex: (N,) array of complex field values
        save_dir: Directory to save plots
    """
    print("\n=== Testing Delaunay triangulation ===")
    tri = Delaunay(pts)
    print(f"Number of triangles: {len(tri.simplices)}")
    
    # Plot the Delaunay triangulation
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left: Points and triangulation
    ax1.triplot(pts[:, 0], pts[:, 1], tri.simplices, 'b-', linewidth=0.5, alpha=0.3)
    ax1.plot(pts[:, 0], pts[:, 1], 'r.', markersize=1)
    ax1.set_xlabel('x')
    ax1.set_ylabel('y')
    ax1.set_title('Delaunay Triangulation')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    
    # Right: Field magnitude on triangulation
    field_mag = np.abs(field_complex)
    tcf = ax2.tricontourf(pts[:, 0], pts[:, 1], tri.simplices, field_mag, levels=20, cmap='coolwarm')
    ax2.triplot(pts[:, 0], pts[:, 1], tri.simplices, 'k-', linewidth=0.2, alpha=0.2)
    ax2.set_xlabel('x')
    ax2.set_ylabel('y')
    ax2.set_title('Field Magnitude |Hz|')
    ax2.set_aspect('equal')
    plt.colorbar(tcf, ax=ax2, label='|Hz|')
    
    plt.tight_layout()
    plot_path = os.path.join(save_dir, f"triangulation.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"Saved triangulation plot to {plot_path}")
    
    return tri

def compute_and_visualize_fourier_energies(df_re, df_im, N, save_dir):
    """
    Compute autocorrelation and Fourier subspace energies, then visualize.
    
    Args:
        df_re: DataFrame with real part of field
        df_im: DataFrame with imaginary part of field
        N: Rotational symmetry order
        save_dir: Directory to save results
        
    Returns:
        dict: Dictionary with autocorrelation and energy results
    """
    print(f"\n=== Computing autocorrelation for N={N} ===")
    
    # Compute Fourier subspace energies (includes autocorrelation)
    r = compute_autocorrelation_field(df_re, df_im, N)
    results = fourier_subspace_energies_field(df_re, df_im, N)
    
    R = results['R']
    E_dc = results['E_dc']
    E_pairs = results['E_pairs']
    E_nyquist = results['E_nyquist']
    total_energy = results['total_energy']
    
    print(f"Autocorrelation sequence (r_m for m=0,...,{N-1}):")
    for m, r_m in enumerate(r):
        print(f"  r_{m} = {r_m.real:.6e} + {r_m.imag:.6e}j")
    
    print(f"\nDFT of autocorrelation (R_k = |X_k|^2):")
    for k, R_k in enumerate(R):
        print(f"  R_{k} = {R_k:.6e}")
    
    print(f"\n=== Fourier subspace energies ===")
    print(f"E_0 (DC):        {E_dc:.6e}")
    for k in range(len(E_pairs)):
        print(f"E_{k+1} (k={k+1} pair):  {E_pairs[k]:.6e}")
    if E_nyquist is not None:
        print(f"E_{N//2} (Nyquist):   {E_nyquist:.6e}")
    print(f"Total energy:    {total_energy:.6e}")
    print(f"Expected (r_0):  {r[0].real:.6e}")
    print(f"Relative error:  {abs(total_energy - r[0].real) / abs(r[0].real):.6e}")
    
    # Visualize energy distribution
    visualize_energy_distribution(E_dc, E_pairs, E_nyquist, total_energy, N, save_dir)
    
    # Save results to CSV
    save_energy_results(E_dc, E_pairs, E_nyquist, r, N, save_dir)
    
    return results

def visualize_energy_distribution(E_dc, E_pairs, E_nyquist, total_energy, N, save_dir):
    """Visualize Fourier subspace energy distribution as bar chart."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    labels = ['DC (k=0)']
    energies = [E_dc/total_energy]
    
    for k in range(len(E_pairs)):
        labels.append(f'Pair k={k+1}')
        energies.append(E_pairs[k]/total_energy)
    
    if E_nyquist is not None:
        labels.append(f'Nyquist (k={N//2})')
        energies.append(E_nyquist/total_energy)
    
    colors = plt.cm.tab10(range(len(labels)))
    bars = ax.bar(labels, energies, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Normalized Energy (E_k / Total Energy)')
    ax.set_title(f'Fourier Subspace Energies (N={N})')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, energy in zip(bars, energies):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{energy:.3f}',
               ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plot_path = os.path.join(save_dir, f"fourier_energies.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"\nSaved energy distribution plot to {plot_path}")

def save_energy_results(E_dc, E_pairs, E_nyquist, r, N, save_dir):
    """Save energy and autocorrelation results to CSV files."""
    # Energy results
    labels = ['DC (k=0)']
    energies = [E_dc]
    
    for k in range(len(E_pairs)):
        labels.append(f'Pair k={k+1}')
        energies.append(E_pairs[k])
    
    if E_nyquist is not None:
        labels.append(f'Nyquist (k={N//2})')
        energies.append(E_nyquist)
    
    energy_results = pd.DataFrame({
        'subspace': labels,
        'energy': energies
    })
    energy_path = os.path.join(save_dir, f"fourier_energies.csv")
    energy_results.to_csv(energy_path, index=False)
    
    # Autocorrelation results
    autocorr_results = pd.DataFrame({
        'm': range(N),
        'r_real': np.real(r),
        'r_imag': np.imag(r)
    })
    autocorr_path = os.path.join(save_dir, f"autocorrelation.csv")
    autocorr_results.to_csv(autocorr_path, index=False)
    
    print(f"\nSaved results:")
    print(f"  - Fourier energies: {energy_path}")
    print(f"  - Autocorrelation: {autocorr_path}")

def test_field_inner_product(simulation_save_path, mode_idx, plane="center", N=6):
    """
    Test field inner product for a specific mode.
    
    Args:
        simulation_save_path: Directory containing exported field data
        mode_idx: Index of mode to test
        plane: Plane to test (default: "center")
        N: Rotational symmetry order (default: 6)
    """
    print(f"\n{'='*60}")
    print(f"Testing field inner product for mode {mode_idx}")
    print(f"{'='*60}")

    # Create output directory for this mode
    mode_save_path = os.path.join(simulation_save_path, f"mode_{mode_idx:02d}_inner_product")
    os.makedirs(mode_save_path, exist_ok=True)
    
    # 1. Load the field data
    df_re_hz = pd.read_csv(
        os.path.join(simulation_save_path, f"{mode_idx:02d}_ReHz_{plane}_2d.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )
    df_im_hz = pd.read_csv(
        os.path.join(simulation_save_path, f"{mode_idx:02d}_ImHz_{plane}_2d.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )
    
    # Get complex field
    pts, hz_complex = get_complex_field(df_re_hz, df_im_hz)
    print(f"\nLoaded field with {len(pts)} points")
    print(f"Field range: real [{np.min(np.real(hz_complex)):.3e}, {np.max(np.real(hz_complex)):.3e}]")
    print(f"            imag [{np.min(np.imag(hz_complex)):.3e}, {np.max(np.imag(hz_complex)):.3e}]")
    
    # 2. Test triangulation and visualize
    tri = test_triangulation(pts, hz_complex, mode_save_path)
    
    # 3. Compute autocorrelation and Fourier energies
    results = compute_and_visualize_fourier_energies(
        df_re_hz, df_im_hz, N, mode_save_path
    )
    
    print(f"\n{'='*60}")
    print(f"Completed testing for mode {mode_idx}")
    print(f"{'='*60}\n")
    
    return results

def test_field_to_vector(simulation_save_path, mode_idx, plane="center", N=6):
    """
    Test field_to_vector function for a specific mode.
    
    This function:
    1. Tests get_standard_basis_field by visualizing all N basis vectors
    2. Computes the standard basis coefficients
    3. Converts to Fourier basis coefficients
    4. Saves both coefficient sets as CSV files
    
    Args:
        simulation_save_path: Directory containing exported field data
        mode_idx: Index of mode to test
        plane: Plane to test (default: "center")
        N: Rotational symmetry order (default: 6)
    """
    
    print(f"\n{'='*60}")
    print(f"Testing field_to_vector for mode {mode_idx}")
    print(f"{'='*60}")
    
    # Create output directory for this mode
    mode_save_path = os.path.join(simulation_save_path, f"mode_{mode_idx:02d}_vector")
    os.makedirs(mode_save_path, exist_ok=True)
    
    # 1. Load the field data
    df_re_hz = pd.read_csv(
        os.path.join(simulation_save_path, f"{mode_idx:02d}_ReHz_{plane}_2d.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )
    df_im_hz = pd.read_csv(
        os.path.join(simulation_save_path, f"{mode_idx:02d}_ImHz_{plane}_2d.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )
    
    # Get complex field
    pts, hz_complex = get_complex_field(df_re_hz, df_im_hz)
    print(f"\nLoaded field with {len(pts)} points")
    
    # 2. Get standard basis vectors
    print(f"\nComputing standard basis vectors...")
    standard_basis = get_standard_basis_field(pts, N)
    
    # 3. Visualize all standard basis vectors
    print(f"Visualizing {N} standard basis vectors...")
    tri = Delaunay(pts)
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for m in range(N):
        ax = axes[m]
        
        # Plot basis vector on triangulation
        tcf = ax.tricontourf(pts[:, 0], pts[:, 1], tri.simplices, 
                            standard_basis[m], cmap='viridis')
        ax.triplot(pts[:, 0], pts[:, 1], tri.simplices, 'k-', 
                  linewidth=0.1, alpha=0.2)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title(f'Standard Basis Vector {m}')
        ax.set_aspect('equal')
        plt.colorbar(tcf, ax=ax, label=f'Basis {m}')
    
    plt.tight_layout()
    basis_plot_path = os.path.join(mode_save_path, "standard_basis_vectors.png")
    plt.savefig(basis_plot_path, dpi=300)
    plt.close()
    print(f"Saved standard basis visualization to {basis_plot_path}")
    
    # 4. Compute coefficients in standard basis
    print(f"\nComputing standard basis coefficients...")
    standard_coeffs = field_to_vector(df_re_hz, df_im_hz, N)
    
    print(f"Standard basis coefficients:")
    for m, coeff in enumerate(standard_coeffs):
        print(f"  c_{m} = {coeff.real:.6e} + {coeff.imag:.6e}j")
    
    # 5. Convert to Fourier basis
    print(f"\nConverting to Fourier basis...")
    fourier_coeffs = standard_to_fourier_basis(standard_coeffs, N)
    fourier_energies = np.abs(fourier_coeffs)**2
    normalized_energies = fourier_energies / np.sum(fourier_energies)
    
    print(f"Fourier basis coefficients:")
    fourier_labels = ['DC (k=0)']
    for k in range(1, (N-1)//2 + 1):
        fourier_labels.extend([f'cos(k={k})', f'sin(k={k})'])
    if N % 2 == 0:
        fourier_labels.append(f'Nyquist (k={N//2})')
    
    for label, coeff in zip(fourier_labels, fourier_coeffs):
        print(f"  {label:15s} = {coeff.real:.6e} + {coeff.imag:.6e}j")
    
    # 6. Save standard basis coefficients to CSV
    standard_df = pd.DataFrame({
        f'basis_{m}': [standard_coeffs[m]] for m in range(N)
    })
    # Split into real and imaginary parts for CSV
    standard_real_df = pd.DataFrame({
        f'basis_{m}': [standard_coeffs[m].real] for m in range(N)
    })
    standard_imag_df = pd.DataFrame({
        f'basis_{m}': [standard_coeffs[m].imag] for m in range(N)
    })
    standard_combined_df = pd.concat([standard_df, standard_real_df, standard_imag_df], axis=0, ignore_index=True)
    standard_combined_df.index = ['complex', 'real', 'imag']
    
    standard_csv_path = os.path.join(mode_save_path, "standard_basis_coefficients.csv")
    standard_combined_df.to_csv(standard_csv_path)
    print(f"\nSaved standard basis coefficients to {standard_csv_path}")
    
    # 7. Save Fourier basis coefficients to CSV
    fourier_df = pd.DataFrame({
        f'{label}': [fourier_coeffs[i]]
        for i, label in enumerate(fourier_labels)
    })
    fourier_real_df = pd.DataFrame({
        f'{label}': [fourier_coeffs[i].real] 
        for i, label in enumerate(fourier_labels)
    })
    fourier_imag_df = pd.DataFrame({
        f'{label}': [fourier_coeffs[i].imag] 
        for i, label in enumerate(fourier_labels)
    })
    fourier_energy_df = pd.DataFrame({
        f'{label}': [normalized_energies[i]]
        for i, label in enumerate(fourier_labels)
    })
    fourier_combined_df = pd.concat([
        fourier_df, 
        fourier_real_df, 
        fourier_imag_df,
        fourier_energy_df,
    ], axis=0, ignore_index=True)
    fourier_combined_df.index = ['complex', 'real', 'imag', 'energy']
    
    fourier_csv_path = os.path.join(mode_save_path, "fourier_basis_coefficients.csv")
    fourier_combined_df.to_csv(fourier_csv_path)
    print(f"Saved Fourier basis coefficients to {fourier_csv_path}")
    
    # 8. Verification: compute energy in both representations
    standard_energy = np.sum(np.abs(standard_coeffs)**2)
    fourier_energy = np.sum(np.abs(fourier_coeffs)**2)
    
    # 9. Create summary plot comparing field and reconstructed field
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Original field magnitude
    field_mag = np.abs(hz_complex)
    tcf0 = axes[0].tricontourf(pts[:, 0], pts[:, 1], tri.simplices, 
                               field_mag, levels=20, cmap='viridis')
    axes[0].triplot(pts[:, 0], pts[:, 1], tri.simplices, 'k-', 
                   linewidth=0.1, alpha=0.1)
    axes[0].set_title('Original Field |Hz|')
    axes[0].set_aspect('equal')
    plt.colorbar(tcf0, ax=axes[0])
    
    # Original field phase
    field_phase = np.angle(hz_complex)/np.pi
    tcf1 = axes[1].tricontourf(pts[:, 0], pts[:, 1], tri.simplices, 
                               field_phase, levels=20, cmap='twilight')
    axes[1].triplot(pts[:, 0], pts[:, 1], tri.simplices, 'k-', 
                   linewidth=0.1, alpha=0.1)
    axes[1].set_title('Original Field Phase(Hz)')
    axes[1].set_aspect('equal')
    cbar1 = plt.colorbar(tcf1, ax=axes[1])
    cbar1.set_label(r'Phase / $\pi$')
    
    # Energy distribution in Fourier basis
    bars = axes[2].bar(range(len(fourier_labels)), normalized_energies,
               color=plt.cm.tab10(range(len(fourier_labels))), alpha=0.7, edgecolor='black')
    axes[2].set_xticks(range(len(fourier_labels)))
    axes[2].set_xticklabels(fourier_labels, rotation=45, ha='right')
    axes[2].set_ylabel('Normalized Energy')
    axes[2].set_title('Energy Distribution in Fourier Basis')
    axes[2].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on top of bars
    for bar, energy in zip(bars, normalized_energies):
        height = bar.get_height()
        axes[2].text(bar.get_x() + bar.get_width()/2., height,
                    f'{energy:.3f}',
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    summary_plot_path = os.path.join(mode_save_path, "field_decomposition_summary.png")
    plt.savefig(summary_plot_path, dpi=300)
    plt.close()
    print(f"Saved summary plot to {summary_plot_path}")
    
    print(f"\n{'='*60}")
    print(f"Completed test_field_to_vector for mode {mode_idx}")
    print(f"All outputs saved to {mode_save_path}")
    print(f"{'='*60}\n")
    
    return 

def verify_boundary_condition_equivalence(
    periodic_save_path,
    floquet_save_path,
    num_modes=16,
    plane="center",
    N=6,
    freq_rtol=1e-4,
    energy_rtol=1e-2,
    overlap_atol=0.99,
    degenerate_freq_tol_THz=0.5,
):
    """
    Verify that periodic and Floquet (k=0) BC give identical simulation results.

    Three checks
    ------------
    1. Eigenfrequencies: Re(freq), Im(freq), Q-factor match after sorting by Re(freq).
    2. Fourier subspace energies: phase-invariant field fingerprint matches.
       Degenerate modes are grouped and their energies summed before comparison.
    3. Complex field overlap: |<hz_per | hz_flo>| / sqrt(||hz_per||^2 ||hz_flo||^2)
       should be >= overlap_atol for non-degenerate modes.

    Returns
    -------
    dict with keys ``passed``, ``results_df``.
    """
    print(f"\n{'='*70}")
    print("VERIFYING BOUNDARY CONDITION EQUIVALENCE (periodic vs Floquet k=0)")
    print(f"{'='*70}")

    periodic_eig_dir = os.path.join(periodic_save_path, "eigenmodes")
    floquet_eig_dir  = os.path.join(floquet_save_path,  "eigenmodes")

    df_per = pd.read_csv(os.path.join(periodic_save_path, "eigenfrequencies_parsed.csv"))
    df_flo = pd.read_csv(os.path.join(floquet_save_path,  "eigenfrequencies_parsed.csv"))

    # Sort both by ascending Re(freq)
    idx_per = np.argsort(df_per["re"].values)[:num_modes]
    idx_flo = np.argsort(df_flo["re"].values)[:num_modes]
    re_per = df_per["re"].values[idx_per];  re_flo = df_flo["re"].values[idx_flo]
    im_per = df_per["im"].values[idx_per];  im_flo = df_flo["im"].values[idx_flo]
    q_per  = df_per["q"].values[idx_per];   q_flo  = df_flo["q"].values[idx_flo]

    # ------------------------------------------------------------------ #
    # 1. Eigenfrequency check: re, im, q
    # ------------------------------------------------------------------ #
    re_err = np.abs(re_per - re_flo) / (np.abs(re_per) + 1e-30)
    im_err = np.abs(im_per - im_flo)
    q_err  = np.abs(q_per  - q_flo)  / (np.abs(q_per)  + 1e-30)
    freq_ok = re_err < freq_rtol

    print(f"\n--- 1. Eigenfrequency check (freq_rtol={freq_rtol}) ---")
    print(f"{'Rank':>4}  {'Re_per':>10}  {'Re_flo':>10}  {'re_err':>9}  "
          f"{'Im_per':>10}  {'Im_flo':>10}  {'im_err':>9}  "
          f"{'Q_per':>9}  {'Q_flo':>9}  {'q_err':>9}  {'OK':>4}")
    for i in range(num_modes):
        ok = freq_ok[i]
        print(f"{i:4d}  {re_per[i]:10.4f}  {re_flo[i]:10.4f}  {re_err[i]:9.2e}  "
              f"{im_per[i]:10.4e}  {im_flo[i]:10.4e}  {im_err[i]:9.2e}  "
              f"{q_per[i]:9.2e}  {q_flo[i]:9.2e}  {q_err[i]:9.2e}  "
              f"{'PASS' if ok else 'FAIL':>4}")
    freq_passed = bool(np.all(freq_ok))
    print(f"Eigenfrequency check: {'PASS' if freq_passed else 'FAIL'}")

    # ------------------------------------------------------------------ #
    # 2. Fourier decomposition check
    # ------------------------------------------------------------------ #
    def _load_fourier_energies(eig_dir, mode_indices):
        all_e = []
        for orig_idx in mode_indices:
            csv_path = os.path.join(eig_dir, f"mode_{orig_idx:02d}_vector",
                                    "fourier_basis_coefficients.csv")
            if not os.path.exists(csv_path):
                return None
            df = pd.read_csv(csv_path, index_col=0)
            row = df.loc["energy"].apply(
                lambda v: float(np.real(complex(str(v))))
            ).values
            all_e.append(row)
        return np.array(all_e)  # (num_modes, num_fourier_components)

    def _group_by_freq(freqs, tol):
        groups, used = [], np.zeros(len(freqs), dtype=bool)
        for i in range(len(freqs)):
            if used[i]:
                continue
            g = [i]
            for j in range(i + 1, len(freqs)):
                if not used[j] and abs(freqs[j] - freqs[i]) < tol:
                    g.append(j); used[j] = True
            used[i] = True
            groups.append(g)
        return groups

    energies_per = _load_fourier_energies(periodic_eig_dir, idx_per)
    energies_flo = _load_fourier_energies(floquet_eig_dir,  idx_flo)
    fourier_errs = np.zeros(num_modes)
    fourier_passed = True

    print(f"\n--- 2. Fourier decomposition check (energy_rtol={energy_rtol}) ---")
    if energies_per is None or energies_flo is None:
        print("    SKIPPED (fourier_basis_coefficients.csv not found)")
    else:
        groups_per = _group_by_freq(re_per, degenerate_freq_tol_THz)
        groups_flo = _group_by_freq(re_flo, degenerate_freq_tol_THz)
        for g_p, g_f in zip(groups_per, groups_flo):
            sumE_p = energies_per[g_p].sum(axis=0)
            sumE_f = energies_flo[g_f].sum(axis=0)
            total  = sumE_p.sum() + 1e-30
            err    = np.max(np.abs(sumE_p - sumE_f)) / total
            ok     = err < energy_rtol
            fourier_passed = fourier_passed and ok
            for i in g_p:
                fourier_errs[i] = err
            label = f"modes {g_p}" if len(g_p) == 1 else f"modes {g_p} (degen)"
            print(f"  {label:35s}  max_err={err:.2e}  {'PASS' if ok else 'FAIL'}")
    print(f"Fourier decomposition check: {'PASS' if fourier_passed else 'FAIL'}")

    # ------------------------------------------------------------------ #
    # 3. Complex field overlap  <hz_per | hz_flo> = ∫ conj(hz_per) * hz_flo dA
    # ------------------------------------------------------------------ #
    print(f"\n--- 3. Complex field overlap check (overlap_atol={overlap_atol}) ---")
    print(f"{'Rank':>4}  {'per_idx':>7}  {'flo_idx':>7}  {'|overlap|':>10}  {'OK':>4}")
    overlap_vals = []
    overlap_passed = True
    for rank in range(num_modes):
        orig_per = idx_per[rank]
        orig_flo = idx_flo[rank]
        re_p_file = os.path.join(periodic_eig_dir, f"{orig_per:02d}_ReHz_{plane}_2d.txt")
        im_p_file = os.path.join(periodic_eig_dir, f"{orig_per:02d}_ImHz_{plane}_2d.txt")
        re_f_file = os.path.join(floquet_eig_dir,  f"{orig_flo:02d}_ReHz_{plane}_2d.txt")
        im_f_file = os.path.join(floquet_eig_dir,  f"{orig_flo:02d}_ImHz_{plane}_2d.txt")
        if not all(os.path.exists(p) for p in [re_p_file, im_p_file, re_f_file, im_f_file]):
            print(f"{rank:4d}: field files missing, skipping")
            overlap_vals.append(np.nan)
            continue

        pts_p, hz_p = get_complex_field(
            pd.read_csv(re_p_file, sep=r"\s+", comment="%", header=None),
            pd.read_csv(im_p_file, sep=r"\s+", comment="%", header=None),
        )
        pts_f, hz_f = get_complex_field(
            pd.read_csv(re_f_file, sep=r"\s+", comment="%", header=None),
            pd.read_csv(im_f_file, sep=r"\s+", comment="%", header=None),
        )

        # Interpolate floquet field onto periodic grid
        hz_f_at_p = (interpolate_field(pts_f, np.real(hz_f), pts_p)
                     + 1j * interpolate_field(pts_f, np.imag(hz_f), pts_p))

        # <hz_p | hz_f> = ∫ conj(hz_p) * hz_f dA
        integrand = np.conj(hz_p) * hz_f_at_p
        inner = (integrate_field(pts_p, np.real(integrand))
                 + 1j * integrate_field(pts_p, np.imag(integrand)))
        norm_p = integrate_field(pts_p, np.abs(hz_p)**2)
        norm_f = integrate_field(pts_p, np.abs(hz_f_at_p)**2)
        overlap = np.abs(inner) / np.sqrt(norm_p * norm_f + 1e-30)

        ok = overlap >= overlap_atol
        overlap_passed = overlap_passed and ok
        overlap_vals.append(overlap)
        print(f"{rank:4d}  {orig_per:7d}  {orig_flo:7d}  {overlap:10.6f}  {'PASS' if ok else 'FAIL'}")
    print(f"Field overlap check: {'PASS' if overlap_passed else 'FAIL'}")

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    results_df = pd.DataFrame({
        "rank":        range(num_modes),
        "re_per":      re_per,  "re_flo":  re_flo,  "re_err":      re_err,
        "im_per":      im_per,  "im_flo":  im_flo,  "im_err":      im_err,
        "q_per":       q_per,   "q_flo":   q_flo,   "q_err":       q_err,
        "fourier_err": fourier_errs,
        "overlap":     overlap_vals,
        "freq_ok":     freq_ok,
    })
    summary_csv = os.path.join(periodic_save_path, "bc_equivalence_summary.csv")
    results_df.to_csv(summary_csv, index=False)
    print(f"\nSaved summary to {summary_csv}")

    _plot_bc_comparison(
        re_per, re_flo, re_err,
        energies_per, energies_flo,
        overlap_vals,
        periodic_save_path, num_modes,
    )

    overall = freq_passed and fourier_passed and overlap_passed
    print(f"\n{'='*70}")
    print(f"OVERALL: {'PASS -- periodic and Floquet BC results are equivalent' if overall else 'FAIL -- discrepancies detected'}")
    print(f"{'='*70}\n")

    return {"passed": overall, "results_df": results_df}


def _plot_bc_comparison(
    re_per, re_flo, re_err,
    energies_per, energies_flo,
    overlap_vals,
    save_dir, num_modes,
):
    """Three-panel summary: freq parity, Fourier energy parity, overlap per mode."""
    has_fourier = (energies_per is not None and energies_flo is not None)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Panel 1: eigenfrequency parity
    ax = axes[0]
    ax.plot(re_per, re_flo, "o", markersize=5, color="steelblue")
    f_min = min(re_per.min(), re_flo.min())
    f_max = max(re_per.max(), re_flo.max())
    ax.plot([f_min, f_max], [f_min, f_max], "k--", linewidth=1, label="y=x")
    ax.set_xlabel("Re(freq) periodic [THz]")
    ax.set_ylabel("Re(freq) Floquet k=0 [THz]")
    ax.set_title("Eigenfrequency parity")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    # Panel 2: Fourier energy parity scatter
    ax2 = axes[1]
    if has_fourier:
        flat_per = energies_per.ravel()
        flat_flo = energies_flo.ravel()
        ax2.scatter(flat_per, flat_flo, s=12, alpha=0.6, color="mediumseagreen")
        emax = max(flat_per.max(), flat_flo.max())
        ax2.plot([0, emax], [0, emax], "k--", linewidth=1, label="y=x")
        ax2.set_xlabel("Fourier energy - periodic BC")
        ax2.set_ylabel("Fourier energy - Floquet k=0")
        ax2.set_title("Fourier subspace energies parity")
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "Fourier CSVs not found", ha="center", va="center",
                 transform=ax2.transAxes)
        ax2.set_title("Fourier subspace energies parity")
    ax2.grid(True, alpha=0.3)

    # Panel 3: complex field overlap per mode
    ax3 = axes[2]
    valid = [(i, v) for i, v in enumerate(overlap_vals) if not np.isnan(v)]
    if valid:
        ranks, ovlps = zip(*valid)
        colors = ["steelblue" if v >= 0.99 else "tomato" for v in ovlps]
        ax3.bar(ranks, ovlps, color=colors, edgecolor="black", alpha=0.8)
        ax3.axhline(0.99, color="gray", linestyle="--", linewidth=1, label="atol=0.99")
        ax3.set_ylim(0, 1.05)
    ax3.set_xlabel("Mode rank (sorted by freq)")
    ax3.set_ylabel("|<hz_per | hz_flo>| / norm")
    ax3.set_title("Complex field overlap")
    ax3.legend(fontsize=8); ax3.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plot_path = os.path.join(save_dir, "bc_equivalence_comparison.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"\nSaved BC comparison plot to {plot_path}")


def test_simulation(save_path, boundary_condition):
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

        if boundary_condition == "periodic":
            k = None
        elif boundary_condition == "floquet":
            k = {'kx': 0, 'ky': 0}
        else:
            raise ValueError(f"Unsupported boundary condition: {boundary_condition}")
        sim_run.build_and_run(config["basic_config"]["a"], config["triangles"], k)
        os.makedirs(save_path, exist_ok=True)
        sim_run.model.save(os.path.join(save_path, "design.mph"))
        sim_run.model.save(os.path.join(save_path, "design.java"))
        sim_run.export_eigenfrequencies(save_path)
        eigenfrequencies = pd.read_csv(
            os.path.join(save_path, "eigenfrequencies.txt"),
            sep=r"\s+",
            comment="%",
            header=None,
        )

        # Parse eigenfrequencies
        s = eigenfrequencies.iloc[:, 0].astype("string").str.strip().str.replace("i", "j", regex=False)
        eig = s.map(lambda z: complex(z))  # e.g. "180.6+0.05j" -> complex

        re = np.real(eig.to_numpy(dtype=np.complex128))
        im = np.imag(eig.to_numpy(dtype=np.complex128))

        # Q = Re / (2 * Im)
        q = re / (np.abs(2 * im) + 1e-15)
        log_q = np.log10(q)
        # export BIC modes
        # bic_mode_indices = np.where(log_q >= 7)[0]
        # for mode_idx in bic_mode_indices:
        for mode_idx in range(len(eig)):
            sim_run.export_2d_fields(mode_idx, "ewfd.Hz", "ReHz", eigenmodes_save_path)
            sim_run.export_2d_fields(mode_idx, "ewfd.Hz*(-i)", "ImHz", eigenmodes_save_path)
        
        sim_run.clear()

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

if __name__ == "__main__":
    out_root = get_tests_out_path("test_simulation")

    # Periodic boundary simulation test
    periodic_save_path = os.path.join(out_root, "test_periodic_boundary_simulation_results")
    periodic_eig_path  = os.path.join(periodic_save_path, "eigenmodes")
    test_simulation(periodic_save_path, boundary_condition="periodic")
    for mode_idx in range(16):
        test_field_inner_product(periodic_eig_path, mode_idx=mode_idx)
        test_field_to_vector(periodic_eig_path, mode_idx=mode_idx)

    # Floquet boundary simulation test (k=0 should be identical to periodic)
    floquet_save_path = os.path.join(out_root, "test_floquet_boundary_simulation_results")
    floquet_eig_path  = os.path.join(floquet_save_path, "eigenmodes")
    test_simulation(floquet_save_path, boundary_condition="floquet")
    for mode_idx in range(16):
        test_field_inner_product(floquet_eig_path, mode_idx=mode_idx)
        test_field_to_vector(floquet_eig_path, mode_idx=mode_idx)

    # Verify that periodic BC and Floquet BC (k=0) give identical results
    results = verify_boundary_condition_equivalence(
        periodic_save_path=periodic_save_path,
        floquet_save_path=floquet_save_path,
        num_modes=16,
        plane="center",
        N=6,
        freq_rtol=1e-4,       # relative tolerance on Re(eigenfreq), ~0.01%
        energy_rtol=1e-2,     # tolerance on Fourier energy and field magnitude, ~1%
        degenerate_freq_tol_THz=0.5,  # group modes within 0.5 THz as degenerate
    )
    assert results["passed"], "Boundary condition equivalence check FAILED"
