import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.backends import make_backend
from bilayer_workflow.config import load_config
from bilayer_workflow.runtime_paths import ensure_directory, get_workspace_path
from bilayer_workflow.workflow import evaluate_candidate


def main():
    parser = argparse.ArgumentParser(description="Scan Bloch wave vector for switchable modes.")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "configs", "default_search.json"))
    parser.add_argument("--backend", choices=["mock", "comsol"], default="mock")
    parser.add_argument("--workspace", default=get_workspace_path("kx_scan"))
    parser.add_argument("--start", type=float, default=0.08)
    parser.add_argument("--stop", type=float, default=0.16)
    parser.add_argument("--points", type=int, default=17)
    args = parser.parse_args()

    config = load_config(args.config)
    backend = make_backend(args.backend)
    ensure_directory(args.workspace)
    rows = []
    for idx, kx_norm in enumerate(np.linspace(args.start, args.stop, args.points)):
        workspace = os.path.join(args.workspace, f"kx_{idx:03d}_{kx_norm:.5f}")
        result = evaluate_candidate({"kx_norm": float(kx_norm)}, config, backend, workspace)
        attrs = result.get("attrs", {})
        rows.append(
            {
                "kx_norm": kx_norm,
                "objective": result["objective"],
                "amorphous_directionality_db": attrs.get("amorphous_directionality_db"),
                "crystalline_directionality_db": attrs.get("crystalline_directionality_db"),
                "switching_margin_db": attrs.get("switching_margin_db"),
                "average_frequency_thz": attrs.get("average_frequency_thz"),
                "state_frequency_difference_thz": attrs.get("state_frequency_difference_thz"),
            }
        )
    output = os.path.join(args.workspace, "kx_scan.csv")
    pd.DataFrame(rows).to_csv(output, index=False)
    print(os.path.abspath(output))


if __name__ == "__main__":
    main()
