import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bilayer_workflow.metrics import ModeResult, evaluate_mode_pairs


def load_default_config():
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "configs", "default_search.json"
    )
    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_switching_pair_is_selected():
    config = load_default_config()
    amorphous = [
        ModeResult("amorphous", 0, 183.5, 1.0e5, 100.0, 1.0),
        ModeResult("amorphous", 1, 183.4, 1.0e8, 1.0, 10.0),
    ]
    crystalline = [
        ModeResult("crystalline", 0, 183.6, 2.0e5, 1.0, 100.0),
        ModeResult("crystalline", 1, 183.6, 1.0e8, 100.0, 1.0),
    ]
    result = evaluate_mode_pairs(amorphous, crystalline, config)
    assert result["attrs"]["amorphous_mode_index"] == 0
    assert result["attrs"]["crystalline_mode_index"] == 0
    assert result["attrs"]["directionality_pass"]


if __name__ == "__main__":
    test_switching_pair_is_selected()
    print("metric tests passed")
