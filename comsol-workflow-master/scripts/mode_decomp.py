import argparse
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
from basis_utils import standard_to_fourier_basis
from energy_recovery import field_to_vector

def get_vector_repr(simulation_save_path, mode_idx=0, N=6):
    # 1. Load the field data
    df_re_hz = pd.read_csv(
        os.path.join(simulation_save_path, f"{mode_idx:02d}_ReHz_2d.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )
    df_im_hz = pd.read_csv(
        os.path.join(simulation_save_path, f"{mode_idx:02d}_ImHz_2d.txt"),
        sep=r"\s+",
        comment="%",
        header=None,
    )

    standard_coeffs = field_to_vector(df_re_hz, df_im_hz, N)
    
    # Convert to Fourier basis and report normalized energies.
    fourier_coeffs = standard_to_fourier_basis(standard_coeffs, N)
    fourier_energies = np.abs(fourier_coeffs)**2
    normalized_energies = fourier_energies / np.sum(fourier_energies)
    return {
        "standard_coeffs": standard_coeffs,
        "fourier_coeffs": fourier_coeffs,
        "normalized_energies": normalized_energies,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze exported COMSOL mode data and print normalized Fourier energies.")
    parser.add_argument("simulation_save_path", help="Directory containing exported field text files.")
    parser.add_argument("--mode-idx", type=int, default=0, help="Eigenmode index to analyze.")
    parser.add_argument("--n", type=int, default=6, help="Rotational symmetry order.")
    args = parser.parse_args()

    result = get_vector_repr(args.simulation_save_path, mode_idx=args.mode_idx, N=args.n)
    print("Normalized Fourier energies:")
    print(np.array2string(result["normalized_energies"], precision=4, suppress_small=True))
