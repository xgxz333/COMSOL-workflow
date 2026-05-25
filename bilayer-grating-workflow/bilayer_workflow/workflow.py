import json
import os

import pandas as pd

from .config import design_with_params, validate_config
from .geometry import GeometryError, build_geometry, visualize_geometry
from .metrics import evaluate_mode_pairs
from .optimizers import make_optimizer
from .storage import OptimizationStorage


def evaluate_candidate(params, config, backend, workspace):
    os.makedirs(workspace, exist_ok=True)
    try:
        geometry = build_geometry(design_with_params(config, params))
    except GeometryError as error:
        return {
            "objective": -1.0e9,
            "attrs": {"valid_geometry": False, "error": str(error)},
        }

    geometry.save_json(os.path.join(workspace, "geometry.json"))
    preview_error = None
    try:
        visualize_geometry(geometry, os.path.join(workspace, "geometry.png"))
    except ModuleNotFoundError as error:
        preview_error = str(error)

    state_modes = {}
    for state in ["amorphous", "crystalline"]:
        state_workspace = os.path.join(workspace, state)
        state_modes[state] = backend.evaluate_state(
            geometry, state, config, state_workspace
        )
        os.makedirs(state_workspace, exist_ok=True)
        pd.DataFrame([mode.to_dict() for mode in state_modes[state]]).to_csv(
            os.path.join(state_workspace, "modes.csv"), index=False
        )

    result = evaluate_mode_pairs(
        state_modes["amorphous"], state_modes["crystalline"], config
    )
    result["attrs"]["valid_geometry"] = True
    if preview_error is not None:
        result["attrs"]["geometry_preview_error"] = preview_error
    with open(os.path.join(workspace, "result.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    return result


def run_search(config, backend, workspace):
    validate_config(config)
    os.makedirs(workspace, exist_ok=True)
    storage = OptimizationStorage(workspace)
    settings = config["optimization"]
    optimizer = make_optimizer(
        settings["method"],
        settings["bounds"],
        int(settings["batch_size"]),
        storage.valid_rows(),
    )

    for iteration in range(int(settings["iterations"])):
        suggestions = optimizer.ask()
        objectives = []
        for suggestion in suggestions:
            run_id = len(storage.rows)
            run_workspace = os.path.join(workspace, "runs", f"run_{run_id:05d}")
            result = evaluate_candidate(
                suggestion.params, config, backend, run_workspace
            )
            record = {
                "meta": {
                    "run_id": run_id,
                    "iteration": iteration,
                    "optimizer": optimizer.name,
                },
                "params": suggestion.params,
                "result": {"objective": result["objective"]},
                "attrs": result.get("attrs", {}),
            }
            storage.write(record)
            objectives.append(result["objective"])
        optimizer.tell(suggestions, objectives)
    return storage.best()
