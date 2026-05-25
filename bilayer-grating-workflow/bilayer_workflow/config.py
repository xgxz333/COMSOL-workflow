import copy
import json


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def design_with_params(config, params):
    design = copy.deepcopy(config["design"])
    design.update({key: float(value) for key, value in params.items()})
    return design


def validate_config(config):
    states = config["materials"]["pcm_states"]
    required_states = {"amorphous", "crystalline"}
    missing = required_states.difference(states)
    if missing:
        raise ValueError(f"Missing PCM states: {sorted(missing)}")

    objective = config["objective"]
    for key in ["amorphous_direction", "crystalline_direction"]:
        if objective[key] not in {"up", "down"}:
            raise ValueError(f"{key} must be 'up' or 'down'")

    low, high = config["simulation"]["frequency_window_thz"]
    if low >= high:
        raise ValueError("frequency_window_thz must be increasing")
