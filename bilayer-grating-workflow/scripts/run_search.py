import argparse
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.backends import make_backend
from bilayer_workflow.config import load_config
from bilayer_workflow.runtime_paths import get_workspace_path
from bilayer_workflow.workflow import run_search


def main():
    parser = argparse.ArgumentParser(description="Optimize a 2D switchable bilayer grating.")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "configs", "default_search.json"))
    parser.add_argument("--backend", choices=["mock", "comsol"], default="mock")
    parser.add_argument("--workspace", default=get_workspace_path("default_search"))
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--method", choices=["Random", "Sobol", "NevergradNGOpt", "NevergradCMA", "NevergradOnePlusOne"])
    args = parser.parse_args()

    config = load_config(args.config)
    if args.iterations is not None:
        config["optimization"]["iterations"] = args.iterations
    if args.batch_size is not None:
        config["optimization"]["batch_size"] = args.batch_size
    if args.method is not None:
        config["optimization"]["method"] = args.method
    best = run_search(config, make_backend(args.backend), args.workspace)
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
