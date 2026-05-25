import argparse
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.backends import make_backend
from bilayer_workflow.config import load_config
from bilayer_workflow.runtime_paths import get_workspace_path
from bilayer_workflow.workflow import evaluate_candidate


def main():
    parser = argparse.ArgumentParser(description="Evaluate the configured seed geometry.")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "configs", "default_search.json"))
    parser.add_argument("--backend", choices=["mock", "comsol"], default="mock")
    parser.add_argument("--workspace", default=get_workspace_path("single_seed"))
    args = parser.parse_args()
    result = evaluate_candidate({}, load_config(args.config), make_backend(args.backend), args.workspace)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
