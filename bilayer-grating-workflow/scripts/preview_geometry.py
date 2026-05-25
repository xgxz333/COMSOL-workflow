import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.config import load_config
from bilayer_workflow.geometry import build_geometry, visualize_geometry
from bilayer_workflow.runtime_paths import ensure_directory, get_out_path


def main():
    parser = argparse.ArgumentParser(description="Render the default 2D bilayer cell.")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "configs", "default_search.json"))
    parser.add_argument("--output", default=get_out_path("default_geometry.png"))
    args = parser.parse_args()

    geometry = build_geometry(load_config(args.config)["design"])
    ensure_directory(os.path.dirname(os.path.abspath(args.output)))
    geometry.save_json(os.path.splitext(args.output)[0] + ".json")
    visualize_geometry(geometry, args.output)
    print(os.path.abspath(args.output))


if __name__ == "__main__":
    main()
